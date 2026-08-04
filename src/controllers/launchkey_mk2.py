from typing import Optional

from .base import (
    NovationController,
    EventType,
    DeviceCapabilities,
    LogicalColor,
)


class Launchkey49MK2(NovationController):
    LAUNCHKEY_CAPS = DeviceCapabilities(
        name="Launchkey 49 MK2",
        grid_width=8,
        grid_height=2,
        has_velocity_pads=True,
        num_knobs=8,
        num_faders=8,
        has_transport=True,
        function_row=False,
        function_column=False,
    )

    def __init__(self, midi_manager, device_name: str = "Launchkey 49"):
        super().__init__(midi_manager, device_name, self.LAUNCHKEY_CAPS)

    def parse_midi(self, message: list[int]) -> Optional[tuple[EventType, dict]]:
        if not message or len(message) < 3:
            return None

        status = message[0] & 0xF0

        if status == 0x90 and len(message) >= 3:
            note = message[1]
            velocity = message[2]
            pad_idx = note - 36
            if 0 <= pad_idx < 16:
                x = pad_idx % 8
                y = pad_idx // 8
                event_type = EventType.GRID_PRESS if velocity > 0 else EventType.GRID_RELEASE
                return (event_type, {
                    "x": x, "y": y, "velocity": velocity,
                })

        if status == 0xB0 and len(message) >= 3:
            cc = message[1]
            value = message[2]

            if 21 <= cc <= 28:
                return (EventType.KNOB, {"control_id": cc - 21, "value": value})
            if 41 <= cc <= 48:
                return (EventType.FADER, {"control_id": cc - 41, "value": value})

            if cc in (114, 115, 116, 117):
                transport_map = {114: 0, 115: 1, 116: 2, 117: 3}
                return (EventType.TRANSPORT, {
                    "control_id": transport_map[cc],
                    "value": value,
                })

        return None

    def send_led(self, x: int, y: int, color: LogicalColor):
        if not (0 <= x < 8 and 0 <= y < 2):
            return
        hw_color = self.color_mapper.to_hardware(color)
        note = 36 + y * 8 + x
        self.midi_manager.send_message(self.device_name, [0x90, note, hw_color])

    def on_connect(self):
        self.clear_grid()

    def on_disconnect(self):
        pass
