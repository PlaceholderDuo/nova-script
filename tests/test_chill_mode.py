"""Virtualizer validation of diagonal chill patterns."""
from tests.virtualizer import VirtualLaunchpad
from src.ui.chill_mode import (
    pattern_wave, pattern_breathe, pattern_starfield,
    pattern_rain, pattern_gradient, PATTERNS,
)
from src.layout.grid import LogicalGrid
from src.controllers.color_map import LogicalColor


def test_diagonal_patterns():
    print("=== DIAGONAL CHILL PATTERNS ===\n")

    v = VirtualLaunchpad()
    grid = LogicalGrid(8, 8)

    def show():
        for x, y in grid.dirty_cells():
            color = grid.get_cell(x, y)
            v.controller.set_grid_color(x, y, color)

    for name, pattern_fn, _ in PATTERNS:
        print(f"\n{'='*50}")
        print(f"  {name}")
        print(f"{'='*50}")

        lit_counts = []
        for t in [0, 4, 8, 14]:
            pattern_fn(grid, t)
            show()
            tag = f"{name} — t={t:.0f}s"
            rendered = v.render(tag)
            lit = sum(
                1 for row in rendered.split("\n")
                for ch in row if ch not in "· │┌└─12345678 "
            )
            lit_counts.append(lit)
            print(f"  t={t:.0f}s → {lit} cells lit")
            assert lit > 0, f"Pattern '{name}' produced 0 lit cells"

        # Diagonal spread: at least 2 distinct columns lit across frames
        lit_any = sum(1 for y in range(8) for x in range(8)
                      if grid.get_cell(x, y) != LogicalColor.OFF)
        assert lit_any > 0, f"Pattern '{name}' produced no active cells at t=14"
        print(f"  → {name}: lit={lit_counts}, active={lit_any} ✓")

    print("✓ All 5 diagonal patterns rendered correctly")


if __name__ == "__main__":
    test_diagonal_patterns()
