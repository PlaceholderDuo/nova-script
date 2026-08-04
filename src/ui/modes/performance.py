from enum import Enum, auto

from src.controllers.base import GridEvent, ControlEvent, LogicalColor
from src.ui.mode import Mode


class ClipState(Enum):
    EMPTY = auto()
    STOPPED = auto()
    PLAYING = auto()
    RECORDING = auto()
    QUEUED = auto()


CLIP_COLORS: dict[ClipState, LogicalColor] = {
    ClipState.EMPTY: LogicalColor.OFF,
    ClipState.STOPPED: LogicalColor.RED_LOW,
    ClipState.PLAYING: LogicalColor.GREEN_HIGH,
    ClipState.RECORDING: LogicalColor.RED_HIGH,
    ClipState.QUEUED: LogicalColor.AMBER_HIGH,
}


class PerformanceMode(Mode):
    def __init__(self, grid, controller, midi_manager=None, osc_bridge=None):
        super().__init__("performance", grid, controller)
        self.midi_manager = midi_manager
        self.osc_bridge = osc_bridge
        self._num_tracks = 8
        self._num_scenes = 8
        self._clips: list[list[ClipState]] = [
            [ClipState.STOPPED] * self._num_tracks
            for _ in range(self._num_scenes)
        ]
        self._active_scene: int = -1

    def enter(self):
        self._render()

    def exit(self):
        self.clear()
        self.commit()

    def handle_grid_event(self, event: GridEvent):
        if event.pressed:
            self.track_press(event)
            return

        resolution = self.resolve_press(event)
        if resolution == "invalid":
            return

        if resolution == "long":
            self._clear_clip(event.x, event.y)
        else:
            self._toggle_clip(event.x, event.y)

        self._render()

    def handle_control_event(self, event: ControlEvent):
        if not event.event_type.name.endswith("_PRESS"):
            return

        if event.control_id >= 200:
            track = event.control_id - 200
            if 0 <= track < self._num_tracks:
                self._stop_track(track)
                self._render()

        elif event.control_id >= 100:
            scene = 7 - (event.control_id - 100)
            if 0 <= scene < self._num_scenes:
                self._launch_scene(scene)
                self._render()

    def _toggle_clip(self, x: int, y: int):
        scene = self._num_scenes - 1 - y
        track = x

        if not (0 <= track < self._num_tracks and 0 <= scene < self._num_scenes):
            return

        current = self._clips[scene][track]
        if current == ClipState.EMPTY:
            return

        if current == ClipState.PLAYING:
            self._clips[scene][track] = ClipState.STOPPED
            self._stop_osc(track, scene)
        else:
            for s in range(self._num_scenes):
                if self._clips[s][track] == ClipState.PLAYING:
                    self._clips[s][track] = ClipState.STOPPED
            self._clips[scene][track] = ClipState.PLAYING
            self._launch_osc(track, scene)

        self._active_scene = scene

    def _clear_clip(self, x: int, y: int):
        scene = self._num_scenes - 1 - y
        track = x
        if 0 <= track < self._num_tracks and 0 <= scene < self._num_scenes:
            if self._clips[scene][track] == ClipState.PLAYING:
                self._clips[scene][track] = ClipState.STOPPED
            else:
                self._clips[scene][track] = ClipState.EMPTY

    def _launch_scene(self, scene: int):
        for track in range(self._num_tracks):
            if self._clips[scene][track] != ClipState.EMPTY:
                for s in range(self._num_scenes):
                    if s != scene and self._clips[s][track] == ClipState.PLAYING:
                        self._clips[s][track] = ClipState.STOPPED
                self._clips[scene][track] = ClipState.PLAYING
                self._launch_osc(track, scene)
        self._active_scene = scene

    def _stop_track(self, track: int):
        for scene in range(self._num_scenes):
            if self._clips[scene][track] == ClipState.PLAYING:
                self._clips[scene][track] = ClipState.STOPPED
        self._stop_osc(track, None)

    def _launch_osc(self, track: int, scene: int):
        if self.osc_bridge:
            self.osc_bridge.send(f"/nova/clip/launch", track, scene)
        if self.midi_manager:
            note = 60 + track
            vel = 100 + scene * 5
            self.midi_manager.send_message(
                self.controller.device_name,
                [0x90, note, vel],
            )

    def _stop_osc(self, track: int, scene: int | None):
        if self.osc_bridge:
            self.osc_bridge.send(f"/nova/clip/stop", track, scene if scene is not None else -1)

    def _render(self):
        self.clear()

        for scene in range(self._num_scenes):
            display_y = self._num_scenes - 1 - scene
            for track in range(self._num_tracks):
                state = self._clips[scene][track]
                color = CLIP_COLORS[state]
                self.grid.set_cell(track, display_y, color)

        for col in range(self._num_tracks):
            has_playing = any(
                self._clips[s][col] == ClipState.PLAYING
                for s in range(self._num_scenes)
            )
            if not has_playing:
                pass

        self.commit()
