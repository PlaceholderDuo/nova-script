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
"""
import asyncio
import logging
import sys
import threading
from pathlib import Path
from queue import Queue

from src.profiles import ProfileManager
from src.engine import Engine


async def run_chill():
    setup_logging(logging.INFO)
    from src.ui.chill_mode import run_chill_mode
    await run_chill_mode()


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


def main():
    args = sys.argv[1:]

    if not args:
        asyncio.run(run_chill())
        return

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
