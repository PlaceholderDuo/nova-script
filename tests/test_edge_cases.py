"""
Comprehensive edge-case and stress tests for nova-script modes.
Tests rapid input, state conflicts, mode transitions, and boundary conditions.
"""
import time
import math
from tests.virtualizer import VirtualLaunchpad
from src.layout.grid import LogicalGrid
from src.controllers.base import GridEvent, ControlEvent, EventType, LogicalColor
from src.ui.modes.menu import MenuMode
from src.ui.modes.performance import PerformanceMode
from src.ui.modes.clip_launcher import ClipLauncherMode
from src.ui.mode_manager import ModeManager


def commit(v, grid):
    for x, y in grid.dirty_cells():
        v.controller.set_grid_color(x, y, grid.get_cell(x, y))


def test_menu_edge_cases():
    """Menu mode: outside-block presses, debounce, rapid taps."""
    print("=" * 60)
    print("TEST 1: Menu Edge Cases")
    print("=" * 60)

    v = VirtualLaunchpad()
    grid = LogicalGrid(8, 8)
    grid.set_on_cell_changed(lambda x, y, c: None)
    mgr = ModeManager(grid, v.controller)

    menu = MenuMode(grid, v.controller)
    switched = []
    menu._on_mode_select = lambda m: switched.append(m)
    menu.set_items([
        {"label": "PERF", "mode": "performance", "color": "RED_HIGH", "x": 0, "y": 6, "w": 2, "h": 2},
        {"label": "CLIP", "mode": "clip_launcher", "color": "RED_MED", "x": 2, "y": 6, "w": 2, "h": 2},
        {"label": "SEQ", "mode": "sequencer", "color": "AMBER_HIGH", "x": 4, "y": 6, "w": 2, "h": 2},
        {"label": "MIX", "mode": "mixer", "color": "GREEN_HIGH", "x": 0, "y": 4, "w": 2, "h": 2},
    ])
    mgr.register(menu)
    mgr.switch_to("menu")

    # Test: press outside all blocks
    switched.clear()
    menu.handle_grid_event(GridEvent(6, 0, True, 127))
    assert switched == [], f"Outside press triggered switch: {switched}"
    print("  ✓ Outside-block press ignored")
    time.sleep(0.15)

    # Test: press inside block works
    switched.clear()
    menu.handle_grid_event(GridEvent(5, 7, True, 127))
    assert switched == ["sequencer"], f"Inside press failed: {switched}"
    print("  ✓ Inside-block press → sequencer")
    time.sleep(0.15)

    # Test: corner of 2×2 block
    switched.clear()
    menu.handle_grid_event(GridEvent(0, 6, True, 127))
    assert switched == ["performance"], f"Corner press failed: {switched}"
    print("  ✓ Corner press (0,6) in PERF block → performance")
    time.sleep(0.15)

    # Test: edge of block
    switched.clear()
    menu.handle_grid_event(GridEvent(1, 7, True, 127))
    assert switched == ["performance"], f"Edge press failed: {switched}"
    print("  ✓ Edge press (1,7) in PERF block → performance")
    time.sleep(0.15)

    # Test rapid taps on same block
    switched.clear()
    for _ in range(5):
        menu.handle_grid_event(GridEvent(0, 7, True, 127))
        time.sleep(0.12)
    assert len(switched) == 5, f"Rapid taps count: {len(switched)} (expected 5)"
    print(f"  ✓ Rapid taps (5) → {len(switched)} switches")

    # Test: press empty area between blocks
    switched.clear()
    empty_areas = [(6, 7), (0, 0), (7, 3), (6, 4)]
    for x, y in empty_areas:
        time.sleep(0.15)
        menu.handle_grid_event(GridEvent(x, y, True, 127))
    assert switched == [], f"Empty area press triggered switch: {switched}"
    print(f"  ✓ {len(empty_areas)} empty-area presses all ignored")

    commit(v, grid)
    print(v.render("Menu layout"))
    print()


def test_performance_state_conflicts():
    """Performance: hint + tuner overlap, rapid FX toggles."""
    print("=" * 60)
    print("TEST 2: Performance State Conflicts")
    print("=" * 60)

    v = VirtualLaunchpad()
    grid = LogicalGrid(8, 8)
    grid.set_on_cell_changed(lambda x, y, c: None)

    pm = PerformanceMode(grid, v.controller)
    pm.set_bpm(120)
    pm.set_hints_config(True, "")
    pm.enter()

    # Test: rapid FX toggles (hint should refresh expiry, not overlap)
    for i in range(5):
        pm._toggle_fx(0, i % 5)
    assert pm._hint_letter != "", "Should have active hint"
    print(f"  ✓ Rapid FX toggles: hint='{pm._hint_letter}', active")

    # Test: hint expires after 0.3s
    time.sleep(0.35)
    pm._render()
    assert time.monotonic() >= pm._hint_expiry, "Hint should have expired"
    print("  ✓ Hint expires after 0.3s")

    # Test: enter tuner while hint is active (tuner should override hint)
    pm._toggle_fx(0, 0)
    pm.handle_control_event(ControlEvent(201, 127, EventType.FUNCTION_PRESS))
    assert pm._tuner_state in ("intro", "active", "exit"), f"Tuner not activated: state={pm._tuner_state}"
    commit(v, grid)
    print(f"  ✓ Tuner activates over hint: state={pm._tuner_state}")

    # Test: exiting tuner returns to performance
    time.sleep(2)
    for _ in range(50):
        time.sleep(0.04)
        pm.tick(50)
        pm._render()
        if pm._tuner_state == "active":
            break

    pm.handle_control_event(ControlEvent(201, 127, EventType.FUNCTION_PRESS))
    for _ in range(15):
        time.sleep(0.05)
        pm._render()
        if pm._tuner_state == "off":
            break
    assert pm._tuner_state == "off", f"Tuner not exited: state={pm._tuner_state}"
    print("  ✓ Tuner exit returns to performance correctly")

    commit(v, grid)
    print(v.render("After tuner exit"))
    print()


def test_clip_launcher_stress():
    """Clip Launcher: rapid launch/stop, scene launch, long press."""
    print("=" * 60)
    print("TEST 3: Clip Launcher Stress")
    print("=" * 60)

    v = VirtualLaunchpad()
    grid = LogicalGrid(8, 8)
    grid.set_on_cell_changed(lambda x, y, c: None)

    cl = ClipLauncherMode(grid, v.controller)
    cl.enter()

    # Helper: press + release a clip (with realistic timing)
    def tap(x, y):
        cl.handle_grid_event(GridEvent(x, y, True, 127))
        time.sleep(0.01)
        cl.handle_grid_event(GridEvent(x, y, False, 0))

    tap(0, 1)
    assert len(cl._playing) == 1, f"Should have 1 playing clip, got {len(cl._playing)}"
    print(f"  ✓ Launch clip → {len(cl._playing)} playing")
    time.sleep(0.1)

    tap(0, 2)
    assert len(cl._playing) == 1, f"Should still have 1 playing, got {len(cl._playing)}"
    print(f"  ✓ Same track new clip replaces → {len(cl._playing)} playing")
    time.sleep(0.1)

    tap(0, 2)
    assert len(cl._playing) == 0, f"Should have 0 playing, got {len(cl._playing)}"
    print(f"  ✓ Stop clip → {len(cl._playing)} playing")
    time.sleep(0.1)

    cl.handle_control_event(ControlEvent(100, 127, EventType.FUNCTION_PRESS))
    playing = len(cl._playing)
    assert playing > 0, f"Scene launch should activate clips, got {playing}"
    print(f"  ✓ Scene launch → {playing} clips playing")

    cl.handle_grid_event(GridEvent(0, 0, True, 127))
    for idx in list(cl._playing):
        if idx % 8 == 0:
            assert False, f"Track 0 should have no playing clips, got idx={idx}"
    print(f"  ✓ Track stop → playing={len(cl._playing)}")

    cl.handle_grid_event(GridEvent(3, 3, True, 127))
    time.sleep(0.6)
    cl.handle_grid_event(GridEvent(3, 3, False, 0))
    cl._render()
    print("  ✓ Long press → clear clip (no crash)")

    cl._playing.clear()
    for i in range(4):
        time.sleep(0.1)
        tap(i, 2)
    assert len(cl._playing) == 4, f"Rapid launches: {len(cl._playing)} (expected 4)"
    print(f"  ✓ Rapid launches (4 tracks) → {len(cl._playing)} playing")

    commit(v, grid)
    print(v.render("Clip Launcher"))
    print()


def test_grid_bounds_and_long_press():
    """Grid coordinate bounds, long press across modes."""
    print("=" * 60)
    print("TEST 4: Grid Bounds & Long Press")
    print("=" * 60)

    v = VirtualLaunchpad()
    grid = LogicalGrid(8, 8)
    grid.set_on_cell_changed(lambda x, y, c: None)

    # Test: grid out-of-bounds writes silently ignored
    v.controller.set_grid_color(-1, 0, LogicalColor.AMBER_HIGH)
    v.controller.set_grid_color(8, 0, LogicalColor.RED_HIGH)
    v.controller.set_grid_color(0, -1, LogicalColor.GREEN_HIGH)
    v.controller.set_grid_color(0, 8, LogicalColor.RED_HIGH)
    print("  ✓ Out-of-bounds LED writes silently ignored")

    # Test: control event IDs in valid ranges
    cl = ClipLauncherMode(grid, v.controller)
    cl.enter()
    cl.handle_control_event(ControlEvent(107, 127, EventType.FUNCTION_PRESS))  # right col bottom
    cl.handle_control_event(ControlEvent(100, 127, EventType.FUNCTION_PRESS))  # right col top
    assert len(cl._playing) > 0, "Scene launch should work"
    print("  ✓ Right column scene launch (both ends)")

    # Test: long press detection in Mode base class
    from src.ui.mode import Mode

    class TestMode(Mode):
        def enter(self): pass
        def exit(self): pass
        def handle_grid_event(self, e):
            if e.pressed:
                self.track_press(e)
            else:
                r = self.resolve_press(e)
                if r == "long":
                    self._results.append("long")
                elif r == "short":
                    self._results.append("short")
        _results = []

    tm = TestMode("test", grid, v.controller)
    tm._results = []

    tm.handle_grid_event(GridEvent(2, 2, True, 127))
    time.sleep(0.01)
    tm.handle_grid_event(GridEvent(2, 2, False, 0))
    assert tm._results == ["short"], f"Short press: {tm._results}"
    print("  ✓ Short press → 'short'")

    # Long press
    tm._results.clear()
    tm.handle_grid_event(GridEvent(2, 2, True, 127))
    time.sleep(0.55)
    tm.handle_grid_event(GridEvent(2, 2, False, 0))
    assert tm._results == ["long"], f"Long press: {tm._results}"
    print("  ✓ Long press (550ms) → 'long'")

    # Cross-pad drag (press on one, release on another)
    tm._results.clear()
    tm.handle_grid_event(GridEvent(2, 2, True, 127))
    time.sleep(0.02)
    tm.handle_grid_event(GridEvent(5, 5, False, 0))
    assert tm._results == [], f"Cross-pad drag: {tm._results}"
    print("  ✓ Cross-pad drag → 'invalid' (ignored)")

    # Debounce
    tm._results.clear()
    tm._debounce_ms = 80
    assert not tm.is_debounced(), "First call never debounced"
    assert tm.is_debounced(), "Second call within 80ms should be debounced"
    time.sleep(0.1)
    assert not tm.is_debounced(), "After 100ms, debounce should clear"
    print("  ✓ Debounce: first free, second blocked, clears after 100ms")
    print()


def test_menu_top_row_shortcuts():
    """Top-row button shortcuts work from menu blocks."""
    print("=" * 60)
    print("TEST 5: Top-Row Shortcuts")
    print("=" * 60)

    v = VirtualLaunchpad()
    grid = LogicalGrid(8, 8)
    grid.set_on_cell_changed(lambda x, y, c: None)
    mgr = ModeManager(grid, v.controller)

    menu = MenuMode(grid, v.controller)
    menu.set_items([
        {"label": "PERF", "mode": "performance", "color": "RED_HIGH", "x": 0, "y": 6, "w": 2, "h": 2},
        {"label": "CLIP", "mode": "clip_launcher", "color": "RED_MED", "x": 2, "y": 6, "w": 2, "h": 2},
    ])
    switched = []
    menu._on_mode_select = lambda m: switched.append(m)
    mgr.register(menu)
    mgr.switch_to("menu")

    switched.clear()
    menu.handle_control_event(ControlEvent(201, 127, EventType.FUNCTION_PRESS))
    assert switched == ["clip_launcher"], f"Top-2 → second item: {switched}"
    print("  ✓ Top-row Button 2 → second menu item (Btn1=Home, Btn2=2nd item)")

    switched.clear()
    menu.handle_control_event(ControlEvent(202, 127, EventType.FUNCTION_PRESS))
    assert switched == [], f"Top-3 with 2 items → nothing: {switched}"
    print("  ✓ Top-row Button 3 → out of range (only 2 items) → nothing")
    print()


def test_hint_letter_rendering():
    """All FX first letters render as valid 5x5 characters."""
    print("=" * 60)
    print("TEST 6: Hint Letter Rendering")
    print("=" * 60)

    from src.ui.modes.message import FONT_5X5

    fx_names = ["Rev", "Dly", "Chor", "Hrm↑"]
    for name in fx_names:
        letter = name[0]
        assert letter in FONT_5X5, f"Missing font char: '{letter}'"
    print("  ✓ All FX first letters exist in font")

    # Special character check
    assert "R" in FONT_5X5, "Missing 'R'"
    assert "D" in FONT_5X5, "Missing 'D'"
    assert "C" in FONT_5X5, "Missing 'C'"
    assert "H" in FONT_5X5, "Missing 'H'"
    print("  ✓ R/D/C/H all in font")

    # Render each letter and verify it produces lit cells
    v = VirtualLaunchpad()
    for letter in ["R", "D", "C", "H"]:
        v.grid.clear()
        pm = PerformanceMode(LogicalGrid(8, 8), v.controller)
        pm._render_letter(letter, LogicalColor.GREEN_HIGH)
        lit = sum(1 for y in range(8) for x in range(8)
                  if pm.grid.get_cell(x, y) != LogicalColor.OFF)
        assert lit > 0, f"Letter '{letter}' produced 0 lit cells"
    print(f"  ✓ All 4 FX letters produce visible output")
    print()


def test_grid_rendering_clean():
    """After each mode operation, dirty cells are properly tracked."""
    print("=" * 60)
    print("TEST 7: Grid Clean Rendering")
    print("=" * 60)

    grid = LogicalGrid(8, 8)
    grid.set_on_cell_changed(lambda x, y, c: None)

    grid.clear()
    dirty = grid.dirty_cells()
    assert len(dirty) == 64, f"Clear should dirty all 64 cells, got {len(dirty)}"
    print(f"  ✓ Clear dirties all 64 cells")

    consumed = grid.dirty_cells()
    assert len(consumed) == 0, f"Second dirty call should return 0, got {len(consumed)}"
    print("  ✓ Dirty cells consumed on second read")

    grid.set_cell(3, 3, LogicalColor.AMBER_HIGH)
    dirty = grid.dirty_cells()
    assert len(dirty) == 1 and (3, 3) in dirty, f"Single cell: {dirty}"
    print("  ✓ Single cell set dirties 1 cell")

    # Fill rect
    grid.clear()
    _ = grid.dirty_cells()
    grid.fill_rect(1, 1, 3, 3, LogicalColor.GREEN_HIGH)
    dirty = grid.dirty_cells()
    assert len(dirty) == 9, f"3×3 rect should dirty 9 cells, got {len(dirty)}"
    print(f"  ✓ fill_rect dirties {len(dirty)} cells")
    print()


def run_all_tests():
    test_menu_edge_cases()
    test_performance_state_conflicts()
    test_clip_launcher_stress()
    test_grid_bounds_and_long_press()
    test_menu_top_row_shortcuts()
    test_hint_letter_rendering()
    test_grid_rendering_clean()
    print("=" * 60)
    print("ALL EDGE-CASE TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
