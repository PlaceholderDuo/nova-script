#!/usr/bin/env python3
"""
Nova-Script CLI entry point.

Usage:
  nova-script                     → launch with default live-show profile
  nova-script <profile>           → launch with named profile
  nova-script --tui [<profile>]   → launch with TUI companion
  nova-script save <profile>      → save current state as profile
  nova-script list                → list available profiles
  nova-script export <profile> <path> → export profile to file
  nova-script import <path> [<alias>] → import profile from file
  nova-script virtualizer              → start virtualizer backend + open browser GUI
  nova-script virtualizer stop          → stop virtualizer and cleanup
"""
import asyncio
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from queue import Queue

from src.profiles import ProfileManager
from src.engine import Engine


async def run_chill(with_tui: bool = False):
    setup_logging(logging.WARNING)
    from src.ui.chill_mode import run_chill_mode

    tui_queue = Queue() if with_tui else None

    if with_tui:
        from src.tui.chill_tui import run_chill_tui
        tui_thread = threading.Thread(
            target=run_chill_tui, args=(tui_queue,), daemon=True
        )
        tui_thread.start()

    try:
        await run_chill_mode(tui_queue=tui_queue)
    except KeyboardInterrupt:
        pass


def setup_logging(level: int = logging.INFO):
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )


async def run_engine(config: dict, with_tui: bool = False):
    setup_logging(logging.DEBUG if not with_tui else logging.INFO)

    tui_queue = Queue() if with_tui else None
    engine = Engine(config=config, tui_queue=tui_queue)

    tui_thread = None
    if with_tui and tui_queue:
        from src.tui.app import run_tui
        tui_thread = threading.Thread(
            target=run_tui, args=(tui_queue, config), daemon=True
        )
        tui_thread.start()

    try:
        await engine.start()
    except KeyboardInterrupt:
        pass
    finally:
        await engine.stop()


def cmd_save(profile_name: str):
    pm = ProfileManager()
    pm.save(profile_name, {})
    print(f"Profile '{profile_name}' saved.")


def cmd_list():
    pm = ProfileManager()
    profiles = pm.list()
    print("Available profiles:")
    for p in profiles:
        marker = " (default)" if p == "live-show" else ""
        print(f"  {p}{marker}")


def cmd_export(profile_name: str, output_path: str):
    pm = ProfileManager()
    pm.export_profile(profile_name, Path(output_path))
    print(f"Exported '{profile_name}' to {output_path}")


def cmd_import(input_path: str, alias: str | None = None):
    pm = ProfileManager()
    name = pm.import_profile(Path(input_path), alias)
    print(f"Imported as '{name}'")


def _get_project_dir() -> Path:
    return Path(__file__).parent.parent


def cmd_virtualizer_start():
    project = _get_project_dir()
    backend = project / "tools" / "novation-virtualizer.py"
    html = project / "tools" / "novation-virtualizer.html"
    python = project / ".venv" / "bin" / "python"

    if not python.exists():
        print("Error: virtual environment not found. Run: python3 -m venv .venv")
        sys.exit(1)

    # Check if already running (with timeout)
    try:
        result = subprocess.run(
            ["lsof", "-ti:8766"], capture_output=True, text=True, timeout=3
        )
        if result.stdout.strip():
            print("Virtualizer is already running on port 8766")
            open_html(html)
            return
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    print("Starting virtualizer backend...")
    proc = subprocess.Popen(
        [str(python), str(backend)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    time.sleep(1)
    if proc.poll() is not None:
        print("Error: Backend failed to start. Check port 8766 is free.")
        sys.exit(1)

    print(f"Virtualizer running (PID {proc.pid})")
    print(f"WebSocket: ws://localhost:8766")
    open_html(html)


def open_html(path: Path):
    subprocess.Popen(["open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def cmd_virtualizer_stop():
    killed = False
    try:
        result = subprocess.run(
            ["lsof", "-ti:8766"], capture_output=True, text=True
        )
        for pid in result.stdout.strip().split("\n"):
            if pid:
                os.kill(int(pid), signal.SIGTERM)
                killed = True
    except FileNotFoundError:
        pass

    if killed:
        print("Virtualizer stopped")
    else:
        print("No virtualizer running")


def main():
    args = sys.argv[1:]

    if not args:
        asyncio.run(run_chill())
        return

    if args[0] == "virtualizer":
        if len(args) >= 2 and args[1] == "stop":
            cmd_virtualizer_stop()
            return
        cmd_virtualizer_start()
        return

    if args[0].startswith("virt") and args[0] != "virtualizer":
        print(f"Unknown command '{args[0]}'. Did you mean 'virtualizer'?")
        print("Usage: nova-script virtualizer [stop]")
        sys.exit(1)

    if args[0] == "list":
        cmd_list()
        return

    if args[0] == "save":
        if len(args) < 2:
            print("Usage: nova-script save <profile-name>")
            sys.exit(1)
        cmd_save(args[1])
        return

    if args[0] == "export":
        if len(args) < 3:
            print("Usage: nova-script export <profile> <output-path>")
            sys.exit(1)
        cmd_export(args[1], args[2])
        return

    if args[0] == "import":
        if len(args) < 2:
            print("Usage: nova-script import <path> [alias]")
            sys.exit(1)
        alias = args[2] if len(args) > 2 else None
        cmd_import(args[1], alias)
        return

    with_tui = "--tui" in args
    profile_name = "live-show"

    for a in args:
        if a != "--tui" and not a.startswith("-"):
            profile_name = a
            break

    config = ProfileManager().load(profile_name)
    asyncio.run(run_engine(config, with_tui=with_tui))


if __name__ == "__main__":
    main()
