"""
Performance Mode — track mute + FX control + tuner.

Top row (1-8): track mute toggles
Right column (1-5): FX toggles (Rev, Dly, Chor, Hrm Up, Hrm Dn)
Grid: visual state feedback + strobe tuner on GTR hold
"""
import math
import time
import logging
from enum import Enum

from src.controllers.base import GridEvent, ControlEvent, LogicalColor
from src.ui.mode import Mode

logger = logging.getLogger(__name__)


class FXType(Enum):
    TOGGLE = "toggle"
    TIME_BASED = "time_based"


DEFAULT_TRACKS = [
    {"index": 0, "alias": "Vox", "osc_mute": "/track/1/mute", "fx": [
        {"name": "Rev", "osc": "/track/1/fx/1/bypass", "type": "toggle"},
        {"name": "Dly", "osc": "/track/1/fx/2/bypass", "type": "time_based"},
        {"name": "Chor", "osc": "/track/1/fx/3/bypass", "type": "time_based"},
        {"name": "Hrm↑", "osc": "/track/1/fx/4/bypass", "type": "toggle"},
        {"name": "Hrm↓", "osc": "/track/1/fx/5/bypass", "type": "toggle"},
    ]},
    {"index": 1, "alias": "GTR", "osc_mute": "/track/2/mute", "fx": [
        {"name": "Rev", "osc": "/track/2/fx/1/bypass", "type": "toggle"},
        {"name": "Dly", "osc": "/track/2/fx/2/bypass", "type": "time_based"},
        {"name": "Chor", "osc": "/track/2/fx/3/bypass", "type": "time_based"},
        {"name": "Hrm↑", "osc": "/track/2/fx/4/bypass", "type": "toggle"},
        {"name": "Hrm↓", "osc": "/track/2/fx/5/bypass", "type": "toggle"},
    ]},
    {"index": 2, "alias": "Bass", "osc_mute": "/track/3/mute", "fx": [
        {"name": "Rev", "osc": "/track/3/fx/1/bypass", "type": "toggle"},
        {"name": "Dly", "osc": "/track/3/fx/2/bypass", "type": "time_based"},
        {"name": "Chor", "osc": "/track/3/fx/3/bypass", "type": "time_based"},
        {"name": "Hrm↑", "osc": "/track/3/fx/4/bypass", "type": "toggle"},
        {"name": "Hrm↓", "osc": "/track/3/fx/5/bypass", "type": "toggle"},
    ]},
]

for i in range(3, 8):
    DEFAULT_TRACKS.append({
        "index": i, "alias": f"Track{i+1}", "osc_mute": f"/track/{i+1}/mute",
        "fx": [{"name": n, "osc": f"/track/{i+1}/fx/{j+1}/bypass", "type": "toggle"}
               for j, n in enumerate(["Rev", "Dly", "Chor", "Hrm↑", "Hrm↓"])]
    })


class PerformanceMode(Mode):
    def __init__(self, grid, controller, config: dict | None = None, osc_bridge=None):
        super().__init__("performance", grid, controller)
        self.osc_bridge = osc_bridge
        self._tracks = config.get("tracks", DEFAULT_TRACKS) if config else DEFAULT_TRACKS
        self._muted: list[bool] = [False] * len(self._tracks)
        self._fx_enabled: list[list[bool]] = [
            [False] * 5 for _ in self._tracks
        ]
        self._active_track: int = 0
        self._tuner_active: bool = False
        self._tuner_track: int = -1
        self._tuner_cents: float = 0.0
        self._tuner_phase: float = 0.0
        self._bpm: float = 120.0
        self._last_beat: float = 0.0
        self._tuner_state: str = "off"
        self._tuner_state_start: float = 0.0
        self._tuner_exit_start: float = 0.0
        self._tuner_letter_idx: int = 0
        self._tuner_letters = ["T", "N", "R"]

    def set_bpm(self, bpm: float):
        self._bpm = bpm

    def enter(self):
        self._active_track = 0
        self._render()

    def exit(self):
        self.clear()
        self.commit()

    def handle_grid_event(self, event: GridEvent):
        if not event.pressed:
            return

        if self._tuner_active:
            self._tuner_active = False
            self._tuner_state = "exit"
            self._tuner_exit_start = time.monotonic()
            return

    def handle_control_event(self, event: ControlEvent):
        is_press = "PRESS" in event.event_type.name
        if not is_press:
            return

        if self._tuner_active:
            self._tuner_active = False
            self._tuner_state = "exit"
            self._tuner_exit_start = time.monotonic()
            return

        if event.control_id >= 200:
            track_idx = event.control_id - 200
            if 0 <= track_idx < len(self._tracks):
                self._toggle_mute(track_idx)
                self._active_track = track_idx
                self._render()

        elif event.control_id >= 100:
            fx_idx = event.control_id - 100
            if 0 <= fx_idx < 5:
                self._toggle_fx(self._active_track, fx_idx)
                self._render()

    def _toggle_mute(self, track_idx: int):
        track = self._tracks[track_idx]
        if track["alias"] == "GTR" and not self._muted[track_idx] and not self._tuner_active:
            self._muted[track_idx] = True
            self._tuner_track = track_idx
            self._tuner_state = "intro"
            self._tuner_state_start = time.monotonic()
            self._tuner_letter_idx = 0
            self._send_osc(track["osc_mute"], 1)
            return

        self._muted[track_idx] = not self._muted[track_idx]
        self._send_osc(track["osc_mute"], 1 if self._muted[track_idx] else 0)

    def _toggle_fx(self, track_idx: int, fx_idx: int):
        if track_idx >= len(self._tracks):
            return
        self._fx_enabled[track_idx][fx_idx] = not self._fx_enabled[track_idx][fx_idx]
        fx = self._tracks[track_idx]["fx"][fx_idx]
        enabled = self._fx_enabled[track_idx][fx_idx]
        self._send_osc(fx["osc"], 0 if enabled else 1)

    def _send_osc(self, addr: str, value: int):
        if self.osc_bridge:
            self.osc_bridge.send(addr, value)

    def tick(self, delta_ms: float):
        if self._tuner_active:
            self._tuner_phase = (self._tuner_phase + delta_ms * 0.01) % (math.pi * 2)
        self._render()

    def _render(self):
        self.clear()

        if self._tuner_state in ("intro", "active"):
            self._render_tuner_state()
            self.commit()
            return

        if self._tuner_state == "exit":
            self._render_tuner_exit()
            self.commit()
            return

        for track_idx, track in enumerate(self._tracks):
            col = track_idx
            if col >= 8:
                break

            mute_color = LogicalColor.RED_HIGH if self._muted[track_idx] else LogicalColor.AMBER_LOW
            if col == self._active_track:
                mute_color = LogicalColor.RED_HIGH if self._muted[track_idx] else LogicalColor.GREEN_LOW

            self.grid.set_cell(col, 7, mute_color)

            for fx_idx in range(min(5, len(track["fx"]))):
                fx = track["fx"][fx_idx]
                enabled = self._fx_enabled[track_idx][fx_idx]
                fx_type = fx.get("type", "toggle")

                if not enabled:
                    color = LogicalColor.RED_HIGH
                elif fx_type == "time_based":
                    beat_phase = (time.monotonic() * self._bpm / 60.0) % 1.0
                    pulse = (math.sin(beat_phase * math.pi * 2) + 1) / 2
                    if pulse > 0.5:
                        color = LogicalColor.GREEN_HIGH
                    else:
                        color = LogicalColor.GREEN_MED
                else:
                    color = LogicalColor.GREEN_HIGH

                display_y = 5 - fx_idx
                if 0 <= display_y < 7:
                    self.grid.set_cell(col, display_y, color)

        self.commit()

    def _render_tuner(self):
        for y in range(8):
            for x in range(8):
                phase_offset = (x - 3.5) * 0.3
                brightness = math.sin(self._tuner_phase + phase_offset)
                if brightness > 0.7:
                    self.grid.set_cell(x, y, LogicalColor.GREEN_HIGH)
                elif brightness > 0.3:
                    self.grid.set_cell(x, y, LogicalColor.GREEN_MED)
                elif brightness > -0.3:
                    self.grid.set_cell(x, y, LogicalColor.AMBER_LOW)

    def _render_tuner_state(self):
        now = time.monotonic()

        if self._tuner_state == "intro":
            elapsed = now - self._tuner_state_start
            letter_duration = 0.3
            transition_duration = 0.3
            total_intro = 3 * letter_duration + transition_duration

            if elapsed < 3 * letter_duration:
                idx = int(elapsed / letter_duration)
                letter = self._tuner_letters[min(idx, 2)]
                self._render_letter(letter, LogicalColor.AMBER_HIGH)
            elif elapsed < total_intro:
                progress = (elapsed - 3 * letter_duration) / transition_duration
                self._render_tuner_transition_in(progress)
            else:
                self._tuner_state = "active"
                self._tuner_active = True
                self._render_tuner()
        else:
            self._render_tuner()

    def _render_tuner_exit(self):
        elapsed = time.monotonic() - self._tuner_exit_start
        duration = 0.3
        if elapsed < duration:
            self._render_tuner_fade(1.0 - elapsed / duration)
        else:
            self._tuner_state = "off"
            self._tuner_active = False
            self._render()

    def _render_letter(self, letter: str, color: LogicalColor):
        from src.ui.modes.message import FONT_5X5
        glyph = FONT_5X5.get(letter, FONT_5X5.get("?", ["00000"] * 5))
        for row in range(5):
            for col in range(5):
                if glyph[row][col] == "1":
                    x = col + 2
                    y = 6 - row
                    if 0 <= x < 8 and 0 <= y < 8:
                        self.grid.set_cell(x, y, color)

    def _render_tuner_transition_in(self, progress: float):
        for y in range(8):
            for x in range(8):
                v = math.sin((x + y) * 0.5 + progress * math.pi * 4)
                if v > 0.3:
                    self.grid.set_cell(x, y, LogicalColor.AMBER_LOW)

    def _render_tuner_fade(self, progress: float):
        for y in range(8):
            for x in range(8):
                v = math.sin((x + y) * 0.5 + progress * math.pi * 8) * progress
                if v > 0.5:
                    self.grid.set_cell(x, y, LogicalColor.GREEN_HIGH)
                elif v > 0.2:
                    self.grid.set_cell(x, y, LogicalColor.AMBER_LOW)

    def update_tuner(self, cents: float):
        self._tuner_cents = cents
