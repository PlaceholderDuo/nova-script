import asyncio
import logging
import sys
import threading
from pathlib import Path
from queue import Queue

from src.engine import Engine


def setup_logging(level: int = logging.INFO):
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )


async def run_headless():
    setup_logging(logging.DEBUG)
    engine = Engine()
    try:
        await engine.start()
    except KeyboardInterrupt:
        pass
    finally:
        await engine.stop()


async def run_with_tui():
    setup_logging(logging.INFO)
    tui_queue: Queue = Queue()
    engine = Engine()
    engine.set_tui_queue(tui_queue)

    from src.tui.app import run_tui

    tui_thread = threading.Thread(target=run_tui, args=(tui_queue,), daemon=True)
    tui_thread.start()

    try:
        await engine.start()
    except KeyboardInterrupt:
        pass
    finally:
        await engine.stop()


def main():
    args = sys.argv[1:]
    if "--tui" in args:
        try:
            asyncio.run(run_with_tui())
        except KeyboardInterrupt:
            pass
    else:
        try:
            asyncio.run(run_headless())
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
