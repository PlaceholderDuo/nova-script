"""
Alesis V25 — 25-key USB MIDI keyboard controller.

NOT a Novation device — this is a class-compliant USB keyboard with:
  - 25 velocity-sensitive keys (MIDI channel 1)
  - 4 assignable knobs      (MIDI channel 3, CC 20-23)
  - Mod wheel               (CC 1)
  - Pitch bend wheel
  - 4 buttons               (CC, channel 3)
  - 8 drum/trigger pads     (notes)

In the live rig this device is used purely as a MIDI *source*: its messages
are forwarded (MIDI thru) out through an audio interface's physical MIDI OUT
jack and into the Akai Force via a MIDI cable.  Optional CC remapping lets us
turn e.g. the mod wheel (CC 1) into a plain learnable controller (CC 16) so
the Force's MIDI-learn can assign it to something like tremolo rate.
"""
import logging

from src.midi.routing import CC, NOTE_ON, NOTE_OFF

logger = logging.getLogger(__name__)


class AlesisV25:
    """Register the V25 as a first-class input device and forward its MIDI.

    Args:
        midi_manager: the MidiManager used for register_input + send_message.
        target_port: output port name to forward everything to.
        input_pattern: substring to match the V25 input port (default "V25").
        cc_remap: dict mapping source CC -> target CC (applied on forward).
    """

    DEVICE_NAME = "Alesis V25"

    HARDWARE_DESC = (
        "25 keys, 4 knobs (CC20-23), mod wheel (CC1), pitch wheel, "
        "4 buttons, 8 drum pads"
    )

    def __init__(self, midi_manager, target_port: str,
                 input_pattern: str = "V25", cc_remap: dict[int, int] | None = None):
        self.midi_manager = midi_manager
        self.target_port = target_port
        self.cc_remap: dict[int, int] = cc_remap or {}
        midi_manager.register_input(self.DEVICE_NAME, self.handle_raw_midi, pattern=input_pattern)
        midi_manager.register_output(target_port)
        logger.info(
            f"Alesis V25 registered ({self.HARDWARE_DESC}) → MIDI thru to {target_port}"
        )

    def handle_raw_midi(self, message: list[int]):
        if not message:
            return
        msg = list(message)
        status = msg[0]
        typ = status & 0xF0
        # Remap CC controller numbers (e.g. mod wheel CC 1 -> CC 16)
        if typ == CC and len(msg) >= 2 and msg[1] in self.cc_remap:
            msg = [msg[0], self.cc_remap[msg[1]]] + list(msg[2:])
        logger.debug(
            f"V25 → {self.target_port}: "
            f"0x{status:02X} " + " ".join(f"{b:02X}" for b in msg[1:])
        )
        logger.info(f"[V25 THRU] 0x{status:02X} " + " ".join(f"{b:02X}" for b in msg[1:]))
        self.midi_manager.send_message(self.target_port, msg)
