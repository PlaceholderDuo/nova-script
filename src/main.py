#!/usr/bin/env python3
"""
Nova-Script CLI entry point.

Usage:
  nova-script                              → launch with default live-show profile
  nova-script <profile>                    → launch with named profile
  nova-script <profile> [--tui] [virtualizer]   → launch with TUI + virtualizer
  nova-script save <profile>               → save current state as profile
  nova-script list                         → list available profiles
  nova-script export <profile> <path>      → export profile to file
  nova-script import <path> [<alias>]      → import profile from file
  nova-script virtualizer stop             → stop virtualizer and cleanup
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


async def run_engine(config: dict, with_tui: bool = False, virt_proc=None):
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


def _start_virtualizer() -> subprocess.Popen | None:
    project = _get_project_dir()
    backend = project / "tools" / "novation-virtualizer.py"
    html = project / "tools" / "novation-virtualizer.html"
    python = project / ".venv" / "bin" / "python"

    if not python.exists():
        print("Error: .venv not found")
        return None

    try:
        result = subprocess.run(
            ["lsof", "-ti:8766"], capture_output=True, text=True, timeout=3
        )
        if result.stdout.strip():
            print("Virtualizer already running on port 8766")
            open_html(html)
            return None
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
        print("Error: Backend failed to start")
        return None

    print(f"Virtualizer running (PID {proc.pid})")
    open_html(html)
    return proc


def _stop_virtualizer(proc: subprocess.Popen | None = None):
    if proc is not None:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except (ProcessLookupError, OSError):
            pass
    try:
        result = subprocess.run(
            ["lsof", "-ti:8766"], capture_output=True, text=True, timeout=3
        )
        for pid in result.stdout.strip().split("\n"):
            if pid:
                try:
                    os.kill(int(pid), signal.SIGTERM)
                except OSError:
                    pass
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass


def cmd_virtualizer_stop():
    proc = None
    try:
        result = subprocess.run(
            ["lsof", "-ti:8766"], capture_output=True, text=True
        )
        if result.stdout.strip():
            proc = True
    except FileNotFoundError:
        pass

    _stop_virtualizer()
    print("Virtualizer stopped" if proc else "No virtualizer running")


def open_html(path: Path):
    subprocess.Popen(["open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    args = sys.argv[1:]

    if not args:
        asyncio.run(run_chill())
        return

    if args[0] == "virtualizer" and len(args) >= 2 and args[1] == "stop":
        cmd_virtualizer_stop()
        return

    if args[0].startswith("virt") and len(args) == 1:
        print(f"Unknown command '{args[0]}'.")
        print("Usage: nova-script <profile> [--tui] [virtualizer]")
        print("  e.g.  nova-script live-show virtualizer")
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
    use_virtualizer = "virtualizer" in args
    profile_name = "live-show"

    for a in args:
        if a not in ("--tui", "virtualizer") and not a.startswith("-"):
            profile_name = a
            break

    config = ProfileManager().load(profile_name)

    virt_proc = None
    if use_virtualizer:
        virt_proc = _start_virtualizer()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def shutdown():
        loop.call_soon_threadsafe(lambda: None)
        for task in asyncio.all_tasks(loop):
            task.cancel()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, shutdown)
        except NotImplementedError:
            signal.signal(sig, lambda s, f: shutdown())

    try:
        loop.run_until_complete(run_engine(config, with_tui=with_tui))
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        tasks = asyncio.all_tasks(loop)
        for task in tasks:
            task.cancel()
        try:
            loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        except Exception:
            pass
        loop.close()
        if virt_proc:
            print("Shutting down virtualizer...")
            _stop_virtualizer(virt_proc)
            print("Done.")


if __name__ == "__main__":
    main()
