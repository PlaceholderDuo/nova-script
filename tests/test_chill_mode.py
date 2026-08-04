"""Virtualizer test for chill mode patterns."""
import math
from tests.virtualizer import VirtualLaunchpad
from src.ui.chill_mode import (
    pattern_wave, pattern_breathe, pattern_starfield,
    pattern_rain, pattern_gradient_spin, PATTERNS,
)
from src.layout.grid import LogicalGrid


def test_all_patterns():
    print("=== CHILL MODE PATTERNS ===\n")

    v = VirtualLaunchpad()
    grid = LogicalGrid(8, 8)

    def commit():
        for x, y in grid.dirty_cells():
            color = grid.get_cell(x, y)
            v.controller.set_grid_color(x, y, color)

    for name, pattern_fn, duration in PATTERNS:
        print(f"\n{'='*50}")
        print(f"  {name} (duration: {duration}s)")
        print(f"{'='*50}")

        for step in range(4):
            t = step * (duration / 4)
            pattern_fn(grid, t)
            commit()
            print(v.render(f"  {name} — t={t:.1f}s"))
            print()


if __name__ == "__main__":
    test_all_patterns()
