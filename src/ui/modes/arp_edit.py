"""
ARP Edit Mode — on-Launchpad pattern editor for ARP sequences.

Enter via long-press E from Instrument Mode. The 8×8 grid becomes:
- Row 0: Beat chase indicator
- Rows 1-7: Scale degree rows (root at row 1, 7th at row 7)
- Right column A-H: Pattern slots (short=select, long=save), E=note-length, G/H=page nav
- Top-1: Exit back to Instrument Mode

Note-length sub-mode (toggle via E): bar-graph showing per-step lengths 1-8.
"""
import json
import math
import time
import logging
from pathlib import Path
from typing import Optional

from src.controllers.base import GridEvent, ControlEvent, LogicalColor
from src.ui.mode import Mode

logger = logging.getLogger(__name__)

PAGE_SIZE = 8
TOTAL_PAGES = 3
TOTAL_SLOTS = PAGE_SIZE * TOTAL_PAGES
STEP_COUNT = 8
SCALE_ROWS = 7
NUM_PADS = 8
DEFAULT_LENGTH = 5

LENGTH_MULTIPLIERS = {
    1: 0.25,   # 1/32 note (ultra-staccato)
    2: 0.33,   # 1/16 triplet
    3: 0.50,   # 1/16 note (standard short)
    4: 0.67,   # 1/8 triplet
    5: 1.00,   # 1/8 note (full step, default)
    6: 1.50,   # dotted 1/8 (overlaps next step)
    7: 2.00,   # 1/4 note (spans 2 steps)
    8: 99.0,   # legato (essentially infinite — released on next note or exit)
}

SLOTS_PER_PAGE = {
    0: list(range(1, 9)),   # Page 1: slots 1-8
    1: list(range(9, 17)),  # Page 2: slots 9-16
    2: list(range(17, 25)), # Page 3: slots 17-24
}

FACTORY_SLOTS = frozenset({1, 2, 3})

FACTORY_NAMES = {
    1: "normal",
    2: "chordal",
    3: "octaves",
}

PATTERNS_DIR = Path(__file__).parent.parent.parent.parent / "config" / "arp_patterns"

RIGHT_A = 0
RIGHT_B = 1
RIGHT_C = 2
RIGHT_D = 3
RIGHT_E = 4
RIGHT_F = 5
RIGHT_G = 6
RIGHT_H = 7


def _slot_file_name(slot: int) -> Path:
    if slot in FACTORY_NAMES:
        return PATTERNS_DIR / f"{FACTORY_NAMES[slot]}.json"
    return PATTERNS_DIR / f"user_{slot:02d}.json"


def _load_pattern_from_slot(slot: int) -> list[int]:
    path = _slot_file_name(slot)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return data.get("intervals", [])
    except Exception:
        logger.warning(f"Failed to load pattern slot {slot}")
        return []


def _save_pattern_to_slot(slot: int, intervals: list[int], lengths: list[int], name: str = ""):
    if slot in FACTORY_SLOTS:
        return
    path = _slot_file_name(slot)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "name": name or f"pattern_{slot:02d}",
        "intervals": intervals,
        "lengths": lengths,
    }, indent=2))


def _slot_has_pattern(slot: int) -> bool:
    return _slot_file_name(slot).exists()


class ArpEditMode(Mode):
    def __init__(self, grid, controller, midi_manager=None):
        super().__init__("arp_edit", grid, controller)
        self.midi_manager = midi_manager
        self._num_pages = 1

        self._intervals: list[int] = [0, 2, 4, 5, 7, 4, 2, 0]
        self._lengths: list[int] = [DEFAULT_LENGTH] * STEP_COUNT
        self._pattern_name: str = "normal"
        self._current_slot: int = 1

        self._scale_intervals: list[int] = [0, 2, 4, 5, 7, 9, 11]
        self._root_note: int = 62
        self._bpm: float = 120.0
        self._diatonic: bool = True

        self._arp_page: int = 0
        self._note_length_mode: bool = False

        # "LENGTH" entry scroll overlay
        self._length_overlay: bool = False
        self._length_overlay_start: float = 0.0
        self._length_scroll_pos: float = 0.0
        self._length_scroll_last: float = 0.0
        self._length_overlay_ms: int = 1000
        self._length_px_per_ms: float = 1.0 / 150.0

        # slot long-press save
        self._slot_press_rid: int | None = None
        self._slot_press_time: float = 0.0
        self._save_flash_slot: int | None = None
        self._save_flash_start: float = 0.0
        self._save_flash_ms: int = 1000
        self._save_flash_on: bool = False

        self._entry_time: float = time.monotonic()
        self._beat_step: int = 0

        self._active_notes: set[int] = set()
        self._sound: dict[int, float | None] = {}

    def _step_duration(self) -> float:
        """Seconds per step. Chase uses 1/2 beat (1/8 note) per step at 4/4."""
        return 60.0 / max(1.0, self._bpm) / 2.0

    def reserves_h_button(self) -> bool:
        return True

    def is_playing(self) -> bool:
        return True

    def set_state(self, *, intervals: list[int], lengths: list[int],
                  pattern_name: str, current_slot: int,
                  scale_intervals: list[int], root_note: int,
                  bpm: float, diatonic: bool):
        self._intervals = list(intervals) if intervals else [0, 2, 4, 5, 7, 4, 2, 0]
        self._lengths = list(lengths) if lengths else [DEFAULT_LENGTH] * STEP_COUNT
        self._pattern_name = pattern_name
        self._current_slot = current_slot
        self._scale_intervals = list(scale_intervals)
        self._root_note = root_note
        self._bpm = bpm
        self._diatonic = diatonic

        self._arp_page = (self._current_slot - 1) // PAGE_SIZE

    def get_state(self) -> dict:
        return {
            "intervals": list(self._intervals),
            "lengths": list(self._lengths),
            "pattern_name": self._pattern_name,
            "current_slot": self._current_slot,
        }

    def enter(self):
        self._entry_time = time.monotonic()
        self._beat_step = 0
        self._note_length_mode = False
        self._release_all_notes()
        self._render()

    def exit(self):
        self._release_all_notes()
        self.clear()
        self.clear_pages()
        self.commit()

    def tick(self, delta_ms: float):
        now = time.monotonic()

        if self._save_flash_slot is not None:
            if (now - self._save_flash_start) * 1000 >= self._save_flash_ms:
                self._save_flash_slot = None
            else:
                new_state = ((now * 2) % 1.0) < 0.5  # ~250ms blink toggle
                if new_state != self._save_flash_on:
                    self._save_flash_on = new_state
                    self._render()
            if self._save_flash_slot is None:
                self._render()

        if self._length_overlay:
            self._advance_length_overlay(now)
            self._render()
            return

        self._advance_chase(time.monotonic())

        if self._needs_render:
            self._needs_render = False
            self._render()

    def _show_length_overlay(self):
        self._length_overlay = True
        self._length_overlay_start = time.monotonic()
        self._length_scroll_pos = 0.0
        self._length_scroll_last = time.monotonic()
        self._render()

    def _advance_length_overlay(self, now: float):
        dt = (now - self._length_scroll_last) * 1000
        self._length_scroll_last = now
        self._length_scroll_pos += dt * self._length_px_per_ms

        if (now - self._length_overlay_start) * 1000 >= self._length_overlay_ms:
            self._length_overlay = False

    def _advance_chase(self, now: float):
        sd = self._step_duration()
        if sd <= 0:
            return
        step = int((now - self._entry_time) / sd) % STEP_COUNT
        if step != self._beat_step:
            self._beat_step = step
            self._play_step(step, now)
            self._needs_render = True

    def _play_step(self, step: int, now: float):
        self._fire_due_offs(now)
        interval = self._intervals[step] if step < len(self._intervals) else -1
        if interval < 0 or interval >= len(self._scale_intervals):
            return
        pitch = self._root_note + self._scale_intervals[interval]
        length = self._lengths[step] if step < len(self._lengths) else DEFAULT_LENGTH
        mult = LENGTH_MULTIPLIERS.get(length, 1.0)
        sd = self._step_duration()

        if length >= 8:
            off_time = None  # legato: hold until replaced or exit
        else:
            off_time = now + mult * sd

        for held in list(self._sound):
            if self._sound[held] is None and held != pitch:
                self._send_note_off(held)

        if pitch in self._sound:
            existing = self._sound[pitch]
            if existing is None:
                return
            if off_time is None or off_time > existing:
                self._sound[pitch] = off_time
            return

        if self.midi_manager:
            try:
                self.midi_manager.send_force([0x90, pitch, 100])
            except Exception:
                pass
        self._active_notes.add(pitch)
        self._sound[pitch] = off_time

    def _fire_due_offs(self, now: float):
        for pitch in list(self._sound):
            off = self._sound[pitch]
            if off is not None and now >= off:
                self._send_note_off(pitch)

    def handle_grid_event(self, event: GridEvent):
        if not event.pressed:
            return

        x, y = event.x, event.y

        if self._note_length_mode:
            self._handle_note_length_grid(x, y)
            return

        if x >= STEP_COUNT:
            return

        if y == 0:
            return

        scale_row = y - 1
        current = self._intervals[x] if x < len(self._intervals) else 0

        if scale_row == current and current >= 0:
            self._intervals[x] = -1
        else:
            self._intervals[x] = scale_row

        self._preview_step(x)
        self._render()

    def handle_control_event(self, event: ControlEvent):
        rid = event.control_id - 100
        if rid < 0 or rid > 7:
            return

        is_press = "PRESS" in event.event_type.name
        is_release = "RELEASE" in event.event_type.name

        # During note-length mode, A-H set global length on press — no long-press.
        if self._note_length_mode:
            if is_press:
                if rid == RIGHT_E:
                    self._note_length_mode = False
                    self._length_overlay = False
                    self._render()
                elif rid <= RIGHT_H:
                    self._lengths = [rid - RIGHT_A + 1] * STEP_COUNT
                    self._render()
            return

        if is_press:
            if rid == RIGHT_E:
                self._note_length_mode = True
                self._show_length_overlay()
                return
            if rid == RIGHT_G:
                self._arp_page = (self._arp_page - 1) % TOTAL_PAGES
                self._render()
                return
            if rid == RIGHT_H:
                self._arp_page = (self._arp_page + 1) % TOTAL_PAGES
                self._render()
                return

            # Track slot buttons for long-press save.
            if rid <= RIGHT_H and rid not in (RIGHT_E, RIGHT_G, RIGHT_H):
                self._slot_press_rid = rid
                self._slot_press_time = time.monotonic()
            return

        if is_release:
            if self._slot_press_rid is not None:
                rid_pressed = self._slot_press_rid
                self._slot_press_rid = None
                if rid_pressed == rid:
                    elapsed = (time.monotonic() - self._slot_press_time) * 1000
                    if elapsed >= self._long_press_ms:
                        self._handle_slot_save(rid)
                        return
                    self._handle_slot_select_by_rid(rid)
                    return
            self._render()

    def _handle_slot_select_by_rid(self, rid: int):
        slots = SLOTS_PER_PAGE[self._arp_page]
        slot = slots[rid]
        if self._handle_slot_select(slot):
            self._render()

    def _handle_slot_save(self, rid: int):
        slot = SLOTS_PER_PAGE[self._arp_page][rid]
        if slot in FACTORY_SLOTS:
            return
        _save_pattern_to_slot(slot, self._intervals, self._lengths, self._pattern_name)
        self._save_flash_slot = slot
        self._save_flash_start = time.monotonic()
        self._save_flash_on = True
        self._render()

    def _handle_slot_select(self, slot: int) -> bool:
        if slot == self._current_slot:
            return False

        intervals = _load_pattern_from_slot(slot)
        if not intervals:
            intervals = [0, 2, 4, 5, 7, 4, 2, 0]

        path = _slot_file_name(slot)
        lengths = [DEFAULT_LENGTH] * STEP_COUNT
        if path.exists():
            try:
                data = json.loads(path.read_text())
                file_lengths = data.get("lengths", [])
                if len(file_lengths) == STEP_COUNT:
                    lengths = list(file_lengths)
            except Exception:
                pass

        self._intervals = list(intervals[:STEP_COUNT])
        self._lengths = list(lengths[:STEP_COUNT])
        self._current_slot = slot
        self._pattern_name = FACTORY_NAMES.get(slot, f"pattern_{slot:02d}")
        self._release_all_notes()
        return True

    def _handle_note_length_grid(self, x: int, y: int):
        if x >= STEP_COUNT:
            return
        length = min(8, max(1, y + 1))
        self._lengths[x] = length
        self._render()

    def _send_note_on(self, note: int):
        if self.midi_manager:
            try:
                self.midi_manager.send_force([0x90, note, 100])
            except Exception:
                pass
        self._active_notes.add(note)

    def _send_note_off(self, note: int):
        self._active_notes.discard(note)
        self._sound.pop(note, None)
        if self.midi_manager:
            try:
                self.midi_manager.send_force([0x80, note, 0])
            except Exception:
                pass

    def _release_all_notes(self):
        for note in list(self._active_notes):
            self._send_note_off(note)

    def _preview_step(self, step: int):
        """Audition a single step when tapping the grid. Uses the step's own length."""
        self._fire_due_offs(time.monotonic())
        interval = self._intervals[step % len(self._intervals)]
        if interval < 0 or interval >= len(self._scale_intervals):
            return
        semitone = self._scale_intervals[interval]
        note = self._root_note + semitone
        length = self._lengths[step % len(self._lengths)] if self._lengths else DEFAULT_LENGTH
        mult = LENGTH_MULTIPLIERS.get(length, 1.0)
        sd = self._step_duration()

        if length >= 8:
            off_time = None
        else:
            off_time = time.monotonic() + mult * sd

        if note in self._sound and self._sound[note] is not None:
            return
        self._send_note_on(note)
        self._sound[note] = off_time

    def _render(self):
        self.clear()

        if self._length_overlay:
            self._render_length_scroll()
        elif self._note_length_mode:
            self._render_note_length()
        else:
            self._render_pattern_editor()

        self._render_right_column()
        self.commit()

        lp = self.controller
        lp.send_top_row_led(0, LogicalColor.GREEN_HIGH)
        for i in range(1, 8):
            lp.send_top_row_led(i, LogicalColor.OFF)

        if self._note_length_mode:
            lp.send_right_column_led(RIGHT_E, LogicalColor.RED_HIGH)
        else:
            lp.send_right_column_led(RIGHT_E, LogicalColor.RED_HIGH)

    def _render_length_scroll(self):
        from src.ui.modes.message import FONT_5X5
        text = "LENGTH"
        char_w = 6
        total_width = len(text) * char_w + 8
        pos = int(self._length_scroll_pos)

        if pos >= total_width:
            self._length_overlay = False
            self._note_length_mode = True
            return

        for col in range(8):
            strip_pos = pos + col
            char_idx = strip_pos // char_w
            if char_idx < 0 or char_idx >= len(text):
                continue
            pixel_in_char = strip_pos % char_w
            if pixel_in_char >= 5:
                continue
            ch = text[char_idx]
            glyph = FONT_5X5.get(ch)
            if glyph is None:
                continue
            for row in range(5):
                if glyph[row][pixel_in_char] == "1":
                    gy = 6 - row
                    if 0 <= gy < 8:
                        self.grid.set_cell(col, gy, LogicalColor.RED_HIGH)

    def _render_pattern_editor(self):
        for step in range(STEP_COUNT):
            if step == self._beat_step:
                self.grid.set_cell(step, 0, LogicalColor.AMBER_HIGH)
            else:
                self.grid.set_cell(step, 0, LogicalColor.AMBER_LOW)

        for row in range(SCALE_ROWS):
            for step in range(STEP_COUNT):
                interval = self._intervals[step] if step < len(self._intervals) else -1
                display_row = min(interval, SCALE_ROWS - 1) if interval >= 0 else -1
                if display_row == row:
                    self.grid.set_cell(step, row + 1, LogicalColor.AMBER_HIGH)
                else:
                    self.grid.set_cell(step, row + 1, LogicalColor.OFF)

    def _render_note_length(self):
        for step in range(STEP_COUNT):
            length = self._lengths[step]
            for y in range(NUM_PADS):
                if y < length:
                    self.grid.set_cell(step, y, LogicalColor.RED_HIGH)
                else:
                    self.grid.set_cell(step, y, LogicalColor.OFF)

    def _render_right_column(self):
        if self._note_length_mode:
            for i in range(NUM_PADS):
                self.controller.send_right_column_led(i, LogicalColor.RED_HIGH)
            return

        slots = SLOTS_PER_PAGE[self._arp_page]
        for i in range(NUM_PADS):
            if i == RIGHT_E:
                self.controller.send_right_column_led(i, LogicalColor.RED_HIGH)
                continue
            if i == RIGHT_G:
                color = LogicalColor.AMBER_LOW if self._arp_page == 0 else LogicalColor.GREEN_HIGH
                self.controller.send_right_column_led(i, color)
                continue
            if i == RIGHT_H:
                color = LogicalColor.AMBER_LOW if self._arp_page == TOTAL_PAGES - 1 else LogicalColor.GREEN_HIGH
                self.controller.send_right_column_led(i, color)
                continue

            slot = slots[i] if i < len(slots) else 1

            if slot == self._save_flash_slot and self._save_flash_on:
                self.controller.send_right_column_led(i, LogicalColor.GREEN_HIGH)
                continue

            is_selected = (slot == self._current_slot)
            is_factory = (slot in FACTORY_SLOTS)
            has_pattern = _slot_has_pattern(slot)

            if is_selected:
                color = LogicalColor.RED_HIGH if is_factory else LogicalColor.AMBER_HIGH
            elif is_factory or has_pattern:
                color = LogicalColor.RED_LOW if is_factory else LogicalColor.AMBER_LOW
            else:
                color = LogicalColor.OFF

            self.controller.send_right_column_led(i, color)
