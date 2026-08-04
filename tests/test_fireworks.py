"""Fireworks particle system test for 8×8 Launchpad grid."""
import math
import random
import time
from dataclasses import dataclass
from src.controllers.color_map import LogicalColor


@dataclass
class Particle:
    x: float
    y: float
    vy: float
    brightness: int  # 0-3
    lifetime: float  # seconds remaining
    max_lifetime: float
    color_index: int  # 0=red, 1=amber, 2=green


FIREWORK_COLORS = [
    [LogicalColor.RED_HIGH, LogicalColor.RED_MED, LogicalColor.RED_LOW],
    [LogicalColor.AMBER_HIGH, LogicalColor.AMBER_MED, LogicalColor.AMBER_LOW],
    [LogicalColor.GREEN_HIGH, LogicalColor.GREEN_MED, LogicalColor.GREEN_LOW],
]


class Fireworks:
    def __init__(self, bpm: float = 120.0, bars: int = 8):
        self._bpm = bpm
        self._bars = bars
        self._beat_interval = 60.0 / bpm  # seconds per beat
        self._particles: list[Particle] = []
        self._last_beat = 0.0
        self._beat_count = 0
        self._max_beats = bars * 4  # 4 beats per bar in 4/4
        self._color_cycle = 0
        self._start_time = 0.0
        self._trail: dict[tuple[int, int], float] = {}  # (x,y) → age

    def start(self):
        self._start_time = time.monotonic()
        self._last_beat = self._start_time
        self._beat_count = 0
        self._particles.clear()
        self._trail.clear()

    def tick(self, now: float | None = None) -> bool:
        """Returns True if fireworks are still active."""
        if now is None:
            now = time.monotonic()

        elapsed = now - self._start_time
        total_beats = elapsed / self._beat_interval

        while self._beat_count < total_beats and self._beat_count < self._max_beats:
            self._burst()
            self._beat_count += 1
            self._last_beat = now

        dt = 0.05
        self._update_particles(dt)

        active = self._beat_count < self._max_beats or len(self._particles) > 0
        if not active:
            self._trail.clear()
        return active

    def _burst(self):
        count = random.randint(3, 6)
        color = self._color_cycle % 3
        self._color_cycle += 1

        for _ in range(count):
            x = random.uniform(0, 7.5)
            y = random.uniform(0, 1.5)
            vy = random.uniform(8.0, 15.0)
            lifetime = random.uniform(0.3, 0.9)

            p = Particle(
                x=x,
                y=y,
                vy=vy,
                brightness=3,
                lifetime=lifetime,
                max_lifetime=lifetime,
                color_index=color,
            )
            self._particles.append(p)

    def _update_particles(self, dt: float):
        gravity = -12.0

        for p in self._particles[:]:
            p.vy += gravity * dt
            p.y += p.vy * dt
            p.lifetime -= dt

            # Trail: mark previous position
            px = int(p.x)
            py = int(p.y)
            if 0 <= px < 8 and 0 <= py < 8:
                self._trail[(px, py)] = 0.15

            if p.y < -1 or p.lifetime <= 0:
                self._particles.remove(p)

        # Fade trails
        for key in list(self._trail.keys()):
            self._trail[key] -= dt
            if self._trail[key] <= 0:
                del self._trail[key]

    def render(self, grid):
        """Render particles + trails to a LogicalGrid."""
        grid.clear()

        for (x, y), age in self._trail.items():
            if 0 <= x < 8 and 0 <= y < 8:
                grid.set_cell(x, y, LogicalColor.RED_LOW)

        for p in self._particles:
            x = int(p.x)
            y = int(p.y)
            if 0 <= x < 8 and 0 <= y < 8:
                life_ratio = p.lifetime / p.max_lifetime
                bright_idx = min(2, int(life_ratio * 3))
                color = FIREWORK_COLORS[p.color_index][bright_idx]
                grid.set_cell(x, y, color)


def test_particle_system():
    """Validate the fireworks render correctly in a unit test."""
    from src.layout.grid import LogicalGrid

    fw = Fireworks(bpm=240, bars=1)  # fast BPM for testing
    fw.start()

    grid = LogicalGrid(8, 8)
    frames = 0
    particles_seen = 0

    # Simulate 3 seconds at 20fps
    for i in range(60):
        now = fw._start_time + i * 0.05
        active = fw.tick(now)
        fw.render(grid)

        # Check that each frame has valid colors
        for y in range(8):
            for x in range(8):
                color = grid.get_cell(x, y)
                assert isinstance(color, LogicalColor), f"Invalid color at ({x},{y}): {color}"

        if fw._particles:
            particles_seen += 1
        frames += 1

        if not active:
            break

    print(f"✓ Fireworks simulated {frames} frames, particles in {particles_seen}")
    print(f"  Total bursts: {fw._beat_count}, max particles: {fw._max_beats}")
    print(f"  Trail cells: {len(fw._trail)}")

    # After simulation, grid should be clean
    fw.render(grid)
    empty = 0
    for y in range(8):
        for x in range(8):
            if grid.get_cell(x, y) == LogicalColor.OFF:
                empty += 1
    print(f"  Final grid: {empty}/64 cells OFF (should be 64)")
    assert empty == 64, f"Grid not clean after fireworks: {64 - empty} cells still lit"

    # Test: trail should fade to zero
    fw = Fireworks(bpm=120, bars=1)
    fw.start()
    for i in range(200):
        active = fw.tick(fw._start_time + i * 0.05)
        if not active:
            break
    fw.render(grid)
    empty = sum(1 for y in range(8) for x in range(8) if grid.get_cell(x, y) == LogicalColor.OFF)
    print(f"  Final full-sim grid: {empty}/64 cells OFF (should be 64)")
    assert empty == 64

    print("\n=== FIREWORKS UNIT TESTS PASSED ===")


if __name__ == "__main__":
    test_particle_system()
