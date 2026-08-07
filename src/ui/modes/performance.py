"""
Performance Mode — dual-channel FX controller (GTR + VOX).

Grid split vertically: GTR (cols 0-3), VOX (cols 4-7).
Volume columns (0,4): dual-level press, 16-31 range spanning 8 pads + mute.
FX blocks (1-3, 5-7): 4 FX per channel, 3-pad preset blocks, 6 presets via bank toggle.
"""
import math
import time
import logging

from src.controllers.base import GridEvent, ControlEvent, LogicalColor
from src.ui.mode import Mode

logger = logging.getLogger(__name__)


GTR_FX_NAMES = ["Delay", "Harmony", "Amp&Drv", "Tremolo"]
VOX_FX_NAMES = ["Delay", "Harmony", "Drv&Flt", "Misc SFX"]

CHANNELS: dict[str, dict] = {
    "GTR": {"vol_col": 0, "fx_start": 1, "fx_end": 3, "track": 2, "fx_names": GTR_FX_NAMES},
    "VOX": {"vol_col": 4, "fx_start": 5, "fx_end": 7, "track": 1, "fx_names": VOX_FX_NAMES},
}

FX_COUNT = 4
ROWS_PER_FX = 2
NUM_PADS = 8
MAX_VOL = 32
MIN_VOL = 16

TUNER_SPEED_PER_CENT = 0.18
MAX_TUNER_SPEED = 7.0
BAND_MIN_X = 0.6
BAND_MAX_X = 6.4
BAND_WIDTH = 1.5
LOCK_CENT = 3.0
NEAR_CENT = 20.0


class PerformanceMode(Mode):
    def __init__(self, grid, controller, config: dict | None = None, osc_bridge=None):
        super().__init__("performance", grid, controller)
        self.osc_bridge = osc_bridge

        self._volumes: dict[str, int] = {"GTR": 24, "VOX": 24}
        self._vol_sub: dict[str, bool] = {"GTR": False, "VOX": False}
        self._muted_ch: dict[str, bool] = {"GTR": False, "VOX": False}

        self._fx_presets: dict[str, list[int]] = {
            "GTR": [1, 1, 1, 1],
            "VOX": [1, 1, 1, 1],
        }
        self._fx_bank: dict[str, list[bool]] = {
            "GTR": [False, False, False, False],
            "VOX": [False, False, False, False],
        }
        self._fx_enabled: dict[str, list[bool]] = {
            "GTR": [False, False, False, False],
            "VOX": [False, False, False, False],
        }

        self._tuner_active: bool = False
        self._active_channel: str = "GTR"
        self._tuner_phase: float = 0.0
        self._tuner_state: str = "off"
        self._tuner_state_start: float = 0.0
        self._tuner_exit_start: float = 0.0
        self._tuner_letters = ["T", "N", "R"]
        self._tuner_cents: float = 0.0
        self._tuner_channel: str = "GTR"
        self._tuner_band_x: float = 3.5
        self._tuner_band_dir: float = 1.0
        self._tuner_band_speed: float = 0.0
        self._hints_enabled: bool = True
        self._hint_color: LogicalColor = LogicalColor.AMBER_HIGH
        self._hint_text: str = ""
        self._hint_expiry: float = 0.0
        self._bpm: float = 120.0

    def set_bpm(self, bpm: float):
        self._bpm = bpm

    def set_hints_config(self, enabled: bool, color: str = ""):
        self._hints_enabled = enabled
        if color:
            try:
                self._hint_color = LogicalColor[color]
            except KeyError:
                self._hint_color = LogicalColor.AMBER_HIGH

    def _show_hint(self, text: str, color: LogicalColor | None = None, duration: float = 0.3):
        if not self._hints_enabled:
            return
        self._hint_text = text
        self._hint_color = color if color is not None else self._hint_color
        self._hint_expiry = time.monotonic() + duration

    def enter(self):
        self._render()

    def exit(self):
        self.clear()
        self.commit()

    def _channel_at(self, x: int) -> str | None:
        if 0 <= x <= 3:
            return "GTR"
        if 4 <= x <= 7:
            return "VOX"
        return None

    def _is_volume_col(self, x: int) -> bool:
        return x == 0 or x == 4

    def _fx_row_for(self, fx_idx: int, sub_row: int) -> int:
        return (FX_COUNT - 1 - fx_idx) * ROWS_PER_FX + sub_row

    def _fx_preset_row(self, fx_idx: int) -> int:
        return self._fx_row_for(fx_idx, 1)

    def _fx_disable_row(self, fx_idx: int) -> int:
        return self._fx_row_for(fx_idx, 0)

    def _pad_to_volume(self, pad_y: int, sub: bool) -> int:
        if pad_y == 0 and sub:
            return 0
        return 18 + 2 * pad_y - (1 if sub else 0)

    def _volume_to_pad(self, vol: int) -> tuple[int, bool]:
        if vol == 0:
            return (0, True)
        if vol < 18:
            return (0, False)
        if vol > 32:
            return (7, False)
        offset = 32 - vol
        pad_y = 7 - (offset // 2)
        sub = (offset % 2) == 1
        return (max(0, min(7, pad_y)), sub)

    def handle_grid_event(self, event: GridEvent):
        if not event.pressed:
            return

        if self._tuner_active:
            self._tuner_active = False
            self._tuner_state = "exit"
            self._tuner_exit_start = time.monotonic()
            return

        x, y = event.x, event.y
        ch = self._channel_at(x)
        if ch is None:
            return

        if self._is_volume_col(x):
            self._handle_volume_press(ch, y)
        elif CHANNELS[ch]["fx_start"] <= x <= CHANNELS[ch]["fx_end"]:
            self._handle_fx_press(ch, x, y)

    def set_active_channel(self, ch: str):
        if ch in CHANNELS:
            self._active_channel = ch

    def handle_control_event(self, event: ControlEvent):
        is_press = "PRESS" in event.event_type.name
        if not is_press:
            return

        if event.control_id == 106:
            self._active_channel = "VOX" if self._active_channel == "GTR" else "GTR"
            if self._tuner_state == "active":
                self._tuner_channel = self._active_channel
                self._tuner_cents = 0.0
                self._tuner_band_speed = 0.0
                self._tuner_band_x = 3.5
                self.mark_dirty()
        elif event.control_id == 107:
            if self._tuner_state in ("intro", "active"):
                self.stop_tuner()
            else:
                self.start_tuner(self._active_channel)

    def _handle_volume_press(self, ch: str, y: int):
        vol = self._volumes[ch]
        sub = self._vol_sub[ch]
        cur_pad, cur_sub = self._volume_to_pad(vol)

        if self._muted_ch[ch]:
            self._muted_ch[ch] = False
            self._volumes[ch] = self._pad_to_volume(y, False)
            self._vol_sub[ch] = False
            self._send_vol_osc(ch)
            self._render()
            return

        if y == cur_pad and not self._muted_ch[ch]:
            if not cur_sub:
                new_sub = True
                new_vol = self._pad_to_volume(y, True)
                if new_vol == 0:
                    self._muted_ch[ch] = True
                    self._volumes[ch] = 0
                    self._vol_sub[ch] = False
                else:
                    self._volumes[ch] = new_vol
                    self._vol_sub[ch] = True
            else:
                self._volumes[ch] = self._pad_to_volume(y, False)
                self._vol_sub[ch] = False
        else:
            self._volumes[ch] = self._pad_to_volume(y, False)
            self._vol_sub[ch] = False

        self._send_vol_osc(ch)
        self._render()

    def _handle_fx_press(self, ch: str, x: int, y: int):
        for fx_idx in range(FX_COUNT):
            if y in (self._fx_preset_row(fx_idx), self._fx_disable_row(fx_idx)):
                break
        else:
            return

        if y == self._fx_disable_row(fx_idx):
            self._fx_enabled[ch][fx_idx] = not self._fx_enabled[ch][fx_idx]
            self._send_fx_bypass(ch, fx_idx)
            self._show_fx_hint(ch, fx_idx)
            self._render()
            return

        pad_idx = x - CHANNELS[ch]["fx_start"]
        if pad_idx < 0 or pad_idx > 2:
            return

        was_disabled = not self._fx_enabled[ch][fx_idx]
        if was_disabled:
            self._fx_enabled[ch][fx_idx] = True

        current_preset = self._fx_presets[ch][fx_idx]
        current_bank = self._fx_bank[ch][fx_idx]

        preset_bank1 = pad_idx + 1
        preset_bank2 = pad_idx + 4

        is_current_pad = (
            (not current_bank and current_preset == preset_bank1)
            or (current_bank and current_preset == preset_bank2)
        )

        if was_disabled:
            new_bank = False
            new_preset = preset_bank1
        elif is_current_pad:
            new_bank = not current_bank
            new_preset = preset_bank2 if new_bank else preset_bank1
        else:
            new_bank = False
            new_preset = preset_bank1

        self._fx_presets[ch][fx_idx] = new_preset
        self._fx_bank[ch][fx_idx] = new_bank

        if was_disabled:
            self._send_fx_bypass(ch, fx_idx)
        self._send_fx_preset(ch, fx_idx)
        self._show_fx_hint(ch, fx_idx)
        self._render()

    def _show_fx_hint(self, ch: str, fx_idx: int):
        name = CHANNELS[ch]["fx_names"][fx_idx]
        letter = name[0].upper()
        self._show_hint(letter)

    def _send_vol_osc(self, ch: str):
        if not self.osc_bridge:
            return
        track = CHANNELS[ch]["track"]
        vol = self._volumes[ch]
        normalized = max(0.0, min(1.0, (vol - MIN_VOL) / (MAX_VOL - MIN_VOL + 1)))
        self.osc_bridge.send(f"/track/{track}/volume", normalized)

    def _send_fx_preset(self, ch: str, fx_idx: int):
        if not self.osc_bridge:
            return
        track = CHANNELS[ch]["track"]
        preset = self._fx_presets[ch][fx_idx]
        self.osc_bridge.send(f"/track/{track}/fx/{fx_idx + 1}/preset", preset)

    def _send_fx_bypass(self, ch: str, fx_idx: int):
        if not self.osc_bridge:
            return
        track = CHANNELS[ch]["track"]
        enabled = self._fx_enabled[ch][fx_idx]
        self.osc_bridge.send(f"/track/{track}/fx/{fx_idx + 1}/bypass", 0 if enabled else 1)

    def tick(self, delta_ms: float):
        dirty = False
        if self._tuner_active:
            self._tuner_phase = (self._tuner_phase + delta_ms * 0.01) % (math.pi * 2)
            self._advance_tuner_band(delta_ms)
            dirty = True
        if dirty:
            self.mark_dirty()

    def _advance_tuner_band(self, delta_ms: float):
        dt = delta_ms / 1000.0
        cents = abs(self._tuner_cents)
        target_speed = min(MAX_TUNER_SPEED, cents * TUNER_SPEED_PER_CENT)
        self._tuner_band_speed += (target_speed - self._tuner_band_speed) * min(1.0, dt * 4.0)
        self._tuner_band_x += self._tuner_band_dir * self._tuner_band_speed * dt
        if self._tuner_band_x < BAND_MIN_X:
            self._tuner_band_x = BAND_MIN_X
            self._tuner_band_dir = 1.0
        elif self._tuner_band_x > BAND_MAX_X:
            self._tuner_band_x = BAND_MAX_X
            self._tuner_band_dir = -1.0

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

        self._render_volume_bar("GTR")
        self._render_volume_bar("VOX")
        self._render_fx_blocks("GTR")
        self._render_fx_blocks("VOX")
        if self._hint_text and time.monotonic() < self._hint_expiry:
            self._render_fx_hint(self._hint_text, self._hint_color)
        self.commit()

    def _render_volume_bar(self, ch: str):
        vol = self._volumes[ch]
        muted = self._muted_ch[ch]
        vol_col = CHANNELS[ch]["vol_col"]

        if muted:
            for y in range(NUM_PADS):
                self.grid.set_cell(vol_col, y, LogicalColor.RED_HIGH)
            return

        cur_pad, cur_sub = self._volume_to_pad(vol)

        for y in range(NUM_PADS):
            if y > cur_pad:
                self.grid.set_cell(vol_col, y, LogicalColor.RED_HIGH)
            elif y == cur_pad:
                color = LogicalColor.AMBER_HIGH if cur_sub else LogicalColor.GREEN_HIGH
                self.grid.set_cell(vol_col, y, color)

    def _render_fx_blocks(self, ch: str):
        fx_start = CHANNELS[ch]["fx_start"]
        fx_end = CHANNELS[ch]["fx_end"]

        for fx_idx in range(FX_COUNT):
            pr = self._fx_preset_row(fx_idx)
            dr = self._fx_disable_row(fx_idx)

            enabled = self._fx_enabled[ch][fx_idx]
            current_preset = self._fx_presets[ch][fx_idx]
            current_bank = self._fx_bank[ch][fx_idx]

            for pad_idx in range(3):
                x = fx_start + pad_idx
                if not current_bank:
                    preset_in_pad = pad_idx + 1
                else:
                    preset_in_pad = pad_idx + 4

                if not enabled:
                    color = LogicalColor.OFF
                elif current_preset == preset_in_pad:
                    color = LogicalColor.RED_HIGH if current_bank else LogicalColor.AMBER_HIGH
                else:
                    color = LogicalColor.GREEN_HIGH

                self.grid.set_cell(x, pr, color)

            for pad_idx in range(3):
                x = fx_start + pad_idx
                color = LogicalColor.RED_MED if not enabled else LogicalColor.RED_HIGH
                self.grid.set_cell(x, dr, color)

    def _render_fx_hint(self, text: str, color: LogicalColor):
        from src.ui.modes.message import FONT_5X5
        glyph = FONT_5X5.get(text, FONT_5X5.get("?", ["00000"] * 5))
        for row in range(5):
            for col in range(5):
                if glyph[row][col] == "1":
                    x = col + 1
                    y = 6 - row
                    if 0 <= x < 8 and 0 <= y < 8:
                        self.grid.set_cell(x, y, color)

    def _render_tuner(self):
        cents = abs(self._tuner_cents)
        locked = (cents < LOCK_CENT) and (self._tuner_band_speed < 0.4)
        band_color = LogicalColor.GREEN_HIGH if locked else (
            LogicalColor.AMBER_HIGH if cents < NEAR_CENT else LogicalColor.RED_HIGH
        )

        lo = int(math.floor(self._tuner_band_x - BAND_WIDTH * 0.5))
        hi = int(math.ceil(self._tuner_band_x + BAND_WIDTH * 0.5))

        bg_lit = LogicalColor.GREEN_LOW

        for y in range(8):
            for x in range(8):
                if lo <= x <= hi:
                    self.grid.set_cell(x, y, band_color)
                else:
                    phase_offset = (x - 3.5) * 0.3
                    brightness = math.sin(self._tuner_phase + phase_offset)
                    if brightness > 0.7:
                        self.grid.set_cell(x, y, bg_lit)
                    elif brightness > 0.3:
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

    def update_tuner(self, cents: float, channel: str = "GTR"):
        self._tuner_cents = cents
        self._tuner_channel = channel
        if self._tuner_active:
            self.mark_dirty()

    def start_tuner(self, channel: str = "GTR"):
        if self._tuner_state in ("intro", "active", "exit"):
            return
        self._tuner_channel = channel
        self._tuner_cents = 0.0
        self._tuner_state = "intro"
        self._tuner_state_start = time.monotonic()
        self.mark_dirty()

    def stop_tuner(self):
        if self._tuner_active:
            self._tuner_active = False
            self._tuner_state = "exit"
            self._tuner_exit_start = time.monotonic()
            self.mark_dirty()
