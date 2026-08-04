"""Fireworks particle system unit tests."""
from src.ui.fireworks import Fireworks
from src.controllers.color_map import LogicalColor
from src.layout.grid import LogicalGrid


def test():
    fw = Fireworks(bpm=240, bars=1)
    fw.start()

    grid = LogicalGrid(8, 8)
    frames = particles = 0

    for i in range(60):
        now = fw._start_time + i * 0.05
        active = fw.tick(now)
        fw.render(grid)

        for y in range(8):
            for x in range(8):
                color = grid.get_cell(x, y)
                assert isinstance(color, LogicalColor), f"Invalid color at ({x},{y}): {color}"

        if fw._particles:
            particles += 1
        frames += 1
        if not active:
            break

    print(f"✓ Fireworks simulated {frames} frames, particles in {particles}")
    print(f"  Total bursts: {fw._beat_count}")

    fw.render(grid)
    empty = sum(1 for y in range(8) for x in range(8) if grid.get_cell(x, y) == LogicalColor.OFF)
    print(f"  Final grid: {empty}/64 cells OFF")
    assert empty == 64, f"Grid not clean: {64 - empty} cells still lit"

    fw = Fireworks(bpm=120, bars=1)
    fw.start()
    for i in range(200):
        active = fw.tick(fw._start_time + i * 0.05)
        if not active:
            break
    fw.render(grid)
    empty = sum(1 for y in range(8) for x in range(8) if grid.get_cell(x, y) == LogicalColor.OFF)
    print(f"  Full sim grid: {empty}/64 cells OFF")
    assert empty == 64

    print("\n=== FIREWORKS TESTS PASSED ===")


if __name__ == "__main__":
    test()
