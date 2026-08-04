from typing import Optional

from .base import (
    NovationController,
    EventType,
    DeviceCapabilities,
    LogicalColor,
)


class LaunchpadMiniMK1(NovationController):
    MK1_CAPS = DeviceCapabilities(
        name="Launchpad Mini MK1",
        grid_width=8,
        grid_height=8,
        function_row=True,
        function_column=True,
    )

    GRID_TOP_ROW_CC = set(range(0x68, 0x70))
    RIGHT_COLUMN_NOTES = [8, 24, 40, 56, 72, 88, 104, 120]

    def __init__(self, midi_manager, device_name: str = "Launchpad Mini"):
        super().__init__(midi_manager, device_name, self.MK1_CAPS)

    def parse_midi(self, message: list[int]) -> Optional[tuple[EventType, dict]]:
        if not message:
            return None

        status = message[0] & 0xF0

        if status == 0x90 and len(message) >= 3:
            note = message[1]
            velocity = message[2]

            if note in self.RIGHT_COLUMN_NOTES:
                idx = self.RIGHT_COLUMN_NOTES.index(note)
                event_type = EventType.FUNCTION_PRESS if velocity > 0 else EventType.FUNCTION_RELEASE
                return (event_type, {
                    "id": idx + 100,
                    "value": velocity,
                    "region": "right_column",
                })

            x = note % 16
            y = 7 - (note // 16)

            if 0 <= x < 8 and 0 <= y < 8:
                event_type = EventType.GRID_PRESS if velocity > 0 else EventType.GRID_RELEASE
                return (event_type, {"x": x, "y": y, "velocity": velocity})

            return None

        if status == 0xB0 and len(message) >= 3:
            controller = message[1]
            value = message[2]

            if controller in self.GRID_TOP_ROW_CC:
                idx = controller - 0x68
                event_type = EventType.FUNCTION_PRESS if value > 0 else EventType.FUNCTION_RELEASE
                return (event_type, {
                    "id": idx + 200,
                    "value": value,
                    "region": "top_row",
                })

        return None

    def send_led(self, x: int, y: int, color: LogicalColor):
        if not (0 <= x < 8 and 0 <= y < 8):
            return

        hw_color = self.color_mapper.to_hardware(color)
        note = (7 - y) * 16 + x
        self.midi_manager.send_message(self.device_name, [0x90, note, hw_color])

    def send_top_row_led(self, index: int, color: LogicalColor):
        if not (0 <= index < 8):
            return
        hw_color = self.color_mapper.to_hardware(color)
        cc = 0x68 + index
        self.midi_manager.send_message(self.device_name, [0xB0, cc, hw_color])

    def send_right_column_led(self, index: int, color: LogicalColor):
        if not (0 <= index < 8):
            return
        hw_color = self.color_mapper.to_hardware(color)
        note = self.RIGHT_COLUMN_NOTES[index]
        self.midi_manager.send_message(self.device_name, [0x90, note, hw_color])

    def on_connect(self):
        self._reset_to_session()
        self.clear_grid()
        self._clear_top_row()
        self._clear_right_column()

    def on_disconnect(self):
        pass

    def _reset_to_session(self):
        self.midi_manager.send_message(self.device_name, [0xB0, 0x00, 0x00])
        self.midi_manager.send_message(
            self.device_name,
            [0xF0, 0x00, 0x20, 0x29, 0x02, 0x0D, 0x01, 0x00, 0xF7]
        )

    def _clear_top_row(self):
        for i in range(8):
            self.send_top_row_led(i, LogicalColor.OFF)

    def _clear_right_column(self):
        for i in range(8):
            self.send_right_column_led(i, LogicalColor.OFF)

    def reset(self):
        self.midi_manager.send_message(self.device_name, [0xB0, 0x00, 0x00])
