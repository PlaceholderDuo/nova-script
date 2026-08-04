"""
Chill Mode — ambient LED effects for standby/idle display.
Diagonal movement patterns — more visually pleasing than horizontal/vertical.
"""
import math
import random
import time
import asyncio
import logging
from queue import Queue, Empty

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
    """Diagonal amber wave sweeping from bottom-left to top-right."""
    phase = (math.sin(t * 0.25) + 1) * 7
    grid.clear()
    for y in range(8):
        for x in range(8):
            dist = abs((x + y) - phase)
            if dist < 0.5:
                grid.set_cell(x, y, LogicalColor.AMBER_MED)
            elif dist < 1.5:
                grid.set_cell(x, y, LogicalColor.AMBER_LOW)
            elif dist < 3.0:
                grid.set_cell(x, y, LogicalColor.RED_LOW)


def pattern_breathe(grid: LogicalGrid, t: float):
    """Diagonal bands pulsing outward from center."""
    phase = math.sin(t * 0.4)
    grid.clear()
    for y in range(8):
        for x in range(8):
            diag = (x + y) / 14.0
            brightness = math.sin(diag * math.pi * 2 + t * 0.5) * 0.5 + 0.5
            if brightness > 0.55:
                grid.set_cell(x, y, LogicalColor.AMBER_LOW)
            elif brightness > 0.35:
                grid.set_cell(x, y, LogicalColor.RED_LOW)


def pattern_starfield(grid: LogicalGrid, t: float):
    """Scattered stars drifting diagonally and fading."""
    random.seed(42)
    grid.clear()
    for i in range(12):
        random.seed(i * 137 + int(t * 0.08) * 73)
        base_x = random.randint(0, 7)
        base_y = random.randint(0, 7)
        drift = t * 0.3 + i * 0.7
        x = int((base_x + drift) % 8)
        y = int((base_y + drift) % 8)
        phase = (t * 0.5 + i * 1.3) % (math.pi * 2)
        brightness = (math.sin(phase) + 1) / 2
        if brightness > 0.7 and 0 <= x < 8 and 0 <= y < 8:
            grid.set_cell(x, y, CHILL_COLORS[i % len(CHILL_COLORS)])
        elif brightness > 0.4 and 0 <= x < 8 and 0 <= y < 8:
            grid.set_cell(x, y, CHILL_COLORS_DIM[i % len(CHILL_COLORS_DIM)])


def pattern_rain(grid: LogicalGrid, t: float):
    """Gentle diagonal falling droplets (top-right toward bottom-left)."""
    random.seed(123)
    grid.clear()
    for i in range(7):
        random.seed(i * 89 + int(t * 0.9) * 41)
        offset = (t * 0.6 + i * 1.5) % 11.0
        x = int((offset * 0.7) % 8)
        y = int(7 - (offset * 0.7) % 8)
        x_trail = int(((offset - 1) * 0.7) % 8)
        y_trail = int(7 - ((offset - 1) * 0.7) % 8)

        if 0 <= x < 8 and 0 <= y < 8:
            grid.set_cell(x, y, LogicalColor.AMBER_MED)
        if 0 <= x_trail < 8 and 0 <= y_trail < 8:
            grid.set_cell(x_trail, y_trail, LogicalColor.AMBER_LOW)


def pattern_gradient(grid: LogicalGrid, t: float):
    """Slow diagonal gradient that rotates through amber/red/green tones."""
    angle = t * 0.15
    cx, cy = 3.5, 3.5
    colors = [
        LogicalColor.AMBER_LOW,
        LogicalColor.AMBER_MED,
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
    ("Gradient", pattern_gradient, 30),
]


class ChillRunner:
    def __init__(self, controller, tui_queue: Queue | None = None):
        self.controller = controller
        self.grid = LogicalGrid(8, 8)
        self._pattern_idx = 0
        self._pattern_start = 0.0
        self._leds_on = True
        self._tui_queue = tui_queue

    async def run(self):
        logger.info("Chill mode active — ambient LED patterns")
        self._pattern_start = time.monotonic()

        while True:
            self._check_tui()

            if not self._leds_on:
                self.controller.clear_grid()
                await asyncio.sleep(0.5)
                continue

            t = time.monotonic() - self._pattern_start
            name, pattern_fn, duration = PATTERNS[self._pattern_idx]

            if t >= duration:
                self._pattern_idx = (self._pattern_idx + 1) % len(PATTERNS)
                self._pattern_start = time.monotonic()
                continue

            pattern_fn(self.grid, t)
            await self._commit()
            await asyncio.sleep(0.05)

    def _check_tui(self):
        if self._tui_queue is None:
            return
        try:
            while True:
                msg = self._tui_queue.get_nowait()
                if msg.get("action") == "toggle_leds":
                    self._leds_on = not self._leds_on
                    if not self._leds_on:
                        self.controller.clear_grid()
                    else:
                        self._pattern_start = time.monotonic()
        except Empty:
            pass

    async def _commit(self):
        if not self._leds_on:
            return
        for x, y in self.grid.dirty_cells():
            color = self.grid.get_cell(x, y)
            self.controller.set_grid_color(x, y, color)


async def run_chill_mode(tui_queue: Queue | None = None):
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
    runner = ChillRunner(lp, tui_queue=tui_queue)

    try:
        await runner.run()
    except KeyboardInterrupt:
        pass
    finally:
        lp.clear_grid()
        lp.reset()
        await mm.stop()
