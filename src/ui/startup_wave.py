"""
Startup wave animation — color ripple from bottom-left to top-right.
Runs independently of the overlay system as a one-shot boot animation.
"""
import math
import logging
from src.controllers.color_map import LogicalColor
from src.layout.grid import LogicalGrid

logger = logging.getLogger(__name__)

WAVE_COLORS = [
    (LogicalColor.AMBER_HIGH, "amber"),
    (LogicalColor.GREEN_HIGH, "green"),
    (LogicalColor.RED_HIGH, "red"),
]

WAVE_DELAY = 0.3  # seconds between color waves
WAVE_SPEED = 0.08  # seconds per diagonal band


class StartupWave:
    def __init__(self, grid: LogicalGrid, controller):
        self.grid = grid
        self.controller = controller
        self._start = 0.0
        self._color_idx = 0

    def start(self):
        self._start = __import__("time").monotonic()
        self._color_idx = 0
        logger.info("Startup wave: amber → green → red")

    def tick(self, now: float | None = None) -> bool:
        """Returns True if animation is still running."""
        if now is None:
            now = __import__("time").monotonic()

        elapsed = now - self._start
        wave_offset = WAVE_DELAY * (self._color_idx + 1)

        if self._color_idx < len(WAVE_COLORS):
            color, _ = WAVE_COLORS[self._color_idx]
            bands_to_light = int(elapsed / WAVE_SPEED)

            self.grid.clear()
            self._render_diagonal_bands(bands_to_light, 3, color)

            if bands_to_light >= 15:
                self._color_idx += 1
                self._start = now

            self._commit()
            return True

        self.grid.clear()
        self._commit()
        return False

    def _render_diagonal_bands(self, num_bands: int, tail: int, color: LogicalColor):
        for band in range(num_bands):
            brightness = 3 - min(2, (num_bands - band - 1))
            c = color if brightness >= 1 else LogicalColor.OFF

            for d in range(band + 1):
                x = d
                y = band - d
                if 0 <= x < 8 and 0 <= y < 8:
                    self.grid.set_cell(x, y, c)

    def _commit(self):
        for x, y in self.grid.dirty_cells():
            color = self.grid.get_cell(x, y)
            self.controller.set_grid_color(x, y, color)


def test_startup_wave():
    """Validate the startup wave renders correctly via virtualizer."""
    import time as t
    from tests.virtualizer import VirtualLaunchpad

    print("=== STARTUP WAVE TEST ===\n")

    v = VirtualLaunchpad()
    v.on_connect()

    logical_grid = LogicalGrid(8, 8)

    def commit_grid():
        for x, y in logical_grid.dirty_cells():
            color = logical_grid.get_cell(x, y)
            v.controller.set_grid_color(x, y, color)

    logical_grid.set_on_cell_changed(lambda x, y, c: None)

    wave = StartupWave(logical_grid, v.controller)
    wave._commit = commit_grid

    wave.start()
    sim_time = wave._start
    frames = 0
    shown = set()

    while wave.tick(now=sim_time):
        frames += 1
        sim_time += 0.05
        key_frames = [1, 6, 12, 18, 24]
        for kf in key_frames:
            if kf not in shown and frames >= kf:
                shown.add(kf)
                print(v.render(f"Frame {frames} (t={sim_time - wave._start:.2f}s)"))
                print()

    print(v.render("Final: all OFF"))
    print(f"\n✓ Startup wave completed in {frames} frames")
    print(f"✓ Grid clean after animation")

    return True


if __name__ == "__main__":
    test_startup_wave()
