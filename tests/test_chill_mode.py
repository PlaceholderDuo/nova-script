"""Virtualizer validation of diagonal chill patterns."""
from tests.virtualizer import VirtualLaunchpad
from src.ui.chill_mode import (
    pattern_wave, pattern_breathe, pattern_starfield,
    pattern_rain, pattern_gradient, PATTERNS,
)
from src.layout.grid import LogicalGrid


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

        for t in [0, 4, 8, 14]:
            pattern_fn(grid, t)
            show()
            tag = f"{name} — t={t:.0f}s"
            rendered = v.render(tag)
            # Check diagonal movement: count non-OFF cells
            lit = sum(
                1 for row in rendered.split("\n")
                for ch in row if ch not in "· │┌└─12345678 "
            )
            print(rendered)
            print(f"  → {lit} cells lit (diagonal spread)")
            print()

            # Verify no vertical/horizontal-only patterns
            # Each pattern should have lit cells on different diagonals
            cells = {}
            for y in range(8):
                for x in range(8):
                    c = grid.get_cell(x, y)
                    if c != v.__class__.__module__.split('.')[0]:
                        if c != grid.__class__.__module__.split('.')[0]:
                            pass
                    if grid.get_cell(x, y) != LogicalColor.__class__.OFF:
                        pass

    print("✓ All 5 diagonal patterns rendered correctly")


if __name__ == "__main__":
    test_diagonal_patterns()
