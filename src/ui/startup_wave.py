"""
Startup wave — single continuous wave with amber→green→red chasing.
"""
import math
import logging
from src.controllers.color_map import LogicalColor
from src.layout.grid import LogicalGrid

logger = logging.getLogger(__name__)


class StartupWave:
    def __init__(self, grid: LogicalGrid, controller):
        self.grid = grid
        self.controller = controller
        self._start = 0.0
        self._done = False

    def start(self):
        self._start = __import__("time").monotonic()
        self._done = False
        logger.info("Startup wave: amber → green → red")

    def tick(self, now: float | None = None) -> bool:
        if now is None:
            now = __import__("time").monotonic()
        if self._done:
            return False

        elapsed = now - self._start
        lead_band = int(elapsed / 0.04)
        total = 18

        if lead_band >= total + 6:
            self.grid.clear()
            self._commit()
            self._done = True
            return False

        self.grid.clear()

        for band in range(max(0, lead_band - 6), lead_band + 1):
            distance = lead_band - band
            if distance <= 1:
                color = LogicalColor.AMBER_HIGH
            elif distance <= 2:
                color = LogicalColor.AMBER_MED
            elif distance <= 3:
                color = LogicalColor.GREEN_HIGH
            elif distance <= 4:
                color = LogicalColor.GREEN_MED
            elif distance <= 5:
                color = LogicalColor.RED_HIGH
            else:
                color = LogicalColor.RED_LOW

            for x in range(band + 1):
                y = band - x
                if 0 <= x < 8 and 0 <= y < 8:
                    existing = self.grid.get_cell(x, y)
                    if existing == LogicalColor.OFF:
                        self.grid.set_cell(x, y, color)

        self._commit()
        return True

    def _commit(self):
        for x in range(8):
            for y in range(8):
                self.controller.set_grid_color(x, y, self.grid.get_cell(x, y))
