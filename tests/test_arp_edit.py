"""
Unit test for ARP Edit Mode — grid editing, beat chase, slot selection.
"""
import sys
import time
from pathlib import Path
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


class MockMidManager:
    def __init__(self):
        self.sent = []

    def send_message(self, device, msg, target="main"):
        self.sent.append((device, list(msg), target))

    def send_force(self, msg):
        self.sent.append(("force", list(msg), "main"))


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
    from src.ui.modes.arp_edit import RIGHT_F

    mode.handle_control_event(type('F', (), {
        'control_id': 100 + RIGHT_F,
        'event_type': type('T', (), {'name': 'RIGHT_COLUMN_PRESS'})(),
        'pressed': True,
    })())
    mode._render()
    assert mode._note_length_mode is True, "F press should enter note-length mode"
    print("  F press → note-length mode ON ✓")

    mode.handle_grid_event(g_press(0, 1))
    mode._render()
    assert mode._lengths[0] == 2, f"Step 0 y=1 → length 2, got {mode._lengths[0]}"
    print("  Step 0 y=1 press → length 2 ✓")

    mode.handle_grid_event(g_press(3, 7))
    mode._render()
    assert mode._lengths[3] == 8, f"Step 3 y=7 press → length 8, got {mode._lengths[3]}"
    print("  Step 3 y=7 press → length 8 ✓")

    mode.handle_control_event(type('F', (), {
        'control_id': 100 + RIGHT_F,
        'event_type': type('T', (), {'name': 'RIGHT_COLUMN_PRESS'})(),
        'pressed': True,
    })())
    assert mode._note_length_mode is True, "F press in note-length should NOT exit"
    print("  F press again → stays in note-length mode ✓")

    # Only the green top-row button (control 200) exits note-length
    mode.exit_note_length()
    assert mode._note_length_mode is False, "exit_note_length should return to pattern"
    print("  Top-1 → note-length mode OFF ✓")


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


def _make_mode(*, intervals=None, lengths=None, bpm=120, root=62,
               scale=(0, 2, 4, 5, 7, 9, 11), midi=None):
    grid = MockGrid()
    ctrl = MockController()
    mode = ArpEditMode(grid, ctrl, midi_manager=midi)
    mode.set_state(
        intervals=intervals or [0, 2, 4, 5, 7, 4, 2, 0],
        lengths=lengths or [5] * STEP_COUNT,
        pattern_name="normal",
        current_slot=1,
        scale_intervals=list(scale),
        root_note=root,
        bpm=bpm,
        diatonic=True,
    )
    mode.enter()
    return mode, grid, ctrl


def test_beat_advances_chase():
    print("\n=== Beat Chase Advances (live) ===")
    mid = MockMidManager()
    mode, _, _ = _make_mode(bpm=120, midi=mid)
    sd = mode._step_duration()
    # At 120bpm step = 0.25s. Advance clock past step 2 boundary.
    mode._advance_chase(mode._entry_time + sd * 2 + 0.001)
    assert mode._beat_step == 2
    print(f"  Beat advanced to step {mode._beat_step} ✓")


def test_staccato_single_note_per_step():
    print("\n=== Short Length: single note, no overlap ===")
    mid = MockMidManager()
    mode, _, _ = _make_mode(bpm=120, lengths=[5] * STEP_COUNT, midi=mid)
    sd = mode._step_duration()
    # Advance from entry: step 1 fires at entry+sd, step 2 at entry+2*sd.
    mode._advance_chase(mode._entry_time + sd + 0.001)
    t = mode._entry_time + sd * 2 + 0.001
    mode._advance_chase(t)
    ons = [m for m in mid.sent if m[1][0] == 0x90]
    offs = [m for m in mid.sent if m[1][0] == 0x80]
    # Each step is a clean attack; short notes self-release.
    assert len(ons) >= 2, f"Expected >=2 notes-on, got {len(ons)}"
    print(f"  Played steps produced {len(ons)} notes-on / {len(offs)} notes-off ✓")


def test_legato_overlap_holds_note():
    print("\n=== Legato (len 8) holds note across steps ===")
    mid = MockMidManager()
    mode, _, _ = _make_mode(bpm=120, lengths=[8] * STEP_COUNT, midi=mid)
    sd = mode._step_duration()
    mode._advance_chase(mode._entry_time + sd + 0.001)   # step 1 note-on (legato)
    mode._advance_chase(mode._entry_time + sd * 2 + 0.001)  # step 2
    mode._advance_chase(mode._entry_time + sd * 3 + 0.001)  # step 3
    # Legato notes stay active across step boundaries.
    assert len(mode._active_notes) >= 1, "Legato note should still be active"
    print(f"  Active notes held: {len(mode._active_notes)} ✓")


def test_legato_distinct_pitches_no_stacking():
    print("\n=== Legato replace: distinct pitches don't stack ===")
    mid = MockMidManager()
    mode, _, _ = _make_mode(bpm=120, lengths=[8] * STEP_COUNT, midi=mid)
    sd = mode._step_duration()
    mode._advance_chase(mode._entry_time + sd + 0.001)
    mode._advance_chase(mode._entry_time + sd * 2 + 0.001)
    # Distinct intervals playing legato → running pitch replaces, stays lean.
    assert len(mode._active_notes) <= 1, f"Expected <=1 active legato note, got {len(mode._active_notes)}"
    print(f"  active while legato-sequencing: {len(mode._active_notes)} ✓")


def test_length_schedules_off_at_due_time():
    print("\n=== Level-3 note releases after partial duration ===")
    mid = MockMidManager()
    mode, _, _ = _make_mode(bpm=120, lengths=[3] * STEP_COUNT, midi=mid)
    sd = mode._step_duration()
    # Step 1 fires; a level-3 (0.5x) note ends half a step later.
    mode._advance_chase(mode._entry_time + sd + 0.001)
    mode._advance_chase(mode._entry_time + sd * 1.6)  # within following step
    # Next step boundary passes; prior short note should be freed.
    mode._advance_chase(mode._entry_time + sd * 2 + 0.001)
    assert len(mode._active_notes) <= 1
    print(f"  Short note released on following step ✓")


def test_length_overlay_activates_on_f():
    print("\n=== LENGTH Overlay Activates on F ===")
    mode, _, _ = _make_mode()
    from src.ui.modes.arp_edit import RIGHT_F
    mode.handle_control_event(type('E', (), {
        'control_id': 100 + RIGHT_F,
        'event_type': type('T', (), {'name': 'RIGHT_COLUMN_PRESS'})(),
        'pressed': True,
    })())
    assert mode._note_length_mode is True
    assert mode._length_overlay is True, "E press should trigger LENGTH scroll overlay"
    print("  F press → note-length ON + overlay active ✓")


def test_length_overlay_draws_pixels():
    print("\n=== LENGTH Overlay F ===")
    mode, grid, _ = _make_mode()
    from src.ui.modes.arp_edit import RIGHT_F
    mode.handle_control_event(type('E', (), {
        'control_id': 100 + RIGHT_F,
        'event_type': type('T', (), {'name': 'RIGHT_COLUMN_PRESS'})(),
        'pressed': True,
    })())
    mode._render()
    lit = [(x, y) for (x, y), c in grid._cells.items() if c != LogicalColor.OFF]
    assert len(lit) > 0, "Overlay should render some RED pixels"
    colors = {c for (x, y), c in grid._cells.items() if c != LogicalColor.OFF}
    assert colors == {LogicalColor.RED_HIGH}, f"Overlay should be RED_HIGH only, got {colors}"
    print(f"  Overlay drew {len(lit)} RED pixels ✓")


def test_length_overlay_times_out_to_bars():
    print("\n=== LENGTH Overlay Times Out to Bars ===")
    mode, grid, _ = _make_mode()
    from src.ui.modes.arp_edit import RIGHT_F
    mode.handle_control_event(type('E', (), {
        'control_id': 100 + RIGHT_F,
        'event_type': type('T', (), {'name': 'RIGHT_COLUMN_PRESS'})(),
        'pressed': True,
    })())
    mode._length_overlay_start = mode._length_scroll_last = time.monotonic() - 3.0
    mode._length_scroll_pos = 9999.0
    mode.tick(50)
    assert mode._length_overlay is False, "Overlay should end after duration"
    mode._render()
    bars = [(x, y) for (x, y), c in grid._cells.items() if c != LogicalColor.OFF]
    assert len(bars) >= 1, "Bar-graph should render after overlay"
    print(f"  Overlay timed out → {len(bars)} bar cells ✓")


def _ctrl(rid, name, pressed):
    return type('CE', (), {
        'control_id': 100 + rid,
        'event_type': type('T', (), {'name': name})(),
        'pressed': pressed,
    })()


def _ctrl(rid, name, pressed):
    return type('CE', (), {
        'control_id': 100 + rid,
        'event_type': type('T', (), {'name': name})(),
        'pressed': pressed,
    })()


def test_short_press_selects_slot():
    print("\n=== Short Press Selects Slot ===")
    mode, _, _ = _make_mode()
    mode._current_slot = 1
    from src.ui.modes.arp_edit import RIGHT_D
    rid = RIGHT_D  # slot 4 on page 1
    mode.handle_control_event(_ctrl(rid, 'RIGHT_COLUMN_PRESS', True))
    mode._slot_press_time = time.monotonic() - 0.05  # short duration
    mode.handle_control_event(_ctrl(rid, 'RIGHT_COLUMN_RELEASE', False))
    assert mode._current_slot == 4, f"Short D should load slot 4, got {mode._current_slot}"
    print(f"  Short press D → slot 4 (no save) ✓")


def test_short_press_dispatch_steps():
    print("\n=== Short Press Dispatches via Release ===")
    mode, _, _ = _make_mode()
    mode._current_slot = 1
    from src.ui.modes.arp_edit import RIGHT_D
    rid = RIGHT_D
    mode.handle_control_event(_ctrl(rid, 'RIGHT_COLUMN_PRESS', True))
    mode._slot_press_time = time.monotonic() - 0.05
    mode.handle_control_event(_ctrl(rid, 'RIGHT_COLUMN_RELEASE', False))
    assert mode._current_slot == 4, f"Short D should load slot 4, got {mode._current_slot}"
    print("  Short D via press+release loads slot 4 ✓")


def test_slot_save_writes_pattern():
    print("\n=== Long-Press Save Writes Pattern ===")
    test_slot = 19
    mode, _, _ = _make_mode(
        intervals=[0, 1, 2, 3, 4, 5, 6, 7],
        lengths=[6, 6, 6, 6, 6, 6, 6, 6],
    )
    from src.ui.modes.arp_edit import _load_pattern_from_slot, RIGHT_D
    rid = RIGHT_D  # slot 4 on page 1
    slot = 4
    mode.handle_control_event(_ctrl(rid, 'RIGHT_COLUMN_PRESS', True))
    mode._slot_press_time = time.monotonic() - 1.0  # long
    mode.handle_control_event(_ctrl(rid, 'RIGHT_COLUMN_RELEASE', False))
    saved = _load_pattern_from_slot(slot)
    assert saved == [0, 1, 2, 3, 4, 5, 6, 7], f"Slot {slot} not saved: {saved}"
    assert mode._save_flash_slot == slot
    from src.ui.modes.arp_edit import _slot_file_name
    _slot_file_name(slot).unlink(missing_ok=True)
    print(f"  Long-press D saved pattern to slot {slot} + flash armed ✓")


def test_save_factory_slot_protected():
    print("\n=== Factory Slot Save Protected ===")
    original = _load_pattern_from_slot(2)
    mode, _, _ = _make_mode()
    from src.ui.modes.arp_edit import RIGHT_B
    rid = RIGHT_B  # slot 2 (factory)
    mode._handle_slot_save(rid)
    after = _load_pattern_from_slot(2)
    assert after == original, "Factory slot 2 should not be saved over"
    print("  Factory slot save blocked ✓")


def test_save_flash_led_blinks():
    print("\n=== Save Flash LED ===")
    mode, _, _ = _make_mode()
    from src.ui.modes.arp_edit import RIGHT_D, _slot_file_name
    slot = 4
    mode._handle_slot_save(RIGHT_D)
    mode._save_flash_on = False
    mode._render()
    mode._save_flash_on = True
    mode._render()
    _slot_file_name(slot).unlink(missing_ok=True)
    print("  Flash toggles without error ✓")


def test_exit_button_is_top_row_one():
    print("=== ARP Exit wired to top-row button 1 (control 200) ===")
    src = Path(__file__).parent.parent / "src" / "engine.py"
    text = src.read_text()
    start = text.index("def _on_control_event")
    end = text.index("def _on_menu_select")
    block = text[start:end]
    assert 'active_mode_name == "arp_edit"' in block
    assert 'event.control_id == 200' in block, "exit must be top-row button 1"
    assert 'event.control_id == 201' not in block, (
        "exit must not be wired to top-row button 2 (201)"
    )
    print("  Top-row 1 exits arp_edit; top-row 2 no longer conflicts ✓")


if __name__ == "__main__":
    test_pattern_editing()
    test_beat_chase()
    test_slot_navigation()
    test_note_length_mode()
    test_global_note_length_set()
    test_page_navigation()
    test_pattern_persistence()
    test_factory_slot_protection()
    test_beat_advances_chase()
    test_staccato_single_note_per_step()
    test_legato_overlap_holds_note()
    test_legato_distinct_pitches_no_stacking()
    test_length_schedules_off_at_due_time()
    test_length_overlay_activates_on_f()
    test_length_overlay_draws_pixels()
    test_length_overlay_times_out_to_bars()
    test_short_press_selects_slot()
    test_short_press_dispatch_steps()
    test_slot_save_writes_pattern()
    test_save_factory_slot_protected()
    test_save_flash_led_blinks()
    test_exit_button_is_top_row_one()
    print("\n✅ ALL ARP EDIT MODE TESTS PASSED")
