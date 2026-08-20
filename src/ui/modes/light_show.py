"""
Light Show Mode — live cue lighting scenes from the Launchpad.

v2 layout (intuitive — no manual needed):
  * Moods are ROWS (5 rows, one per mood); 8 scenes per mood laid out left→right.
  * Right column A-E is the mood identity light AND a momentary PEAK button:
      hold  → fire that mood's peak (blinder/sparkle), button blinks at BPM;
      release → return to whatever scene was active before the peak.
  * Scene press / peak hold flashes the scene/mood name as scrolling help text
    (5×5 glyphs, RED) drawn in the grid — same style as the guitar screen.

Scene types (grid pads):
  snap   — tap to fade to this scene and hold.
  pulse  — tap to fire a short burst, auto-return after pulse_beats.
"""
import json
import logging
import time

from src.controllers.base import GridEvent, ControlEvent, LogicalColor
from src.ui.mode import Mode
from src.ui.modes.message import FONT_5X5

logger = logging.getLogger(__name__)

# Mood identity colors (MK1-native: amber/red/green × brightness), top→bottom.
MOOD_COLORS = [
    LogicalColor.AMBER_HIGH,   # Standard — bright warm
    LogicalColor.AMBER_LOW,    # Acoustic Candlelight — dim warm
    LogicalColor.GREEN_HIGH,   # EDM — bright cool
    LogicalColor.RED_HIGH,     # High Energy — bright red
    LogicalColor.GREEN_LOW,    # Ballad — dim cool
]

# Mood index → grid row (y). Mood 0 (Standard) at the top (y=7) so the A button
# (top of the right column) lines up with the top mood row. Bottom 3 rows are
# left free for help text / future.
MOOD_ROWS = [7, 6, 5, 4, 3]

SNAP_COLOR = LogicalColor.AMBER_MED
PULSE_COLOR = LogicalColor.RED_MED
ACTIVE_COLOR = LogicalColor.GREEN_HIGH
HINT_COLOR = LogicalColor.RED_HIGH   # help text = RED (matches guitar screen)

ENTRY_ROW_MS = 60        # entry sweep: reveal one mood row every ~60ms
HINT_CHAR_W = 6          # 5px glyph + 1px gap
HINT_LEAD_PX = 8         # blank pixels before the text enters
HINT_TRAIL_PX = 8        # blank pixels after the text exits
HINT_SCROLL_MS = 40      # scroll speed for help text


class LightShowMode(Mode):
    name = "light_show"

    def __init__(self, grid, controller, config: dict | None = None,
                 feed_path: str = "/tmp/lighting_feed"):
        super().__init__("light_show", grid, controller)
        cfg = config or {}
        self.feed_path = cfg.get("feed", feed_path)
        self.moods = cfg.get("moods") or []

        self._current_scene: str | None = None   # active snap scene name
        # peak (right-column hold)
        self._held_mood: int | None = None       # mood index whose peak is held
        self._peak_return_to: str | None = None  # scene to return to after peak
        self._blink_on = False                   # BPM blink phase (held button)
        # pulse (grid scene auto-return)
        self._pending_pulse: dict | None = None
        self._pulse_return_to: str | None = None
        self._pulse_remaining_beats = 0
        # entry animation + help text
        self._entry_row = 0
        self._entry_accum = 0.0
        self._hint_text = ""
        self._hint_scroll = 0.0
        self._hint_max = 0.0
        self._hint_last_tick = 0.0

    # -- engine hooks ------------------------------------------------------ #

    def set_bpm(self, bpm: float):
        pass

    def on_beat(self, beat_count: int):
        # Peak button blink at BPM.
        if self._held_mood is not None:
            self._blink_on = not self._blink_on
            self._render()
        # Pulse auto-return countdown.
        if self._pulse_remaining_beats > 0:
            self._pulse_remaining_beats -= 1
            if self._pulse_remaining_beats == 0:
                self._finish_pulse()
        elif self._pending_pulse is not None:
            self._fire_pulse()

    # -- lifecycle --------------------------------------------------------- #

    def enter(self):
        self._held_mood = None
        self._peak_return_to = None
        self._blink_on = False
        self._pending_pulse = None
        self._pulse_return_to = None
        self._pulse_remaining_beats = 0
        self._entry_row = 0
        self._entry_accum = 0.0
        self._clear_hint()
        self._render()

    def exit(self):
        self.clear_pages()
        self.clear()
        self.commit()
        self._send_event({"event": "FORCE_LOOK", "look": None})

    def tick(self, delta_ms: float):
        super().tick(delta_ms)
        # Entry sweep: reveal mood rows top→bottom once on entry.
        if self._entry_row < len(self.moods):
            self._entry_accum += delta_ms
            if self._entry_accum >= ENTRY_ROW_MS:
                self._entry_accum = 0.0
                self._entry_row += 1
                self._render()
        # Help text scroll + expiry.
        if self._hint_text:
            now = time.monotonic() * 1000
            if self._hint_scroll >= self._hint_max:
                self._clear_hint()
                self._render()
            elif now - self._hint_last_tick >= HINT_SCROLL_MS:
                self._hint_last_tick = now
                self._hint_scroll += 1
                self._render()

    # -- events ------------------------------------------------------------ #

    def handle_grid_event(self, event: GridEvent):
        if not event.pressed:
            return
        mood_idx = self._row_to_mood(event.y)
        if mood_idx is None or mood_idx >= len(self.moods):
            return
        scenes = self.moods[mood_idx].get("scenes") or []
        if event.x >= len(scenes):
            return
        self._cue(mood_idx, scenes[event.x])

    def handle_control_event(self, event: ControlEvent):
        idx = event.control_id - 100
        if not (0 <= idx < len(self.moods)):
            return
        if "PRESS" in event.event_type.name:
            self._start_peak(idx)
        else:
            self._end_peak(idx)

    # -- cueing ------------------------------------------------------------ #

    def _cue(self, mood_idx: int, scene: dict):
        if scene.get("cue") == "pulse":
            self._pulse_return_to = self._current_scene
            self._pending_pulse = scene
            self._show_help(scene["name"])
            return
        self._current_scene = scene["name"]
        self._send_event({
            "event": "FORCE_LOOK",
            "look": scene["look"],
            "fade_ms": scene.get("fade_ms", 800),
            "scene": scene["name"],
        })
        self._show_help(scene["name"])
        self._render()

    def _fire_pulse(self):
        scene = self._pending_pulse
        self._pending_pulse = None
        if scene is None:
            return
        self._current_scene = scene["name"]
        self._send_event({
            "event": "FORCE_LOOK",
            "look": scene["look"],
            "fade_ms": scene.get("fade_ms", 150),
            "scene": scene["name"],
            "pulse": True,
        })
        self._pulse_remaining_beats = max(1, scene.get("pulse_beats", 1))

    def _finish_pulse(self):
        if self._pulse_return_to:
            for m in self.moods:
                for s in m.get("scenes") or []:
                    if s["name"] == self._pulse_return_to:
                        self._current_scene = s["name"]
                        self._send_event({
                            "event": "FORCE_LOOK",
                            "look": s["look"],
                            "fade_ms": s.get("fade_ms", 800),
                            "scene": s["name"],
                        })
                        break
        else:
            self._current_scene = None
            self._send_event({"event": "FORCE_LOOK", "look": None})
        self._pulse_return_to = None
        self._pulse_remaining_beats = 0
        self._render()

    def _start_peak(self, mood_idx: int):
        mood = self.moods[mood_idx]
        peak = mood.get("peak") or {}
        look = peak.get("look")
        if not look:
            return
        self._held_mood = mood_idx
        self._peak_return_to = self._current_scene
        self._blink_on = True
        self._send_event({
            "event": "FORCE_LOOK",
            "look": look,
            "fade_ms": peak.get("fade_ms", 120),
            "scene": mood["name"] + " PEAK",
        })
        self._show_help(mood["name"] + " PEAK")
        self._render()

    def _end_peak(self, mood_idx: int):
        if self._held_mood != mood_idx:
            return
        self._held_mood = None
        if self._peak_return_to:
            for m in self.moods:
                for s in m.get("scenes") or []:
                    if s["name"] == self._peak_return_to:
                        self._send_event({
                            "event": "FORCE_LOOK",
                            "look": s["look"],
                            "fade_ms": s.get("fade_ms", 800),
                            "scene": s["name"],
                        })
                        break
        else:
            self._send_event({"event": "FORCE_LOOK", "look": None})
        self._peak_return_to = None
        self._blink_on = False
        self._render()

    # -- feed / help ------------------------------------------------------- #

    def _send_event(self, event: dict):
        try:
            with open(self.feed_path, "a") as f:
                f.write(json.dumps(event) + "\n")
                f.flush()
        except OSError as exc:
            logger.warning("LightShow: feed write failed: %s", exc)

    def _show_help(self, text: str):
        self._hint_text = (text or "").upper()
        self._hint_scroll = 0.0
        self._hint_max = HINT_LEAD_PX + len(self._hint_text) * HINT_CHAR_W + HINT_TRAIL_PX
        self._hint_last_tick = time.monotonic() * 1000

    def _clear_hint(self):
        self._hint_text = ""
        self._hint_scroll = 0.0
        self._hint_max = 0.0

    def _hint_active(self) -> bool:
        return bool(self._hint_text)

    # -- layout ------------------------------------------------------------ #

    def _row_to_mood(self, y: int) -> int | None:
        try:
            return MOOD_ROWS.index(y)
        except ValueError:
            return None

    # -- rendering --------------------------------------------------------- #

    def _render(self):
        self.clear()

        if self._hint_active():
            self._render_hint()
        else:
            self._render_scene_grid()

        # Right column A-E: mood identity light; the held peak button blinks at
        # BPM (OFF on the off-beat) so you can see it's live.
        for i in range(8):
            if i < len(self.moods):
                if i == self._held_mood and not self._blink_on:
                    color = LogicalColor.OFF
                else:
                    color = MOOD_COLORS[i]
                self.controller.send_right_column_led(i, color)
            else:
                self.controller.send_right_column_led(i, LogicalColor.OFF)

        self.commit()

    def _render_scene_grid(self):
        for mood_idx, mood in enumerate(self.moods):
            y = MOOD_ROWS[mood_idx]
            if mood_idx >= self._entry_row:
                continue  # not revealed yet (entry sweep)
            scenes = mood.get("scenes") or []
            for x, scene in enumerate(scenes):
                if x >= 8:
                    break
                if scene["name"] == self._current_scene:
                    color = ACTIVE_COLOR
                elif scene.get("cue") == "pulse":
                    color = PULSE_COLOR
                else:
                    color = SNAP_COLOR
                self.grid.set_cell(x, y, color)

    def _render_hint(self):
        """Scrolling 5×5 help text in RED (same glyph style as the guitar
        screen). Lead/trail blank space so it enters and exits cleanly."""
        for char_idx, ch in enumerate(self._hint_text):
            glyph = FONT_5X5.get(ch, FONT_5X5.get("?", ["00000"] * 5))
            x0 = int(HINT_LEAD_PX + char_idx * HINT_CHAR_W - self._hint_scroll)
            for row in range(5):
                for col in range(5):
                    if glyph[row][col] == "1":
                        x = x0 + col
                        y = 7 - row
                        if 0 <= x < 8 and 0 <= y < 8:
                            self.grid.set_cell(x, y, HINT_COLOR)
