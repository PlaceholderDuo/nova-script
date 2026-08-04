"""
Startup wave animation — color ripple from bottom-left to top-right.
Overlapping colors with brightness fade for smooth trailing effect.
"""
import math
import logging
from src.controllers.color_map import LogicalColor
from src.layout.grid import LogicalGrid

logger = logging.getLogger(__name__)

WAVE_COLORS = [
    (LogicalColor.AMBER_HIGH, LogicalColor.AMBER_MED, LogicalColor.AMBER_LOW),
    (LogicalColor.GREEN_HIGH, LogicalColor.GREEN_MED, LogicalColor.GREEN_LOW),
    (LogicalColor.RED_HIGH, LogicalColor.RED_MED, LogicalColor.RED_LOW),
]

WAVE_SPEED = 0.06  # seconds per diagonal band


class StartupWave:
    def __init__(self, grid: LogicalGrid, controller):
        self.grid = grid
        self.controller = controller
        self._start = 0.0

    def start(self):
        self._start = __import__("time").monotonic()
        logger.info("Startup wave: amber → green → red")

    def tick(self, now: float | None = None) -> bool:
        """Returns True if animation is still running."""
        if now is None:
            now = __import__("time").monotonic()

        elapsed = now - self._start
        total_bands = 15  # max diagonal bands (0 through 14)
        bands_per_color = total_bands + 10  # each color wave spans ~25 bands
        total_duration = bands_per_color * WAVE_SPEED * 3 + WAVE_SPEED * 5

        if elapsed >= total_duration:
            self.grid.clear()
            self._commit()
            return False

        self.grid.clear()

        for ci, (high, med, low) in enumerate(WAVE_COLORS):
            color_offset = ci * 6  # stagger colors by 6 bands
            lead = int((elapsed - color_offset * WAVE_SPEED) / WAVE_SPEED)
            for band in range(max(0, lead - 4), lead + 1):
                pos = band - lead + 4
                if pos <= 1:
                    c = high
                elif pos <= 2:
                    c = med
                elif pos <= 4:
                    c = low
                else:
                    c = LogicalColor.OFF

                for d in range(band + 1):
                    x = d
                    y = band - d
                    if 0 <= x < 8 and 0 <= y < 8:
                        existing = self.grid.get_cell(x, y)
                        if existing == LogicalColor.OFF or c != LogicalColor.OFF:
                            if c != LogicalColor.OFF:
                                self.grid.set_cell(x, y, c)

        self._commit()
        return True

    def _commit(self):
        for x, y in self.grid.dirty_cells():
            color = self.grid.get_cell(x, y)
            self.controller.set_grid_color(x, y, color)
