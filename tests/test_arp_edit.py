"""
Unit test for ARP Edit Mode — grid editing, beat chase, slot selection.
"""
import sys
import time
sys.path.insert(0, ".")

from src.ui.modes.arp_edit import (ArpEditMode, _load_pattern_from_slot,
                                    _save_pattern_to_slot, _slot_has_pattern,
                                    STEP_COUNT, FACTORY_SLOTS, DEFAULT_LENGTH,
                                    _slot_file_name)
from src.controllers.base import GridEvent, LogicalColor


class MockGrid:
    def __init__(self):
        self._cells = {}
        self._dirty = set()

    def set_cell(self, x, y, c):
        self._cells[(x, y)] = c
        self._dirty.add((x, y))

    def get_cell(self, x, y):
        return self._cells.get((x, y), LogicalColor.OFF)

    def get(self, x, y):
        return self._cells.get((x, y), LogicalColor.OFF)

    def clear(self):
        self._cells.clear()
        self._dirty.clear()

    def dirty_cells(self):
        d = list(self._dirty)
        self._dirty.clear()
        return d


class MockController:
    def __init__(self):
        self.right_leds = {}
        self.top_leds = {}

    def send_right_column_led(self, i, c):
        self.right_leds[i] = c

    def send_top_row_led(self, i, c):
        self.top_leds[i] = c

    def set_grid_color(self, x, y, c):
        pass


def g_press(x, y):
    return GridEvent(x, y, True)


def test_pattern_editing():
    print("=== Pattern Editing ===")
    grid = MockGrid()
    ctrl = MockController()
    mode = ArpEditMode(grid, ctrl)
    mode.set_state(
        intervals=[0, 2, 4, 5, 7, 4, 2, 0],
        lengths=[5] * STEP_COUNT,
        pattern_name="normal",
        current_slot=1,
        scale_intervals=[0, 2, 4, 5, 7, 9, 11],
        root_note=62,
        bpm=120,
        diatonic=True,
    )
    mode.enter()
    mode._render()

    assert mode._intervals == [0, 2, 4, 5, 7, 4, 2, 0]
    print("  Initial intervals: [0, 2, 4, 5, 7, 4, 2, 0] ✓")

    mode.handle_grid_event(g_press(0, 4))
    mode._render()
    assert mode._intervals[0] == 3, f"Step 0 row 4 → interval 3, got {mode._intervals[0]}"
    print(f"  Step 0 row 4 press → interval 3 ✓")

    mode.handle_grid_event(g_press(0, 4))
    mode._render()
    assert mode._intervals[0] == -1, f"Same cell press clears to skip (-1), got {mode._intervals[0]}"
    print("  Same cell press → clears to skip (-1) ✓")

    mode.handle_grid_event(g_press(3, 7))
    mode._render()
    assert mode._intervals[3] == 6, f"Step 3 row 7 press → interval 6, got {mode._intervals[3]}"
    print("  Step 3 row 7 press → interval 6 ✓")


def test_beat_chase():
    print("\n=== Beat Chase ===")
    grid = MockGrid()
    ctrl = MockController()
    mode = ArpEditMode(grid, ctrl)
    mode.set_state(
        intervals=[0, 2, 4, 5, 7, 4, 2, 0],
        lengths=[5] * STEP_COUNT,
        pattern_name="normal",
        current_slot=1,
        scale_intervals=[0, 2, 4, 5, 7, 9, 11],
        root_note=62,
        bpm=120,
        diatonic=True,
    )
    mode.enter()
    mode._entry_time = time.monotonic() - 1.0
    mode.tick(100)
    mode._render()

    step = mode._beat_step
    assert 0 <= step < 8, f"Beat step should be 0-7, got {step}"
    for s in range(8):
        expected = LogicalColor.AMBER_HIGH if s == step else LogicalColor.AMBER_LOW
        assert grid.get_cell(s, 0) == expected, f"Step {s} row 0: expected {expected.name}, got {grid.get_cell(s, 0).name}"
    print(f"  Beat position: step {step} ✓")


def test_slot_navigation():
    print("\n=== Slot Navigation ===")
    grid = MockGrid()
    ctrl = MockController()
    mode = ArpEditMode(grid, ctrl)
    mode.set_state(
        intervals=[0, 2, 4, 5, 7, 4, 2, 0],
        lengths=[5] * STEP_COUNT,
        pattern_name="normal",
        current_slot=1,
        scale_intervals=[0, 2, 4, 5, 7, 9, 11],
        root_note=62,
        bpm=120,
        diatonic=True,
    )
    mode.enter()
    mode._render()

    assert mode._arp_page == 0
    assert mode._current_slot == 1
    print(f"  Initial: page {mode._arp_page}, slot {mode._current_slot} ✓")

    slots_page1 = [1, 2, 3, 4, 5, 6, 7, 8]
    assert mode._handle_slot_select(4) is True, "Select slot 4 should return True (changed)"
    print(f"  Selected slot 4, pattern_name={mode._pattern_name} ✓")

    assert mode._handle_slot_select(4) is False, "Re-select slot 4 should return False (no change)"
    print("  Re-select same slot → no-op ✓")


def test_note_length_mode():
    print("\n=== Note-Length Mode ===")
    grid = MockGrid()
    ctrl = MockController()
    mode = ArpEditMode(grid, ctrl)
    mode.set_state(
        intervals=[0, 2, 4, 5, 7, 4, 2, 0],
        lengths=[5, 5, 3, 5, 5, 5, 5, 5],
        pattern_name="normal",
        current_slot=1,
        scale_intervals=[0, 2, 4, 5, 7, 9, 11],
        root_note=62,
        bpm=120,
        diatonic=True,
    )
    mode.enter()

    assert mode._note_length_mode is False
    from src.ui.modes.arp_edit import RIGHT_E

    mode.handle_control_event(type('E', (), {
        'control_id': 100 + RIGHT_E,
        'event_type': type('T', (), {'name': 'RIGHT_COLUMN_PRESS'})(),
        'pressed': True,
    })())
    mode._render()
    assert mode._note_length_mode is True, "E press should enter note-length mode"
    print("  E press → note-length mode ON ✓")

    mode.handle_grid_event(g_press(0, 1))
    mode._render()
    assert mode._lengths[0] == 2, f"Step 0 y=1 → length 2, got {mode._lengths[0]}"
    print("  Step 0 y=1 press → length 2 ✓")

    mode.handle_grid_event(g_press(3, 7))
    mode._render()
    assert mode._lengths[3] == 8, f"Step 3 y=7 press → length 8, got {mode._lengths[3]}"
    print("  Step 3 y=7 press → length 8 ✓")

    mode.handle_control_event(type('E', (), {
        'control_id': 100 + RIGHT_E,
        'event_type': type('T', (), {'name': 'RIGHT_COLUMN_PRESS'})(),
        'pressed': True,
    })())
    assert mode._note_length_mode is False, "E press in note-length → exit"
    print("  E press again → note-length mode OFF ✓")


def test_global_note_length_set():
    print("\n=== Global Note-Length Set ===")
    grid = MockGrid()
    ctrl = MockController()
    mode = ArpEditMode(grid, ctrl)
    mode.set_state(
        intervals=[0, 2, 4, 5, 7, 4, 2, 0],
        lengths=[3, 5, 3, 5, 3, 5, 3, 5],
        pattern_name="normal",
        current_slot=1,
        scale_intervals=[0, 2, 4, 5, 7, 9, 11],
        root_note=62,
        bpm=120,
        diatonic=True,
    )
    mode.enter()
    mode._note_length_mode = True

    from src.ui.modes.arp_edit import RIGHT_C
    mode.handle_control_event(type('E', (), {
        'control_id': 100 + RIGHT_C,
        'event_type': type('T', (), {'name': 'RIGHT_COLUMN_PRESS'})(),
        'pressed': True,
    })())
    mode._render()
    assert mode._lengths == [3] * STEP_COUNT, f"C button (level 3) → all lengths=3, got {mode._lengths}"
    print("  C button → all steps length 3 ✓")


def test_page_navigation():
    print("\n=== Page Navigation ===")
    grid = MockGrid()
    ctrl = MockController()
    mode = ArpEditMode(grid, ctrl)
    mode.set_state(
        intervals=[0, 2, 4, 5, 7, 4, 2, 0],
        lengths=[5] * STEP_COUNT,
        pattern_name="normal",
        current_slot=1,
        scale_intervals=[0, 2, 4, 5, 7, 9, 11],
        root_note=62,
        bpm=120,
        diatonic=True,
    )
    mode.enter()
    mode._render()

    assert mode._arp_page == 0
    print(f"  Page {mode._arp_page + 1} ✓")

    from src.ui.modes.arp_edit import RIGHT_H, RIGHT_G

    mode.handle_control_event(type('E', (), {
        'control_id': 100 + RIGHT_H,
        'event_type': type('T', (), {'name': 'RIGHT_COLUMN_PRESS'})(),
        'pressed': True,
    })())
    mode._render()
    assert mode._arp_page == 1
    print(f"  H press → page {mode._arp_page + 1} ✓")

    mode.handle_control_event(type('E', (), {
        'control_id': 100 + RIGHT_G,
        'event_type': type('T', (), {'name': 'RIGHT_COLUMN_PRESS'})(),
        'pressed': True,
    })())
    mode._render()
    assert mode._arp_page == 0, f"G press → page {mode._arp_page + 1}"
    print(f"  G press → page {mode._arp_page + 1} ✓")

    mode.handle_control_event(type('E', (), {
        'control_id': 100 + RIGHT_G,
        'event_type': type('T', (), {'name': 'RIGHT_COLUMN_PRESS'})(),
        'pressed': True,
    })())
    mode._render()
    assert mode._arp_page == 2, f"Wrap: G at page 1 → page {mode._arp_page + 1}"
    print(f"  G wrap → page {mode._arp_page + 1} ✓")


def test_pattern_persistence():
    print("\n=== Pattern Save/Load ===")
    test_slot = 20
    saved_intervals = [0, 3, 5, 0, 3, 5, 0, 3]
    saved_lengths = [5, 3, 5, 3, 5, 3, 5, 3]

    assert test_slot not in FACTORY_SLOTS

    _save_pattern_to_slot(test_slot, saved_intervals, saved_lengths, "test_pattern")
    assert _slot_has_pattern(test_slot), "Slot should exist after save"
    print(f"  Saved to slot {test_slot} ✓")

    loaded = _load_pattern_from_slot(test_slot)
    assert loaded == saved_intervals, f"Loaded intervals: {loaded}"
    print(f"  Loaded intervals match ✓")

    import json
    data = json.loads(_slot_file_name(test_slot).read_text())
    loaded_lengths = data.get("lengths", [])
    assert loaded_lengths == saved_lengths, f"Loaded lengths: {loaded_lengths}"
    print(f"  Loaded lengths match ✓")

    _slot_file_name(test_slot).unlink(missing_ok=True)
    assert not _slot_has_pattern(test_slot), "Cleanup: file deleted"
    print(f"  Cleaned up ✓")


def test_factory_slot_protection():
    print("\n=== Factory Slot Protection ===")
    original = _load_pattern_from_slot(1)

    _save_pattern_to_slot(1, [0, 0, 0, 0, 0, 0, 0, 0], [1] * STEP_COUNT)
    after = _load_pattern_from_slot(1)
    assert after == original, "Factory slot 1 should be protected (no overwrite)"
    print("  Factory slot 1: save blocked ✓")


if __name__ == "__main__":
    test_pattern_editing()
    test_beat_chase()
    test_slot_navigation()
    test_note_length_mode()
    test_global_note_length_set()
    test_page_navigation()
    test_pattern_persistence()
    test_factory_slot_protection()
    print("\n✅ ALL ARP EDIT MODE TESTS PASSED")
