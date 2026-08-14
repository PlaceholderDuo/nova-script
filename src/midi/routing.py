"""
MIDI routing — MIDI thru/passthrough with optional CC remapping.
"""
import logging

logger = logging.getLogger(__name__)

NOTE_ON = 0x90
NOTE_OFF = 0x80
CC = 0xB0


class MidiThru:
    """Routes MIDI from one device to another, with optional CC remapping.

    Args:
        midi_manager: the MidiManager for register_device + send_message.
        source_port: substring matching the input port name.
        target_port: substring matching the output port name.
        channels: optional list of MIDI channels (0-15) to forward. None = all.
        note_only: if True, forward only note-on/note-off. Default False.
        cc_remap: dict mapping source CC number -> target CC number. Forwarded
            CC messages are rewritten to the target controller number. Useful
            for turning e.g. the mod wheel (CC 1) into a plain learnable knob.
    """

    def __init__(self, midi_manager, source_port: str, target_port: str,
                 channels: list[int] | None = None, note_only: bool = False,
                 cc_remap: dict[int, int] | None = None):
        self._mgr = midi_manager
        self._target = target_port
        self._channels: set[int] = set(channels) if channels else set()
        self._note_only = note_only
        self._cc_remap: dict[int, int] = cc_remap or {}
        # Register the target as an output device so send_message can reach it.
        self._mgr.register_output(target_port)
        self._mgr.register_device(source_port, self._on_message)

    def _on_message(self, message: list[int]):
        if not message:
            return
        status = message[0]
        chan = status & 0x0F
        if self._channels and chan not in self._channels:
            return

        typ = status & 0xF0
        if self._note_only:
            if typ not in (NOTE_ON, NOTE_OFF):
                return

        # Remap CC controller numbers (e.g. mod wheel CC 1 -> CC 16)
        if typ == CC and len(message) >= 2 and message[1] in self._cc_remap:
            message = [message[0], self._cc_remap[message[1]]] + list(message[2:])

        self._mgr.send_message(self._target, message)
