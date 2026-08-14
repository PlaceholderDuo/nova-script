"""
Light Show Mode — live cue lighting scenes from the Launchpad.

The Launchpad becomes a lighting controller: pick a *mood* (a library of
scenes) from the right column, then cue scenes from the grid. Scenes are
pushed to the lighting engine over /tmp/lighting_feed (the same JSON-lines
feed the TUI and iPhone lighting page write to), so the engine drives
QLC+ (DMX) + Govee rods.

Scene types:
  snap   — tap to fade to this scene and hold.
  pulse  — tap to fire a short burst (e.g. a flash/blinder), then auto-return
           to whatever scene was active before.

Master clock: the mode receives BPM + beat callbacks from the engine, which
gets them from the configured clock source (Akai Force MIDI clock by default,
REAPER OSC or internal as alternatives). Pulse durations can be expressed in
beats so they stay musical.
"""
import logging
import time

from src.controllers.base import GridEvent, ControlEvent, LogicalColor
from src.ui.mode import Mode

logger = logging.getLogger(__name__)

# Right-column mood selectors (A=100, B=101, ... H=107)
MOOD_COLORS = [
    LogicalColor.AMBER_HIGH,   # Standard
    LogicalColor.GREEN_HIGH,   # Acoustic Candlelight
    LogicalColor.BLUE_HIGH,    # EDM
    LogicalColor.RED_HIGH,     # High Energy
    LogicalColor.YELLOW_HIGH,  # Ballad
]

# Grid: 2 rows of 4 → 8 scene pads. Rows y=7..6, cols x=0..3 / x=4..7.
SCENE_LAYOUT = [(x, 7 - r) for r in range(2) for x in range(0, 4)] + \
               [(x, 7 - r) for r in range(2) for x in range(4, 8)]
# → [(0,7),(1,7),(2,7),(3,7),(4,7),(5,7),(6,7),(7,7),  top row
#    (0,6),(1,6),...                                        second row]


class LightShowMode(Mode):
    name = "light_show"

    def __init__(self, grid, controller, config: dict | None = None, feed_path: str = "/tmp/lighting_feed"):
        super().__init__("light_show", grid, controller)
        cfg = config or {}
        self.feed_path = feed_path

        # moods: list of {name, scenes: [{name, look, fade_ms, cue, pulse_beats}]}
        self.moods = cfg.get("moods") or []
        self._mood_idx = 0

        self._current_scene: str | None = None   # currently-active scene name
        self._return_to: str | None = None       # scene to return to after a pulse
        self._pulse_until: float = 0.0           # monotonic deadline for pulse return
        self._pulse_remaining_beats: int = 0
        self._bpm: float = 120.0
        self._pending_pulse: str | None = None   # scene queued for next beat

    # -- engine hooks ------------------------------------------------------ #

    def set_bpm(self, bpm: float):
        self._bpm = bpm

    def on_beat(self, beat_count: int):
        """Called by the engine on each clock beat (any source). Drives pulses."""
        if self._pulse_remaining_beats > 0:
            self._pulse_remaining_beats -= 1
            if self._pulse_remaining_beats == 0:
                self._finish_pulse()
        elif self._pending_pulse:
            self._fire_pulse(self._pending_pulse)
            self._pending_pulse = None

    # -- event handling ---------------------------------------------------- #

    def enter(self):
        self._mood_idx = 0
        self._current_scene = None
        self._return_to = None
        self._pulse_remaining_beats = 0
        self._pending_pulse = None
        self._render()

    def exit(self):
        self.clear_pages()
        self.clear()
        self.commit()
        # Release manual control on exit so the auto-engine takes back over.
        self._send_event({"event": "FORCE_LOOK", "look": None})

    def handle_grid_event(self, event: GridEvent):
        if not event.pressed:
            return
        mood = self._current_mood()
        if not mood:
            return
        idx = self._scene_index_at(event.x, event.y)
        if idx is None or idx >= len(mood["scenes"]):
            return
        self._cue(idx)

    def handle_control_event(self, event: ControlEvent):
        if "PRESS" not in event.event_type.name:
            return
        # Right column A-E → mood select
        if 100 <= event.control_id <= 104:
            new_idx = event.control_id - 100
            if new_idx < len(self.moods) and new_idx != self._mood_idx:
                self._mood_idx = new_idx
                self._current_scene = None
                self._return_to = None
                self._pulse_remaining_beats = 0
                self._pending_pulse = None
                self._render()

    # -- cueing ------------------------------------------------------------ #

    def _cue(self, idx: int):
        mood = self._current_mood()
        if not mood:
            return
        scene = mood["scenes"][idx]
        cue = scene.get("cue", "snap")

        if cue == "pulse":
            # Remember what we're returning to, then fire on the next beat so
            # the flash lands on the grid.
            self._return_to = self._current_scene
            self._pending_pulse = scene["name"]
            self._render()
        else:
            self._return_to = None
            self._pulse_remaining_beats = 0
            self._pending_pulse = None
            self._current_scene = scene["name"]
            self._send_event({
                "event": "FORCE_LOOK",
                "look": scene["look"],
                "fade_ms": scene.get("fade_ms", 800),
                "scene": scene["name"],
            })
            self._render()

    def _fire_pulse(self, scene_name: str):
        mood = self._current_mood()
        if not mood:
            return
        scene = next((s for s in mood["scenes"] if s["name"] == scene_name), None)
        if not scene:
            return
        self._current_scene = scene_name
        self._send_event({
            "event": "FORCE_LOOK",
            "look": scene["look"],
            "fade_ms": scene.get("fade_ms", 200),
            "scene": scene_name,
            "pulse": True,
        })
        beats = scene.get("pulse_beats", 1)
        self._pulse_remaining_beats = max(1, beats)

    def _finish_pulse(self):
        self._pending_pulse = None
        if self._return_to:
            # Return to the pre-pulse scene.
            mood = self._current_mood()
            scene = next((s for s in mood["scenes"] if s["name"] == self._return_to), None)
            if scene:
                self._current_scene = self._return_to
                self._send_event({
                    "event": "FORCE_LOOK",
                    "look": scene["look"],
                    "fade_ms": scene.get("fade_ms", 800),
                    "scene": scene["name"],
                })
        else:
            self._current_scene = None
            self._send_event({"event": "FORCE_LOOK", "look": None})
        self._return_to = None
        self._pulse_remaining_beats = 0
        self._render()

    # -- feed -------------------------------------------------------------- #

    def _send_event(self, event: dict):
        try:
            import os
            line = __import__("json").dumps(event) + "\n"
            with open(self.feed_path, "a") as f:
                f.write(line)
                f.flush()
        except OSError as exc:
            logger.warning("LightShow: feed write failed: %s", exc)

    # -- layout helpers ---------------------------------------------------- #

    def _current_mood(self) -> dict | None:
        if not self.moods:
            return None
        return self.moods[self._mood_idx]

    def _scene_index_at(self, x: int, y: int) -> int | None:
        try:
            return SCENE_LAYOUT.index((x, y))
        except ValueError:
            return None

    # -- rendering --------------------------------------------------------- #

    def _render(self):
        self.clear()

        mood = self._current_mood()
        if not mood:
            self.commit()
            return

        scenes = mood["scenes"]
        for idx, scene in enumerate(scenes):
            x, y = SCENE_LAYOUT[idx]
            if scene.get("cue") == "pulse":
                color = LogicalColor.RED_HIGH
            elif scene["name"] == self._current_scene:
                color = LogicalColor.GREEN_HIGH
            else:
                color = LogicalColor.AMBER_MED
            self.grid.set_cell(x, y, color)

        # Right column: A-E mood selectors (mood color, current = HIGH).
        for i in range(8):
            if i < len(self.moods):
                base = MOOD_COLORS[i % len(MOOD_COLORS)]
                color = base if i != self._mood_idx else LogicalColor.GREEN_HIGH
                self.controller.send_right_column_led(i, color)
            else:
                self.controller.send_right_column_led(i, LogicalColor.OFF)

        self.commit()
