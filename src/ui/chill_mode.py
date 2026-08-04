"""
Chill Mode — ambient LED effects for standby/idle display.
Slow, smooth patterns inspired by keyboard backlighting.
"""
import math
import random
import time
import asyncio
import logging
from typing import Generator

from src.controllers.color_map import LogicalColor
from src.layout.grid import LogicalGrid

logger = logging.getLogger(__name__)

CHILL_COLORS = [
    LogicalColor.AMBER_LOW,
    LogicalColor.AMBER_MED,
    LogicalColor.RED_LOW,
    LogicalColor.GREEN_LOW,
    LogicalColor.AMBER_HIGH,
]
CHILL_COLORS_DIM = [
    LogicalColor.AMBER_LOW,
    LogicalColor.RED_LOW,
    LogicalColor.GREEN_LOW,
]


def pattern_wave(grid: LogicalGrid, t: float):
    """Horizontal color wave sweeping side to side. Very smooth."""
    phase = math.sin(t * 0.3) * 4 + 4
    grid.clear()
    for y in range(8):
        for x in range(8):
            dist = abs(x - phase)
            if dist < 0.5:
                grid.set_cell(x, y, LogicalColor.AMBER_MED)
            elif dist < 1.5:
                grid.set_cell(x, y, LogicalColor.AMBER_LOW)
            elif dist < 3.0:
                grid.set_cell(x, y, LogicalColor.RED_LOW)


def pattern_breathe(grid: LogicalGrid, t: float):
    """All pads pulse brightness in unison. Slow breathing."""
    brightness = (math.sin(t * 0.5) + 1) / 2
    if brightness > 0.6:
        color = LogicalColor.AMBER_LOW
    elif brightness > 0.3:
        color = LogicalColor.RED_LOW
    else:
        color = LogicalColor.AMBER_LOW
        brightness = max(0, brightness - 0.1)

    for y in range(8):
        for x in range(8):
            if brightness > 0.05:
                grid.set_cell(x, y, color)
            else:
                grid.set_cell(x, y, LogicalColor.OFF)


def pattern_starfield(grid: LogicalGrid, t: float):
    """Scattered dim lights that slowly fade in and out."""
    random.seed(42)
    grid.clear()
    for i in range(10):
        random.seed(i * 137 + int(t * 0.15) * 73)
        x = random.randint(0, 7)
        y = random.randint(0, 7)
        phase = (t * 0.6 + i * 1.3) % (math.pi * 2)
        brightness = (math.sin(phase) + 1) / 2
        if brightness > 0.7:
            grid.set_cell(x, y, CHILL_COLORS[i % len(CHILL_COLORS)])
        elif brightness > 0.4:
            grid.set_cell(x, y, CHILL_COLORS_DIM[i % len(CHILL_COLORS_DIM)])


def pattern_rain(grid: LogicalGrid, t: float):
    """Gentle falling droplets from top of grid."""
    random.seed(123)
    grid.clear()
    for i in range(6):
        random.seed(i * 89 + int(t * 1.2) * 41)
        x = random.randint(0, 7)
        fall_progress = (t * 0.8 + i * 1.7) % 8.0
        y_top = 7 - int(fall_progress)
        y_bot = y_top - 1

        if 0 <= y_top < 8:
            grid.set_cell(x, y_top, LogicalColor.AMBER_MED)
        if 0 <= y_bot < 8:
            grid.set_cell(x, y_bot, LogicalColor.AMBER_LOW)


def pattern_gradient_spin(grid: LogicalGrid, t: float):
    """Slow diagonal gradient that rotates through color."""
    angle = t * 0.2
    cx, cy = 3.5, 3.5

    colors = [
        LogicalColor.AMBER_LOW,
        LogicalColor.AMBER_MED,
        LogicalColor.AMBER_HIGH,
        LogicalColor.RED_LOW,
        LogicalColor.GREEN_LOW,
        LogicalColor.AMBER_LOW,
    ]

    for y in range(8):
        for x in range(8):
            dx = x - cx
            dy = y - cy
            rotated = dx * math.cos(angle) - dy * math.sin(angle)
            idx = int(abs(rotated)) % len(colors)
            grid.set_cell(x, y, colors[idx])


PATTERNS = [
    ("Wave", pattern_wave, 30),
    ("Breathe", pattern_breathe, 25),
    ("Starfield", pattern_starfield, 35),
    ("Rain", pattern_rain, 25),
    ("Gradient", pattern_gradient_spin, 30),
]


class ChillRunner:
    def __init__(self, controller):
        self.controller = controller
        self.grid = LogicalGrid(8, 8)
        self._pattern_idx = 0
        self._pattern_start = 0.0
        self._fade_frames = 0
        self._fading = False

    async def run(self):
        logger.info("Chill mode active — ambient LED patterns")
        self._pattern_start = time.monotonic()
        self._fade_frames = 0

        while True:
            t = time.monotonic() - self._pattern_start

            name, pattern_fn, duration = PATTERNS[self._pattern_idx]

            if t >= duration - 1.0 and not self._fading:
                self._fading = True
                self._fade_frames = 0

            if t >= duration:
                self._pattern_idx = (self._pattern_idx + 1) % len(PATTERNS)
                self._pattern_start = time.monotonic()
                self._fading = False
                self._fade_frames = 0
                continue

            pattern_fn(self.grid, t)

            await self._commit()
            await asyncio.sleep(0.05)

    async def _commit(self):
        for x, y in self.grid.dirty_cells():
            color = self.grid.get_cell(x, y)
            self.controller.set_grid_color(x, y, color)


async def run_chill_mode():
    """Standalone entry point — connects to Launchpad and runs chill patterns."""
    from src.midi.manager import MidiManager
    from src.controllers.launchpad_mk1 import LaunchpadMiniMK1

    mm = MidiManager(poll_interval=1.0)
    lp = LaunchpadMiniMK1(mm)

    mm.register_device("Launchpad Mini", lp.handle_raw_midi)
    await mm.start()

    connected = False
    for _ in range(20):
        if mm.devices.get("Launchpad Mini", None) and mm.devices["Launchpad Mini"].connected:
            connected = True
            break
        await asyncio.sleep(0.5)

    if not connected:
        logger.warning("Launchpad not found. Chill mode requires a Launchpad.")
        await mm.stop()
        return

    lp.on_connect()
    runner = ChillRunner(lp)

    try:
        await runner.run()
    except KeyboardInterrupt:
        pass
    finally:
        lp.clear_grid()
        lp.reset()
        await mm.stop()
