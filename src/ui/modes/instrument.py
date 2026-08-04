"""
Instrument Mode — 8x8 grid-based instrument like Ableton Push / Akai Force.

Grid: scale-mapped pads with configurable row offset.
Right column: mode controls (Notes/Chords, Scale, Hold, ARP, ARP Pattern).
"""
import json
import logging
import time
from pathlib import Path

from src.controllers.base import GridEvent, ControlEvent, LogicalColor
from src.ui.mode import Mode

logger = logging.getLogger(__name__)

SCALES: dict[str, list[int]] = {
    "major":      [0, 2, 4, 5, 7, 9, 11],
    "blues":      [0, 3, 5, 6, 7, 10],
    "chromatic":  list(range(12)),
}

CHORD_PATTERNS: dict[str, list[int]] = {
    "major":      [0, 4, 7],
    "blues":      [0, 3, 7, 10],
    "chromatic":  [0, 4, 7],
}

SCALE_NAMES = ["major", "blues", "chromatic"]
SCALE_COLORS: dict[str, LogicalColor] = {
    "major": LogicalColor.GREEN_HIGH,
    "blues": LogicalColor.AMBER_HIGH,
    "chromatic": LogicalColor.RED_HIGH,
}

ARP_PATTERNS = ["normal", "chordal", "octaves"]
ARP_PATTERN_COLORS: dict[int, LogicalColor] = {
    0: LogicalColor.GREEN_HIGH,
    1: LogicalColor.AMBER_HIGH,
    2: LogicalColor.RED_HIGH,
}

OFFSET_OPTIONS = [12, 2, 3, 4, 5]
OFFSET_LABELS = ["Oct", "2", "3", "4", "5"]


def _load_arp_pattern(name: str) -> list[int]:
    path = Path(__file__).parent.parent.parent / "config" / "arp_patterns" / f"{name}.json"
    try:
        with open(path) as f:
            data = json.load(f)
            return data["intervals"]
    except Exception:
        default_intervals = {
            "normal": [0, 1, 2, 3, 4, 5, 6, 7],
            "chordal": [0, 6, 2, 4, 0, 6, 2, 4],
            "octaves": [0, 7, 14, 7, 0, 7, 14, 7],
        }
        return default_intervals.get(name, [0, 1, 2, 3, 4, 5, 6, 7])


class InstrumentMode(Mode):
    CTRL_NOTES = 0
    CTRL_SCALE = 1
    CTRL_HOLD = 2
    CTRL_ARP = 3
    CTRL_ARP_PAT = 4

    ARP_OFF = "off"
    ARP_UP = "up"
    ARP_DOWN = "down"

    def __init__(self, grid, controller, config: dict | None = None, midi_manager=None):
        super().__init__("instrument", grid, controller)
        self.midi_manager = midi_manager
        self._num_pages = 0

        self._input_mode: str = "notes"
        self._scale_name: str = "major"
        self._root_note: int = 48
        self._note_offset: int = 12
        self._hold: bool = False
        self._arp_mode: str = self.ARP_OFF
        self._arp_pattern_idx: int = 0
        self._arp_pattern_name: str = "normal"
        self._arp_step: int = 0
        self._arp_timer: float = 0.0
        self._arp_interval: float = 0.125
        self._active_notes: dict[int, float] = {}
        self._pressed_pads: set[tuple[int, int]] = set()
        self._last_arp_progress: float = 0.0

        self._a_held: bool = False
        self._editing_offset: bool = False
        self._a_flash_timer: float = 0.0
        self._a_flash_state: bool = False

        self._bpm: float = 120.0

    def set_bpm(self, bpm: float):
        self._bpm = bpm
        if self._arp_mode != self.ARP_OFF:
            self._arp_interval = 60.0 / bpm / 4.0

    @property
    def _scale(self) -> list[int]:
        return SCALES[self._scale_name]

    @property
    def _chord(self) -> list[int]:
        return CHORD_PATTERNS[self._scale_name]

    def _get_note(self, x: int, y: int) -> int | None:
        s = self._scale
        slen = len(s)
        scale_idx = x % slen
        octave_shift = (x // slen) * 12
        row_offset = y * self._note_offset
        return self._root_note + s[scale_idx] + octave_shift + row_offset

    def _is_root(self, x: int, y: int) -> bool:
        note = self._get_note(x, y)
        if note is None:
            return False
        return note % 12 == self._root_note % 12

    def enter(self):
        self._render()
        self._render_controls()

    def exit(self):
        self.clear()
        self.clear_pages()
        self.commit()
        self._release_all_notes()

    def handle_grid_event(self, event: GridEvent):
        if self._editing_offset:
            if event.pressed:
                self._select_offset(event.x)
            return

        if event.pressed:
            self._pressed_pads.add((event.x, event.y))
            self._on_pad_press(event.x, event.y)
        else:
            self._pressed_pads.discard((event.x, event.y))
            if not self._hold:
                self._on_pad_release(event.x, event.y)

        self._render()

    def handle_control_event(self, event: ControlEvent):
        is_press = "PRESS" in event.event_type.name
        if not is_press:
            cid = event.control_id
            if cid == 100 + self.CTRL_NOTES:
                self._a_held = False
                self._editing_offset = False
                self._render()
                self._render_controls()
            return

        cid = event.control_id

        if 100 <= cid < 108:
            idx = cid - 100
            if idx == self.CTRL_NOTES:
                self._a_press()
            elif idx == self.CTRL_SCALE:
                self._cycle_scale()
            elif idx == self.CTRL_HOLD:
                self._toggle_hold()
            elif idx == self.CTRL_ARP:
                self._cycle_arp()
            elif idx == self.CTRL_ARP_PAT:
                self._cycle_arp_pattern()

    def tick(self, delta_ms: float):
        now = time.monotonic()

        a_flash_changed = False
        if self._a_held:
            elapsed = now - self._a_flash_timer
            if (elapsed % 0.3) < 0.15:
                if not self._a_flash_state:
                    self._a_flash_state = True
                    a_flash_changed = True
            else:
                if self._a_flash_state:
                    self._a_flash_state = False
                    a_flash_changed = True

        arp_advanced = False
        if self._arp_mode != self.ARP_OFF and self._active_notes:
            self._last_arp_progress += delta_ms / 1000.0
            if self._last_arp_progress >= self._arp_interval:
                self._last_arp_progress -= self._arp_interval
                self._advance_arp()
                arp_advanced = True

        if a_flash_changed:
            self._render_controls()
        if arp_advanced:
            self._render()

    def _a_press(self):
        if self._editing_offset:
            self._editing_offset = False
            self._render()
            self._render_controls()
            return

        self._a_held = True
        self._a_flash_timer = time.monotonic()
        self._a_flash_state = True

        if not self._editing_offset:
            self._show_offset_overlay()

    def _show_offset_overlay(self):
        self._editing_offset = True
        self._render()

    def _select_offset(self, x: int):
        if 0 <= x < len(OFFSET_OPTIONS):
            self._note_offset = OFFSET_OPTIONS[x]
        self._editing_offset = False
        self._a_held = False
        self._render()
        self._render_controls()

    def _cycle_scale(self):
        names = SCALE_NAMES
        current = names.index(self._scale_name)
        self._scale_name = names[(current + 1) % len(names)]
        self._release_all_notes()
        self._render()
        self._render_controls()

    def _toggle_hold(self):
        self._hold = not self._hold
        if not self._hold:
            self._release_all_notes()
        self._render()
        self._render_controls()

    def _cycle_arp(self):
        modes = [self.ARP_OFF, self.ARP_UP, self.ARP_DOWN]
        current = modes.index(self._arp_mode)
        self._arp_mode = modes[(current + 1) % len(modes)]
        if self._arp_mode == self.ARP_OFF:
            self._release_all_notes()
        else:
            self._arp_interval = 60.0 / self._bpm / 4.0
            self._arp_step = 0
            self._last_arp_progress = 0.0
        self._render()
        self._render_controls()

    def _cycle_arp_pattern(self):
        self._arp_pattern_idx = (self._arp_pattern_idx + 1) % len(ARP_PATTERNS)
        self._arp_pattern_name = ARP_PATTERNS[self._arp_pattern_idx]
        self._arp_step = 0
        self._last_arp_progress = 0.0
        self._render()
        self._render_controls()

    def _on_pad_press(self, x: int, y: int):
        note = self._get_note(x, y)
        if note is None:
            return

        if self._input_mode == "chords":
            for interval in self._chord:
                chord_note = note + interval
                self._send_note_on(chord_note)
        else:
            self._send_note_on(note)

        if self._hold:
            if self._active_notes:
                self._release_all_notes()
                if self._input_mode == "chords":
                    for interval in self._chord:
                        self._send_note_on(note + interval)
                else:
                    self._send_note_on(note)

        if self._arp_mode != self.ARP_OFF:
            self._arp_step = 0
            self._last_arp_progress = 0.0

    def _on_pad_release(self, x: int, y: int):
        pass

    def _send_note_on(self, note: int):
        self._active_notes[note] = time.monotonic()
        if self.midi_manager:
            try:
                self.midi_manager.send_message("Launchpad Mini",
                    [0x90, note, 100], target="force")
            except Exception:
                pass
        logger.debug(f"Note ON: {note}")

    def _send_note_off(self, note: int):
        self._active_notes.pop(note, None)
        if self.midi_manager:
            try:
                self.midi_manager.send_message("Launchpad Mini",
                    [0x80, note, 0], target="force")
            except Exception:
                pass
        logger.debug(f"Note OFF: {note}")

    def _release_all_notes(self):
        notes = list(self._active_notes.keys())
        for note in notes:
            self._send_note_off(note)

    def _advance_arp(self):
        if not self._active_notes:
            return

        pattern = _load_arp_pattern(self._arp_pattern_name)
        sorted_notes = sorted(self._active_notes.keys())

        if self._arp_mode == self.ARP_DOWN:
            sorted_notes.reverse()

        for note in list(self._active_notes.keys()):
            self._send_note_off(note)

        if sorted_notes:
            interval_idx = self._arp_step % len(pattern)
            base_idx = interval_idx % len(sorted_notes)
            note = sorted_notes[base_idx] + pattern[interval_idx]
            self._send_note_on(note)

        self._arp_step += 1

    def _render(self):
        self.clear()

        for y in range(8):
            for x in range(8):
                note = self._get_note(x, y)
                if note is None:
                    continue

                is_root = self._is_root(x, y)
                was_pressed = (x, y) in self._pressed_pads
                is_octave = False

                if was_pressed and not is_root:
                    pressed_note = self._get_note(x, y)
                    for px, py in self._pressed_pads:
                        pn = self._get_note(px, py)
                        if pn and abs(pn - (pressed_note or 0)) % 12 == 0 and abs(pn - (pressed_note or 0)) >= 12:
                            is_octave = True
                            break

                color = LogicalColor.AMBER_LOW

                if was_pressed:
                    color = LogicalColor.GREEN_HIGH
                elif is_root:
                    color = LogicalColor.RED_HIGH
                elif is_octave:
                    color = LogicalColor.GREEN_MED

                self.grid.set_cell(x, y, color)

        self._render_offset_overlay()
        self.commit()

    def _render_offset_overlay(self):
        if not self._editing_offset:
            return
        sel_idx = OFFSET_OPTIONS.index(self._note_offset) if self._note_offset in OFFSET_OPTIONS else 0
        for i, (_offset, label) in enumerate(zip(OFFSET_OPTIONS, OFFSET_LABELS)):
            x = i
            y = 7
            color = LogicalColor.GREEN_HIGH if i == sel_idx else LogicalColor.AMBER_HIGH
            self.grid.set_cell(x, y, color)

    def _render_controls(self):
        if self._editing_offset or self._a_held:
            offset_idx = OFFSET_OPTIONS.index(self._note_offset) if self._note_offset in OFFSET_OPTIONS else 0
            for i in range(min(len(OFFSET_OPTIONS) + 1, 8)):
                ctrl_idx = i
                if i < len(OFFSET_OPTIONS):
                    color = LogicalColor.GREEN_HIGH if i == offset_idx else LogicalColor.AMBER_HIGH
                else:
                    color = LogicalColor.OFF
                self.controller.send_right_column_led(ctrl_idx, color)
            return

        a_color = LogicalColor.GREEN_HIGH if self._input_mode == "notes" else LogicalColor.AMBER_HIGH
        self.controller.send_right_column_led(self.CTRL_NOTES, a_color)

        b_color = SCALE_COLORS[self._scale_name]
        self.controller.send_right_column_led(self.CTRL_SCALE, b_color)

        c_color = LogicalColor.GREEN_HIGH if self._hold else LogicalColor.RED_HIGH
        self.controller.send_right_column_led(self.CTRL_HOLD, c_color)

        if self._arp_mode == self.ARP_OFF:
            d_color = LogicalColor.RED_HIGH
        elif self._arp_mode == self.ARP_UP:
            d_color = LogicalColor.GREEN_HIGH
        else:
            d_color = LogicalColor.AMBER_HIGH
        self.controller.send_right_column_led(self.CTRL_ARP, d_color)

        e_color = ARP_PATTERN_COLORS.get(self._arp_pattern_idx, LogicalColor.OFF)
        self.controller.send_right_column_led(self.CTRL_ARP_PAT, e_color)

        for i in range(8):
            if i > self.CTRL_ARP_PAT:
                self.controller.send_right_column_led(i, LogicalColor.OFF)
