from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

from .color_map import ColorMapper, LogicalColor


class EventType(Enum):
    GRID_PRESS = auto()
    GRID_RELEASE = auto()
    FUNCTION_PRESS = auto()
    FUNCTION_RELEASE = auto()
    KNOB = auto()
    FADER = auto()
    TRANSPORT = auto()
    PAD_PRESS = auto()
    PAD_RELEASE = auto()


@dataclass(frozen=True)
class GridEvent:
    x: int
    y: int
    pressed: bool
    velocity: int = 127
    device: str = ""


@dataclass(frozen=True)
class ControlEvent:
    control_id: int
    value: int
    event_type: EventType
    device: str = ""


@dataclass
class DeviceCapabilities:
    name: str
    grid_width: int
    grid_height: int
    has_velocity_pads: bool = False
    has_rgb: bool = False
    has_aftertouch: bool = False
    num_knobs: int = 0
    num_faders: int = 0
    has_transport: bool = False
    function_row: bool = True
    function_column: bool = True


class NovationController(ABC):
    def __init__(
        self,
        midi_manager,
        device_name: str,
        capabilities: DeviceCapabilities,
    ):
        self.midi_manager = midi_manager
        self.device_name = device_name
        self.capabilities = capabilities

        self.color_mapper = ColorMapper("mk1")

        self._grid_state: list[list[LogicalColor]] = [
            [LogicalColor.OFF] * capabilities.grid_width
            for _ in range(capabilities.grid_height)
        ]

        self._on_grid_event = None
        self._on_control_event = None

    def set_callbacks(self, on_grid_event=None, on_control_event=None):
        self._on_grid_event = on_grid_event
        self._on_control_event = on_control_event

    def handle_raw_midi(self, message: list[int]):
        parsed = self.parse_midi(message)
        if parsed is None:
            return
        event_type, data = parsed

        if event_type in (EventType.GRID_PRESS, EventType.GRID_RELEASE):
            event = GridEvent(
                x=data["x"],
                y=data["y"],
                pressed=(event_type == EventType.GRID_PRESS),
                velocity=data.get("velocity", 127),
                device=self.device_name,
            )
            if self._on_grid_event:
                self._on_grid_event(event)

        elif event_type in (EventType.FUNCTION_PRESS, EventType.FUNCTION_RELEASE):
            event = ControlEvent(
                control_id=data["id"],
                value=data.get("value", 127),
                event_type=event_type,
                device=self.device_name,
            )
            if self._on_control_event:
                self._on_control_event(event)

    @abstractmethod
    def parse_midi(self, message: list[int]) -> Optional[tuple[EventType, dict]]:
        ...

    @abstractmethod
    def send_led(self, x: int, y: int, color: LogicalColor):
        ...

    def set_grid_color(self, x: int, y: int, color: LogicalColor):
        if 0 <= x < self.capabilities.grid_width and 0 <= y < self.capabilities.grid_height:
            if self._grid_state[y][x] == color:
                return
            self._grid_state[y][x] = color
            self.send_led(x, y, color)

    def clear_grid(self):
        for y in range(self.capabilities.grid_height):
            for x in range(self.capabilities.grid_width):
                self.set_grid_color(x, y, LogicalColor.OFF)

    def reset_grid_state(self):
        """Reset _grid_state to all OFF without sending MIDI.
        Used when switching modes so the new mode's diff-based render
        doesn't collide with leftover state from the previous mode."""
        for y in range(self.capabilities.grid_height):
            for x in range(self.capabilities.grid_width):
                self._grid_state[y][x] = LogicalColor.OFF

    def refresh_grid(self):
        """Force all cells to re-send to hardware. Use after reconnect."""
        for y in range(self.capabilities.grid_height):
            for x in range(self.capabilities.grid_width):
                self.send_led(x, y, self._grid_state[y][x])

    def get_grid_color(self, x: int, y: int) -> LogicalColor:
        if 0 <= x < self.capabilities.grid_width and 0 <= y < self.capabilities.grid_height:
            return self._grid_state[y][x]
        return LogicalColor.OFF

    @property
    def grid_state(self) -> list[list[LogicalColor]]:
        return self._grid_state

    def on_connect(self):
        self.clear_grid()

    def on_disconnect(self):
        pass
