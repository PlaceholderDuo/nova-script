"""
Nova-Script Virtualizer — Virtual hardware test harness.

Simulates button presses and renders LED output as ASCII grid.
Enables full pipeline testing without physical hardware.

ASCII color map:
  OFF       → '·'
  RED_LOW   → 'r'    RED_MED   → 'R'    RED_HIGH   → '#'
  GREEN_LOW → 'g'    GREEN_MED → 'G'    GREEN_HIGH → '$'
  AMBER_LOW → 'a'    AMBER_MED → 'A'    AMBER_HIGH → '@'
"""
import time
from typing import Optional
from src.controllers.color_map import LogicalColor
from src.controllers.launchpad_mk1 import LaunchpadMiniMK1
from src.controllers.launchkey_mk2 import Launchkey49MK2
from src.controllers.base import GridEvent, ControlEvent, EventType
from src.layout.grid import LogicalGrid


ASCII_COLORS: dict[LogicalColor, str] = {
    LogicalColor.OFF: "·",
    LogicalColor.RED_LOW: "r",
    LogicalColor.RED_MED: "R",
    LogicalColor.RED_HIGH: "#",
    LogicalColor.GREEN_LOW: "g",
    LogicalColor.GREEN_MED: "G",
    LogicalColor.GREEN_HIGH: "$",
    LogicalColor.AMBER_LOW: "a",
    LogicalColor.AMBER_MED: "A",
    LogicalColor.AMBER_HIGH: "@",
    LogicalColor.YELLOW_LOW: "a",
    LogicalColor.YELLOW_MED: "A",
    LogicalColor.YELLOW_HIGH: "@",
    LogicalColor.ORANGE_LOW: "r",
    LogicalColor.ORANGE_MED: "R",
    LogicalColor.ORANGE_HIGH: "#",
    LogicalColor.WHITE_LOW: "·",
    LogicalColor.WHITE_MED: "A",
    LogicalColor.WHITE_HIGH: "@",
    LogicalColor.BLUE_LOW: "g",
    LogicalColor.BLUE_MED: "G",
    LogicalColor.BLUE_HIGH: "$",
    LogicalColor.PURPLE_LOW: "r",
    LogicalColor.PURPLE_MED: "R",
    LogicalColor.PURPLE_HIGH: "#",
    LogicalColor.CYAN_LOW: "g",
    LogicalColor.CYAN_MED: "G",
    LogicalColor.CYAN_HIGH: "$",
}


class VirtualMidiManager:
    """Stores MIDI output in a buffer. Allows injecting MIDI input."""

    def __init__(self):
        self.sent_messages: list[list[int]] = []
        self._input_callback = None
        self._poll_running = False

    def send_message(self, device_name: str, message: list[int], target: str = "main"):
        self.sent_messages.append(list(message))

    def register_device(self, name: str, input_callback):
        pass

    def inject_raw_midi(self, message: list[int]):
        """Simulate a MIDI event arriving from hardware."""
        pass

    def set_on_connect(self, cb): pass
    def set_on_disconnect(self, cb): pass

    async def start(self): pass
    async def stop(self): pass

    @property
    def last_message(self) -> Optional[list[int]]:
        return self.sent_messages[-1] if self.sent_messages else None

    def clear(self):
        self.sent_messages.clear()


class VirtualGrid:
    """ASCII rendering of Launchpad LED state."""

    def __init__(self, width: int = 8, height: int = 8):
        self.width = width
        self.height = height
        self._cells: list[list[LogicalColor]] = [
            [LogicalColor.OFF] * width for _ in range(height)
        ]
        self.top_row: list[LogicalColor] = [LogicalColor.OFF] * 8
        self.right_col: list[LogicalColor] = [LogicalColor.OFF] * 8

    def set_cell(self, x: int, y: int, color: LogicalColor):
        if 0 <= x < self.width and 0 <= y < self.height:
            self._cells[y][x] = color

    def set_top(self, index: int, color: LogicalColor):
        if 0 <= index < 8:
            self.top_row[index] = color

    def set_right(self, index: int, color: LogicalColor):
        if 0 <= index < 8:
            self.right_col[index] = color

    def get_cell(self, x: int, y: int) -> LogicalColor:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self._cells[y][x]
        return LogicalColor.OFF

    def clear(self):
        for y in range(self.height):
            for x in range(self.width):
                self._cells[y][x] = LogicalColor.OFF
        self.top_row = [LogicalColor.OFF] * 8
        self.right_col = [LogicalColor.OFF] * 8

    def render(self, title: str = "") -> str:
        lines = []
        if title:
            lines.append(f"  {title}")
            lines.append(f"  {'─' * len(title)}")

        lines.append("  ┌─1─2─3─4─5─6─7─8─┐")

        for y in range(self.height - 1, -1, -1):
            row_chars = [ASCII_COLORS.get(c, "?") for c in self._cells[y]]
            extra = f" {ASCII_COLORS.get(self.right_col[y], '·')}" if y < len(self.right_col) else ""
            lines.append(f"  │ {' '.join(row_chars)} │{extra}")

        top_str = " ".join(ASCII_COLORS.get(c, "?") for c in self.top_row)
        lines.append(f"  └─{top_str}─┘")
        lines.append(f"    1 2 3 4 5 6 7 8")
        return "\n".join(lines)

    def __repr__(self):
        return self.render()


class VirtualLaunchpad:
    """
    Virtual Launchpad Mini MK1 for testing.
    Captures LED output as ASCII grid. Accepts simulated button presses.
    """

    def __init__(self):
        self.vmidi = VirtualMidiManager()
        self.controller = LaunchpadMiniMK1(self.vmidi)
        self.grid = VirtualGrid(8, 8)
        self._pressed_buttons: set[int] = set()

        # Re-wire LED output to our virtual grid
        def virtual_send_led(x, y, color):
            self.grid.set_cell(x, y, color)

        def virtual_send_top(index, color):
            self.grid.set_top(index, color)

        def virtual_send_right(index, color):
            self.grid.set_right(index, color)

        self.controller.send_led = virtual_send_led
        self.controller.send_top_row_led = virtual_send_top
        self.controller.send_right_column_led = virtual_send_right
        self.controller.clear_grid = lambda: self.grid.clear()
        self.controller._clear_top_row = lambda: [self.grid.set_top(i, LogicalColor.OFF) for i in range(8)]
        self.controller._clear_right_column = lambda: [self.grid.set_right(i, LogicalColor.OFF) for i in range(8)]
        self.controller._grid_state = self.grid._cells

    def on_connect(self):
        self.controller.on_connect()

    def render(self, title: str = "") -> str:
        return self.grid.render(title)

    # ── Button simulation ──────────────────────────────

    def press(self, x: int, y: int, velocity: int = 127):
        """Simulate pressing a grid pad."""
        self._inject_event(GridEvent(x, y, True, velocity))

    def release(self, x: int, y: int):
        """Simulate releasing a grid pad."""
        self._inject_event(GridEvent(x, y, False, 0))

    def tap(self, x: int, y: int, hold_ms: int = 50):
        """Full press+release of a grid pad."""
        self.press(x, y)
        if hold_ms > 0:
            time.sleep(hold_ms / 1000)
        self.release(x, y)

    def long_press(self, x: int, y: int, duration_ms: int = 600):
        """Long press: press, wait, release."""
        self.press(x, y)
        time.sleep(duration_ms / 1000)
        self.release(x, y)

    def press_control(self, control_id: int, value: int = 127):
        """Simulate pressing a top row or right column button."""
        self._inject_control(control_id, True, value)

    def release_control(self, control_id: int):
        """Simulate releasing a top row or right column button."""
        self._inject_control(control_id, False, 0)

    def tap_control(self, control_id: int):
        """Tap a control button."""
        self.press_control(control_id)
        self.release_control(control_id)

    def press_top(self, index: int):
        """Press top row button (index 0-7 = buttons 1-8)."""
        self.press_control(200 + index)

    def release_top(self, index: int):
        self.release_control(200 + index)

    def tap_top(self, index: int):
        """Tap top row button."""
        self.press_top(index)
        self.release_top(index)

    def press_right(self, index: int):
        """Press right column button (index 0-7, top to bottom)."""
        self.press_control(100 + index)

    def release_right(self, index: int):
        self.release_control(100 + index)

    def tap_right(self, index: int):
        self.press_right(index)
        self.release_right(index)

    def combo(self, btn1: int, btn2: int):
        """Simulate a two-button combo: hold btn1, press btn2, release both."""
        self.press_top(btn1)
        time.sleep(0.05)
        self.press_top(btn2)
        time.sleep(0.05)
        self.release_top(btn2)
        self.release_top(btn1)

    # ── Assertions ─────────────────────────────────────

    def assert_cell(self, x: int, y: int, color: LogicalColor):
        actual = self.grid.get_cell(x, y)
        assert actual == color, (
            f"Cell ({x},{y}): expected {color.name} ({ASCII_COLORS[color]}), "
            f"got {actual.name} ({ASCII_COLORS[actual]})"
        )

    def assert_top(self, index: int, color: LogicalColor):
        actual = self.grid.top_row[index]
        assert actual == color, (
            f"Top [{index}]: expected {color.name}, got {actual.name}"
        )

    def assert_all_off(self):
        for y in range(8):
            for x in range(8):
                self.assert_cell(x, y, LogicalColor.OFF)

    # ── Internals ──────────────────────────────────────

    def _inject_event(self, event: GridEvent):
        if self.controller._on_grid_event:
            self.controller._on_grid_event(event)

    def _inject_control(self, control_id: int, pressed: bool, value: int):
        event_type = EventType.FUNCTION_PRESS if pressed else EventType.FUNCTION_RELEASE
        event = ControlEvent(control_id, value, event_type)
        if self.controller._on_control_event:
            self.controller._on_control_event(event)


class VirtualLaunchkey:
    """Virtual Launchkey 49 MK2 for testing."""

    def __init__(self):
        self.vmidi = VirtualMidiManager()
        self.controller = Launchkey49MK2(self.vmidi)
        self.grid = VirtualGrid(8, 2)

        def virtual_send_led(x, y, color):
            self.grid.set_cell(x, y, color)

        self.controller.send_led = virtual_send_led
        self.controller._grid_state = self.grid._cells

    def render(self, title: str = "") -> str:
        return self.grid.render(title)

    def press_pad(self, index: int, velocity: int = 127):
        """Press pad 0-15 (row-major)."""
        x = index % 8
        y = index // 8
        self._inject(GridEvent(x, y, True, velocity))

    def release_pad(self, index: int):
        x = index % 8
        y = index // 8
        self._inject(GridEvent(x, y, False, 0))

    def tap_pad(self, index: int):
        self.press_pad(index)
        self.release_pad(index)

    def turn_knob(self, index: int, value: int):
        self._inject_ctrl(index, value, EventType.KNOB)

    def move_fader(self, index: int, value: int):
        self._inject_ctrl(index, value, EventType.FADER)

    def press_transport(self, button: int):
        self._inject_ctrl(button, 127, EventType.TRANSPORT)

    def _inject(self, event: GridEvent):
        if self.controller._on_grid_event:
            self.controller._on_grid_event(event)

    def _inject_ctrl(self, control_id: int, value: int, event_type: EventType):
        event = ControlEvent(control_id, value, event_type)
        if self.controller._on_control_event:
            self.controller._on_control_event(event)
