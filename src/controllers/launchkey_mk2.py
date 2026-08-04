import logging
from typing import Optional

from .base import (
    NovationController,
    EventType,
    DeviceCapabilities,
    LogicalColor,
)

logger = logging.getLogger(__name__)

LK_COLOR_PALETTE: dict[LogicalColor, int] = {
    LogicalColor.OFF: 0,
    LogicalColor.RED_LOW: 5,
    LogicalColor.RED_MED: 6,
    LogicalColor.RED_HIGH: 7,
    LogicalColor.GREEN_LOW: 21,
    LogicalColor.GREEN_MED: 22,
    LogicalColor.GREEN_HIGH: 23,
    LogicalColor.AMBER_LOW: 9,
    LogicalColor.AMBER_MED: 10,
    LogicalColor.AMBER_HIGH: 11,
    LogicalColor.YELLOW_LOW: 13,
    LogicalColor.YELLOW_MED: 14,
    LogicalColor.YELLOW_HIGH: 15,
    LogicalColor.ORANGE_LOW: 9,
    LogicalColor.ORANGE_MED: 10,
    LogicalColor.ORANGE_HIGH: 11,
    LogicalColor.WHITE_LOW: 1,
    LogicalColor.WHITE_MED: 2,
    LogicalColor.WHITE_HIGH: 3,
    LogicalColor.BLUE_LOW: 41,
    LogicalColor.BLUE_MED: 42,
    LogicalColor.BLUE_HIGH: 43,
    LogicalColor.PURPLE_LOW: 49,
    LogicalColor.PURPLE_MED: 50,
    LogicalColor.PURPLE_HIGH: 51,
    LogicalColor.CYAN_LOW: 33,
    LogicalColor.CYAN_MED: 34,
    LogicalColor.CYAN_HIGH: 35,
}

LK_EXTENDED_PAD_NOTES = [
    112, 113, 114, 115, 116, 117, 118, 119,
     96,  97,  98,  99, 100, 101, 102, 103,
]

LK_BASIC_PAD_NOTES = [
    36, 37, 38, 39, 40, 41, 42, 43,
    44, 45, 46, 47, 48, 49, 50, 51,
]


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
        self._extended = False
        self._pad_notes = LK_BASIC_PAD_NOTES

    def parse_midi(self, message: list[int]) -> Optional[tuple[EventType, dict]]:
        if not message or len(message) < 3:
            return None

        status = message[0] & 0xF0
        note = message[1]
        value = message[2]

        if status == 0x90:
            try:
                pad_idx = self._pad_notes.index(note)
                x = pad_idx % 8
                y = pad_idx // 8
                event_type = EventType.GRID_PRESS if value > 0 else EventType.GRID_RELEASE
                return (event_type, {"x": x, "y": y, "velocity": value})
            except ValueError:
                pass

        if status == 0xB0:
            if 21 <= note <= 28:
                return (EventType.KNOB, {"control_id": note - 21, "value": value})
            if 41 <= note <= 48:
                return (EventType.FADER, {"control_id": note - 41, "value": value})
            if note == 7:
                return (EventType.FADER, {"control_id": 8, "value": value, "label": "master"})
            if note == 51:
                return (EventType.FUNCTION_PRESS if value > 0 else EventType.FUNCTION_RELEASE,
                        {"control_id": note, "value": value, "label": "mute_solo"})
            if note in (112, 113, 114, 115, 116, 117):
                transport_map = {112: 0, 113: 1, 114: 2, 115: 3, 116: 4, 117: 5}
                return (EventType.TRANSPORT, {
                    "control_id": transport_map[note],
                    "value": value,
                })
            if note in (102, 103):
                return (EventType.TRANSPORT, {
                    "control_id": 6 if note == 103 else 7,
                    "value": value,
                })

        return None

    def send_led(self, x: int, y: int, color: LogicalColor):
        if not (0 <= x < 8 and 0 <= y < 2):
            return

        palette_color = LK_COLOR_PALETTE.get(color, 0)
        note = self._pad_notes[y * 8 + x]
        self.midi_manager.send_message(
            self.device_name,
            [0x9F, note, palette_color],
            target="incontrol",
        )

    def send_led_flash(self, x: int, y: int, color: LogicalColor):
        if not (0 <= x < 8 and 0 <= y < 2):
            return
        palette_color = LK_COLOR_PALETTE.get(color, 0)
        note = self._pad_notes[y * 8 + x]
        self.midi_manager.send_message(
            self.device_name,
            [0x91, note, palette_color],
            target="incontrol",
        )

    def send_led_pulse(self, x: int, y: int, color: LogicalColor):
        if not (0 <= x < 8 and 0 <= y < 2):
            return
        palette_color = LK_COLOR_PALETTE.get(color, 0)
        note = self._pad_notes[y * 8 + x]
        self.midi_manager.send_message(
            self.device_name,
            [0x92, note, palette_color],
            target="incontrol",
        )

    def on_connect(self):
        self.enter_extended_mode()
        self.clear_grid()
        logger.info(f"{self.capabilities.name}: connected, Extended mode activated")

    def on_disconnect(self):
        self._extended = False
        logger.info(f"{self.capabilities.name}: disconnected")

    def enter_extended_mode(self):
        self.midi_manager.send_message(
            self.device_name,
            [0x9F, 0x0C, 0x7F],
            target="incontrol",
        )
        self._extended = True
        self._pad_notes = LK_EXTENDED_PAD_NOTES

    def exit_extended_mode(self):
        self.midi_manager.send_message(
            self.device_name,
            [0x9F, 0x0C, 0x00],
            target="incontrol",
        )
        self._extended = False
        self._pad_notes = LK_BASIC_PAD_NOTES

    def enter_incontrol_pads(self):
        self.midi_manager.send_message(
            self.device_name,
            [0x9F, 0x0F, 0x7F],
            target="incontrol",
        )

    def enter_incontrol_pots(self):
        self.midi_manager.send_message(
            self.device_name,
            [0x9F, 0x0D, 0x7F],
            target="incontrol",
        )

    def enter_incontrol_sliders(self):
        self.midi_manager.send_message(
            self.device_name,
            [0x9F, 0x0E, 0x7F],
            target="incontrol",
        )

    def reset_leds(self):
        self.midi_manager.send_message(
            self.device_name,
            [0xBF, 0x00, 0x00],
            target="incontrol",
        )

    def clear_grid(self):
        self.reset_leds()
        for y in range(self.capabilities.grid_height):
            for x in range(self.capabilities.grid_width):
                self._grid_state[y][x] = LogicalColor.OFF
