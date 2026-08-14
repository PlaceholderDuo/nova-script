"""
Clip Launcher — 8×8 grid of launchable clips with MIDI + OSC output.
Hold Button 3 (control_id 202) to enter/exit edit mode.
Edit mode: pads pulse at BPM, press to cycle colors, OFF pads don't send MIDI.
"""
import math
import time
import logging

from src.controllers.base import GridEvent, ControlEvent, LogicalColor
from src.ui.mode import Mode

logger = logging.getLogger(__name__)

MK1_COLOR_CYCLE = [
    LogicalColor.OFF,
    LogicalColor.AMBER_HIGH,
    LogicalColor.RED_HIGH,
    LogicalColor.GREEN_HIGH,
    LogicalColor.AMBER_MED,
    LogicalColor.RED_MED,
    LogicalColor.GREEN_MED,
]

DEFAULT_CLIPS = []
for scene in range(8):
    for track in range(8):
        idx = scene * 8 + track
        active = (scene < 4)
        DEFAULT_CLIPS.append({
            "track": track, "scene": scene,
            "label": f"T{track+1}S{scene+1}",
            "midi_note": 60 + track + scene * 12,
            "midi_channel": 0,
            "midi_vel": 100,
            "osc_addr": f"/nova/clip/{track}/{scene}",
        })


class ClipLauncherMode(Mode):
    def __init__(self, grid, controller, config: dict | None = None, osc_bridge=None, midi_manager=None):
        super().__init__("clip_launcher", grid, controller)
        self.osc_bridge = osc_bridge
        self.midi_manager = midi_manager
        clips_cfg = config.get("clips", DEFAULT_CLIPS) if config else DEFAULT_CLIPS
        self._clips = clips_cfg
        self._playing: set[int] = set()
        self._num_tracks = 8
        self._num_scenes = 8
        self._edit_mode: bool = False
        self._edit_press_time: float = 0.0
        self._clip_colors: list[LogicalColor] = [LogicalColor.OFF] * 64
        self._bpm: float = 120.0
        self._init_default_colors()

    def _init_default_colors(self):
        # 4 even quadrants (top/bottom × left/right):
        #   Amber  top-left, Green top-right,
        #   Red 80% (MED) bottom-right, OFF bottom-left.
        for scene in range(self._num_scenes):
            for track in range(self._num_tracks):
                idx = scene * 8 + track
                top = scene < 4
                left = track < 4
                if top and left:
                    self._clip_colors[idx] = LogicalColor.AMBER_HIGH
                elif top and not left:
                    self._clip_colors[idx] = LogicalColor.GREEN_HIGH
                elif not top and not left:
                    self._clip_colors[idx] = LogicalColor.RED_MED
                else:
                    self._clip_colors[idx] = LogicalColor.OFF

    def set_bpm(self, bpm: float):
        self._bpm = bpm

    def enter(self):
        self._render()

    def exit(self):
        self._edit_mode = False
        self.clear()
        self.commit()

    def handle_grid_event(self, event: GridEvent):
        if event.pressed:
            if self.is_debounced():
                return
            if self._edit_mode:
                self._edit_press(event.x, event.y)
                return
            x, y = event.x, event.y
            if y == 0:
                self._stop_track(x)
                self._render()
                return
            idx = (self._num_scenes - 1 - y) * self._num_tracks + x
            if self._clip_colors[idx] == LogicalColor.OFF:
                return
            self.track_press(event)
        else:
            if self._edit_mode:
                return
            resolution = self.resolve_press(event)
            if resolution == "invalid":
                return
            x, y = event.x, event.y
            if resolution == "long":
                self._clear_clip(x, self._num_scenes - 1 - y)
            else:
                self._toggle_clip(x, self._num_scenes - 1 - y)
            self._render()

    def handle_control_event(self, event: ControlEvent):
        is_press = "PRESS" in event.event_type.name

        if event.control_id == 202:
            if is_press:
                self._edit_press_time = time.monotonic()
                if self._edit_mode:
                    self._edit_mode = False
                    logger.info("Clip Launcher edit mode: OFF (saved)")
                    self._render()
                    return
            else:
                if self._edit_mode:
                    return
                elapsed = (time.monotonic() - self._edit_press_time) * 1000
                if elapsed >= 1000:
                    self._edit_mode = True
                    logger.info("Clip Launcher edit mode: ON")
                self._render()
            return

        if not is_press:
            return

        if self._edit_mode:
            return

        if event.control_id >= 100:
            scene_idx = event.control_id - 100
            scene = self._num_scenes - 1 - scene_idx
            if 0 <= scene < self._num_scenes:
                self._launch_scene(scene)
                self._render()

    def _edit_press(self, x: int, y: int):
        scene = self._num_scenes - 1 - y
        idx = scene * self._num_tracks + x
        if not (0 <= idx < 64):
            return
        current = self._clip_colors[idx]
        if current == LogicalColor.OFF:
            self._clip_colors[idx] = MK1_COLOR_CYCLE[1]
        else:
            try:
                ci = MK1_COLOR_CYCLE.index(current)
                next_ci = (ci + 1) % len(MK1_COLOR_CYCLE)
                self._clip_colors[idx] = MK1_COLOR_CYCLE[next_ci]
            except ValueError:
                self._clip_colors[idx] = MK1_COLOR_CYCLE[0]
        self._render()

    def _toggle_clip(self, track: int, scene: int):
        idx = scene * self._num_tracks + track
        if self._clip_colors[idx] == LogicalColor.OFF:
            return
        if idx in self._playing:
            self._playing.discard(idx)
            self._stop_output(track, scene, idx)
        else:
            for s in range(self._num_scenes):
                sidx = s * self._num_tracks + track
                self._playing.discard(sidx)
            self._playing.add(idx)
            self._launch_output(track, scene, idx)

    def _launch_scene(self, scene: int):
        for track in range(self._num_tracks):
            idx = scene * self._num_tracks + track
            if self._clip_colors[idx] == LogicalColor.OFF:
                continue
            for s in range(self._num_scenes):
                sidx = s * self._num_tracks + track
                self._playing.discard(sidx)
            self._playing.add(idx)
            self._launch_output(track, scene, idx)

    def _stop_track(self, track: int):
        for s in range(self._num_scenes):
            self._playing.discard(s * self._num_tracks + track)

    def _clear_clip(self, track: int, scene: int):
        idx = scene * self._num_tracks + track
        self._playing.discard(idx)
        self._clip_colors[idx] = LogicalColor.OFF

    def _launch_output(self, track: int, scene: int, idx: int):
        clip = self._clips[idx] if idx < len(self._clips) else None
        if clip is None:
            return
        if self.midi_manager:
            note = clip.get("midi_note", 60)
            channel = clip.get("midi_channel", 0)
            vel = clip.get("midi_vel", 100)
            self.midi_manager.send_force([0x90 + channel, note, vel])
        if self.osc_bridge:
            addr = clip.get("osc_addr", f"/nova/clip/{track}/{scene}")
            self.osc_bridge.send(addr, 1)

    def _stop_output(self, track: int, scene: int, idx: int):
        clip = self._clips[idx] if idx < len(self._clips) else None
        if clip is None:
            return
        if self.midi_manager:
            note = clip.get("midi_note", 60)
            channel = clip.get("midi_channel", 0)
            self.midi_manager.send_force([0x80 + channel, note, 0])
        if self.osc_bridge:
            addr = clip.get("osc_addr", f"/nova/clip/{track}/{scene}")
            self.osc_bridge.send(addr, 0)

    def tick(self, delta_ms: float):
        if self._edit_mode and int(time.monotonic() * 10) % 2 == 0:
            self._render()

    def _render(self):
        self.clear()

        beat_phase = (time.monotonic() * self._bpm / 60.0) % 1.0
        pulse = (math.sin(beat_phase * math.pi * 2) + 1) / 2

        for scene in range(self._num_scenes):
            display_y = self._num_scenes - 1 - scene
            for track in range(self._num_tracks):
                idx = scene * self._num_tracks + track
                pad_color = self._clip_colors[idx]

                if idx in self._playing:
                    color = LogicalColor.GREEN_HIGH
                    self.grid.set_cell(track, display_y, color)
                elif self._edit_mode and pad_color != LogicalColor.OFF:
                    p = 0.75 + pulse * 0.25
                    color = pad_color
                    self.grid.set_cell(track, display_y, color)
                elif self._edit_mode and pad_color == LogicalColor.OFF:
                    if pulse < 0.05:
                        self.grid.set_cell(track, display_y, LogicalColor.AMBER_LOW)
                    else:
                        self.grid.set_cell(track, display_y, LogicalColor.OFF)
                elif pad_color != LogicalColor.OFF:
                    self.grid.set_cell(track, display_y, pad_color)

        for track in range(self._num_tracks):
            has_playing = any(
                (s * self._num_tracks + track) in self._playing
                for s in range(self._num_scenes)
            )
            color = LogicalColor.RED_HIGH if has_playing else LogicalColor.OFF
            self.grid.set_cell(track, 0, color)

        self.commit()
