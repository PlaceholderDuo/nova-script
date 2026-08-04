import time
from typing import Optional

from src.controllers.base import GridEvent, ControlEvent, LogicalColor
from src.ui.mode import Mode


FONT_5X5 = {
    "A": ["01110", "10001", "11111", "10001", "10001"],
    "B": ["11110", "10001", "11110", "10001", "11110"],
    "C": ["01110", "10001", "10000", "10001", "01110"],
    "D": ["11100", "10010", "10001", "10010", "11100"],
    "E": ["11111", "10000", "11110", "10000", "11111"],
    "F": ["11111", "10000", "11110", "10000", "10000"],
    "G": ["01110", "10000", "10111", "10001", "01110"],
    "H": ["10001", "10001", "11111", "10001", "10001"],
    "I": ["01110", "00100", "00100", "00100", "01110"],
    "J": ["00111", "00010", "00010", "10010", "01100"],
    "K": ["10001", "10010", "11100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001"],
    "O": ["01110", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "11110", "10000", "10000"],
    "Q": ["01110", "10001", "10101", "10011", "01111"],
    "R": ["11110", "10001", "11110", "10010", "10001"],
    "S": ["01111", "10000", "01110", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "11111"],
    "V": ["10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10101", "11011", "10001"],
    "X": ["10001", "01010", "00100", "01010", "10001"],
    "Y": ["10001", "01010", "00100", "00100", "00100"],
    "Z": ["11111", "00010", "00100", "01000", "11111"],
    "0": ["01110", "10011", "10101", "11001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "11111"],
    "2": ["01110", "00001", "00110", "01000", "11111"],
    "3": ["01110", "00001", "00110", "00001", "01110"],
    "4": ["00010", "00110", "01010", "11111", "00010"],
    "5": ["11111", "10000", "11110", "00001", "11110"],
    "6": ["01110", "10000", "11110", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "00100"],
    "8": ["01110", "10001", "01110", "10001", "01110"],
    "9": ["01110", "10001", "01111", "00001", "01110"],
    " ": ["00000", "00000", "00000", "00000", "00000"],
    ".": ["00000", "00000", "00000", "00100", "00000"],
    ",": ["00000", "00000", "00000", "00100", "01000"],
    "!": ["00100", "00100", "00100", "00000", "00100"],
    "?": ["01110", "00001", "00110", "00000", "00100"],
    "-": ["00000", "00000", "11111", "00000", "00000"],
    "+": ["00000", "00100", "01110", "00100", "00000"],
    "/": ["00001", "00010", "00100", "01000", "10000"],
    ":": ["00000", "00100", "00000", "00100", "00000"],
    "'": ["00100", "00100", "00000", "00000", "00000"],
    "#": ["01010", "11111", "01010", "11111", "01010"],
}


class MessageMode(Mode):
    def __init__(self, grid, controller):
        super().__init__("message", grid, controller)
        self._message_queue: list[str] = []
        self._current_text: str = ""
        self._scroll_pos: int = 0
        self._char_width: int = 5
        self._char_height: int = 5
        self._scroll_speed_ms: float = 150.0
        self._last_scroll: float = 0.0
        self._previous_mode: str = ""

    def set_previous_mode(self, mode_name: str):
        self._previous_mode = mode_name

    def enqueue_message(self, text: str):
        text = text.upper().strip()
        self._message_queue.append(text)
        if not self._current_text:
            self._next_message()

    def _next_message(self):
        if self._message_queue:
            self._current_text = self._message_queue.pop(0) + "   "
            self._scroll_pos = 0
        else:
            self._current_text = ""

    def enter(self):
        self._scroll_pos = 0
        self._last_scroll = time.monotonic()
        self._render()

    def exit(self):
        self.clear()
        self.commit()

    def handle_grid_event(self, event: GridEvent):
        if event.pressed:
            self._message_queue.clear()
            self._current_text = ""

    def handle_control_event(self, event: ControlEvent):
        if event.event_type.name.endswith("_PRESS"):
            self._message_queue.clear()
            self._current_text = ""

    def tick(self, delta_ms: float):
        if not self._current_text:
            return

        now = time.monotonic()
        if (now - self._last_scroll) * 1000 >= self._scroll_speed_ms:
            self._last_scroll = now
            self._scroll_pos += 1

            max_scroll = len(self._current_text) * self._char_width + 8
            if self._scroll_pos >= max_scroll:
                if self._message_queue:
                    self._next_message()
                else:
                    self._current_text = ""

            self._render()

    def _render(self):
        self.clear()

        if not self._current_text:
            return

        for char_idx, char in enumerate(self._current_text):
            glyph = FONT_5X5.get(char, FONT_5X5.get("?"))

            char_x_offset = char_idx * (self._char_width + 1) - self._scroll_pos

            for row in range(self._char_height):
                for col in range(self._char_width):
                    if glyph[row][col] == "1":
                        x = char_x_offset + col
                        y = 7 - row

                        if 0 <= x < 8 and 0 <= y < 8:
                            current = self.grid.get_cell(x, y)
                            if current == LogicalColor.OFF:
                                self.grid.set_cell(x, y, LogicalColor.AMBER_HIGH)

        self.commit()
