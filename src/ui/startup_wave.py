"""
Startup wave — bidirectional diagonal ripple that sweeps 3× across the grid.
Bottom-left → top-right → back to bottom-left → repeats 3×. ~5 seconds total.
"""
import math
import time
import logging
from src.controllers.color_map import LogicalColor
from src.layout.grid import LogicalGrid

logger = logging.getLogger(__name__)

PASS_DURATION = 0.4
TOTAL_PASSES = 3
TRAIL_LENGTH = 4
FRAME_MS = 0.03
SLEEP_MS = 0.0


class StartupWave:
    def __init__(self, grid: LogicalGrid, controller):
        self.grid = grid
        self.controller = controller
        self._start = 0.0
        self._done = False

    def start(self):
        self._start = time.monotonic()
        self._done = False
        logger.info(f"Startup wave: bidirectional 3× sweep (~{PASS_DURATION * TOTAL_PASSES:.1f}s)")

    def tick(self) -> bool:
        if self._done:
            return False

        now = time.monotonic()
        elapsed = now - self._start
        total = PASS_DURATION * TOTAL_PASSES

        if elapsed >= total:
            self.grid.clear()
            self._commit()
            self._done = True
            return False

        pass_idx = int(elapsed / PASS_DURATION)
        pass_elapsed = elapsed - pass_idx * PASS_DURATION
        forward = (pass_idx % 2 == 0)

        lead = int(pass_elapsed / 0.015)

        colors = []
        for band in range(max(0, lead - TRAIL_LENGTH), lead + 1):
            dist = lead - band
            if dist <= 1:
                color = LogicalColor.AMBER_HIGH
            elif dist <= 2:
                color = LogicalColor.GREEN_HIGH
            elif dist <= 3:
                color = LogicalColor.RED_HIGH
            else:
                color = LogicalColor.RED_LOW

            if forward:
                total_pos = band
            else:
                total_pos = 14 - band

            for x in range(max(0, total_pos - 7), min(7, total_pos) + 1):
                y = total_pos - x
                if 0 <= x < 8 and 0 <= y < 8:
                    colors.append((x, y, color))

        self.grid.clear()
        for x, y, color in colors:
            self.grid.set_cell(x, y, color)
        self._commit()
        return True

    def _commit(self):
        for x, y in self.grid.dirty_cells():
            self.controller.set_grid_color(x, y, self.grid.get_cell(x, y))
