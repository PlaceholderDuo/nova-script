import time
from typing import Optional

from src.controllers.base import GridEvent, ControlEvent, LogicalColor
from src.ui.mode import Mode


class SequencerMode(Mode):
    def __init__(self, grid, controller, midi_manager=None):
        super().__init__("sequencer", grid, controller)
        self.midi_manager = midi_manager
        self._steps_per_row = 8
        self._visible_steps = 8
        self._scroll_offset = 0
        self._num_rows = 7
        self._steps: list[list[bool]] = []
        self._current_step = 0
        self._playing = False
        self._resolution = 16  # steps per beat
        self._midi_channel = 0
        self._note_base = 36  # C1
        self._last_tick = time.monotonic()
        self._bpm = 120.0
        self._tick_interval = 60.0 / self._bpm / (self._resolution / 4)
        self._page = 0
        self._pages = 1

        self._init_steps()

    def _init_steps(self):
        total_steps = 32
        self._steps = [[False] * total_steps for _ in range(self._num_rows)]
        self._pages = (total_steps - 1) // self._visible_steps + 1

    def enter(self):
        self._playing = True
        self._last_tick = time.monotonic()
        self._render()

    def exit(self):
        self._playing = False
        self._current_step = 0
        self.clear()
        self.commit()

    def handle_grid_event(self, event: GridEvent):
        if not event.pressed:
            return

        if event.y >= self._num_rows:
            return

        step_idx = event.x + self._page * self._visible_steps
        if step_idx < len(self._steps[event.y]):
            self._steps[event.y][step_idx] = not self._steps[event.y][step_idx]
            self._render()

    def handle_control_event(self, event: ControlEvent):
        if not event.event_type.name.endswith("_PRESS"):
            return

        if event.control_id >= 200:
            top_idx = event.control_id - 200
            if top_idx == 0:
                self._playing = not self._playing
                if self._playing:
                    self._last_tick = time.monotonic()
            elif top_idx == 1:
                self._page = 0
                self._current_step = 0
            elif top_idx == 6:
                self._page = max(0, self._page - 1)
            elif top_idx == 7:
                self._page = min(self._pages - 1, self._page + 1)
            self._render()

        elif event.control_id >= 100:
            col_idx = event.control_id - 100
            if col_idx == 0:
                self._resolution = max(4, self._resolution // 2)
                self._update_tick_interval()
            elif col_idx == 1:
                self._resolution = min(32, self._resolution * 2)
                self._update_tick_interval()

    def _update_tick_interval(self):
        self._tick_interval = 60.0 / self._bpm / (self._resolution / 4)

    def tick(self, delta_ms: float):
        if not self._playing:
            return

        now = time.monotonic()
        if now - self._last_tick >= self._tick_interval:
            self._last_tick = now

            self._current_step = (self._current_step + 1) % len(self._steps[0])

            page = self._current_step // self._visible_steps
            if page != self._page:
                self._page = page

            self._send_step_notes(self._current_step)
            self._render()

    def _send_step_notes(self, step: int):
        if self.midi_manager is None:
            return

        for row in range(self._num_rows):
            if self._steps[row][step]:
                note = self._note_base + (self._num_rows - 1 - row)
                self.midi_manager.send_message(
                    self.controller.device_name,
                    [0x90 + self._midi_channel, note, 100],
                )

    def _render(self):
        self.clear()

        for row in range(self._num_rows):
            for col in range(self._visible_steps):
                step_idx = col + self._page * self._visible_steps
                if step_idx >= len(self._steps[row]):
                    break

                color = LogicalColor.OFF
                if step_idx == self._current_step and self._playing:
                    color = LogicalColor.GREEN_LOW
                elif self._steps[row][step_idx]:
                    if row < 2:
                        color = LogicalColor.RED_HIGH
                    elif row < 4:
                        color = LogicalColor.AMBER_HIGH
                    else:
                        color = LogicalColor.GREEN_HIGH
                elif step_idx % 4 == 0:
                    color = LogicalColor.RED_LOW

                self.grid.set_cell(col, row, color)

        if self._playing:
            play_color = LogicalColor.GREEN_HIGH
            transport_row = self._num_rows
        else:
            play_color = LogicalColor.RED_HIGH

        for x in range(self._visible_steps):
            self.grid.set_cell(x, self._num_rows, play_color if x < 2 else (
                LogicalColor.AMBER_LOW if x == 6 else (
                    LogicalColor.AMBER_LOW if x == 7 else LogicalColor.OFF
                )
            ))

        self.commit()
