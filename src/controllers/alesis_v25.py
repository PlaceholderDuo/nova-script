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

Velocity shaping: the V25 keybed responds softly — a normal press lands far
quieter than the Force's own pads, forcing hard slams for full volume.  An
optional velocity curve (default "linear" = passthrough) boosts soft/medium
hits so the keyboard plays like a real piano.  See `apply_velocity`.
"""
import logging

from src.midi.routing import CC, NOTE_ON, NOTE_OFF

logger = logging.getLogger(__name__)


def apply_velocity(in_vel: int, curve: str = "linear", power: float = 2.0,
                   boost: float = 1.0, floor: int = 1) -> int:
    """Map a note-on velocity (1-127) through the configured curve.

    - "linear": flat gain — out = in * boost (boost=1.0 is identity).
    - "piano": power curve — out = 127 * (in/127)^(1/power) * boost. Boosts
      soft/medium hits so a normal press lands near full strength while hard
      hits still reach 127 (power 2.0 = square-root curve).

    `floor` keeps very soft hits audible. Velocity 0 (running-status note-off)
    is never raised, so notes always release cleanly.
    """
    if in_vel <= 0:
        return 0
    if curve == "piano":
        norm = in_vel / 127.0
        out = 127.0 * (norm ** (1.0 / max(power, 0.1))) * boost
    else:
        out = in_vel * boost
    return max(floor, min(127, round(out)))


class AlesisV25:
    """Register the V25 as a first-class input device and forward its MIDI.

    Args:
        midi_manager: the MidiManager used for register_input + send_message.
        target_port: output port name to forward everything to.
        input_pattern: substring to match the V25 input port (default "V25").
        cc_remap: dict mapping source CC -> target CC (applied on forward).
        velocity: dict with curve/boost/power/floor shaping for note velocities
            (see `apply_velocity`). Empty or None = linear passthrough.
    """

    DEVICE_NAME = "Alesis V25"

    HARDWARE_DESC = (
        "25 keys, 4 knobs (CC20-23), mod wheel (CC1), pitch wheel, "
        "4 buttons, 8 drum pads"
    )

    def __init__(self, midi_manager, target_port: str,
                 input_pattern: str = "V25", cc_remap: dict[int, int] | None = None,
                 velocity: dict | None = None):
        self.midi_manager = midi_manager
        self.target_port = target_port
        self.cc_remap: dict[int, int] = cc_remap or {}
        v = velocity or {}
        self._curve = v.get("curve", "linear")
        self._power = float(v.get("power", 2.0))
        self._boost = float(v.get("boost", 1.0))
        self._floor = int(v.get("floor", 1))
        midi_manager.register_input(self.DEVICE_NAME, self.handle_raw_midi, pattern=input_pattern)
        midi_manager.register_output(target_port)
        logger.info(
            f"Alesis V25 registered ({self.HARDWARE_DESC}) → MIDI thru to {target_port} "
            f"[velocity curve={self._curve}]"
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
        # Velocity shaping on note-ons only (velocity 0 = running-status note-off).
        if typ == NOTE_ON and len(msg) >= 3 and msg[2] > 0:
            msg[2] = apply_velocity(msg[2], self._curve, self._power, self._boost, self._floor)
        logger.debug(
            f"V25 → {self.target_port}: "
            f"0x{status:02X} " + " ".join(f"{b:02X}" for b in msg[1:])
        )
        logger.info(f"[V25 THRU] 0x{status:02X} " + " ".join(f"{b:02X}" for b in msg[1:]))
        self.midi_manager.send_message(self.target_port, msg)
