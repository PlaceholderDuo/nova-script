"""
MIDI routing tests — Akai Force output + sequencer note-off discipline.

Guards the fix that all note output routes to the Akai Force device via
send_force() (previously notes went to the Launchpad's own port and never
reached any sound module), and that the sequencer emits note-offs.
"""
import types

from src.layout.grid import LogicalGrid
from src.ui.modes.sequencer import SequencerMode


class FakeForce:
    def __init__(self):
        self.sent = []

    def send_force(self, msg):
        self.sent.append(list(msg))


class MockLp:
    device_name = "Launchpad Mini"


class RecordingManager:
    """Stand-in for MidiManager: captures send_message/send_force/register calls."""

    def __init__(self):
        self.sent = []
        self.registered = []
        self.force_device = None
        self.devices = {}

    def send_message(self, device_name, message, target="main"):
        self.sent.append((device_name, list(message), target))

    def send_force(self, message):
        if self.force_device and self.force_device in self.devices:
            self.send_message(self.force_device, message, target="main")

    def register_force_output(self, port_pattern):
        if not port_pattern:
            return
        self.force_device = port_pattern
        self.register_device(port_pattern, input_callback=lambda msg: None)

    def register_device(self, name, input_callback):
        self.registered.append(name)
        self.devices[name] = object()


def test_manager_force_routing():
    print("=== Force routing via MidiManager.send_force ===")
    from src.midi.manager import MidiManager
    m = MidiManager.__new__(MidiManager)
    m.force_device = "Akai Force"
    m.devices = {"Akai Force": object()}
    calls = []

    def fake_send(device_name, message, target="main"):
        calls.append((device_name, list(message), target))

    m.send_message = fake_send

    m.send_force([0x90, 60, 100])
    m.send_force([0x80, 60, 0])

    assert calls == [
        ("Akai Force", [0x90, 60, 100], "main"),
        ("Akai Force", [0x80, 60, 0], "main"),
    ]
    print(f"  OK send_force routes to Akai Force device: {calls}")


def test_manager_force_registration():
    print("=== register_force_output ===")
    from src.midi.manager import MidiManager
    m = MidiManager.__new__(MidiManager)
    m.force_device = None
    m.devices = {}
    registered = []
    m.register_device = lambda name, input_callback: registered.append(name)

    m.register_force_output("Akai Force")

    assert m.force_device == "Akai Force"
    assert "Akai Force" in registered
    print(f"  OK force_device={m.force_device}, registered={registered}")


def test_register_force_output_blank_is_noop():
    print("=== blank force output is a no-op ===")
    from src.midi.manager import MidiManager
    m = MidiManager.__new__(MidiManager)
    m.force_device = None
    m.devices = {}
    calls = []
    m.register_device = lambda name, input_callback: calls.append(name)
    m.register_force_output("")
    m.register_force_output(None)
    assert calls == []
    assert m.force_device is None
    print(f"  OK no-op: {calls}")


def test_sequencer_notes_and_offs_to_force():
    print("=== Sequencer note-on + note-off to Force ===")
    grid = LogicalGrid(8, 8)
    force = FakeForce()
    seq = SequencerMode(grid, MockLp(), midi_manager=force)
    seq._resolution = 16
    seq._update_tick_interval()

    seq._steps[0][1] = True

    seq._send_step_offs(0)
    seq._send_step_notes(1)
    seq._send_step_offs(1)

    ons = [m for m in force.sent if m[0] == 0x90]
    offs = [m for m in force.sent if m[0] == 0x80]
    print(f"  notes={ons} offs={offs}")
    assert ons and ons[0][1] == seq._note_base + (seq._num_rows - 1), "note-on for row 0 expected"
    assert ons[0][2] == 100, "note-on velocity 100 expected"
    assert offs, "note-off expected"
    print("  OK notes + note-offs routed via send_force")


def test_sequencer_off_on_same_note_as_on():
    print("=== Sequencer note-off matches note-on pitch ===")
    grid = LogicalGrid(8, 8)
    force = FakeForce()
    seq = SequencerMode(grid, MockLp(), midi_manager=force)
    seq._resolution = 16
    seq._update_tick_interval()

    seq._steps[0][1] = True
    seq._steps[3][1] = True

    seq._send_step_offs(0)
    seq._send_step_notes(1)
    seq._send_step_offs(1)

    ons = [m for m in force.sent if m[0] == 0x90]
    offs = [m for m in force.sent if m[0] == 0x80]
    assert ons, "expected note-ons"
    assert offs, "expected note-offs"

    expected_ons = {
        seq._note_base + (seq._num_rows - 1),
        seq._note_base + (seq._num_rows - 1 - 3),
    }
    assert {m[1] for m in ons} == expected_ons
    assert {m[1] for m in offs} == expected_ons
    print(f"  OK pitches match between on/off: {expected_ons}")


def test_alesis_v25_forwarding():
    print("=== Alesis V25 MIDI thru forwarding ===")
    from src.controllers.alesis_v25 import AlesisV25

    class FakeMgr:
        def __init__(self):
            self.sent = []
            self.regs = []
            self.cb = None

        def register_input(self, name, cb, pattern=None):
            self.regs.append(("in", name, pattern))
            self.cb = cb

        def register_output(self, name):
            self.regs.append(("out", name))

        def send_message(self, tgt, msg):
            self.sent.append((tgt, msg))

    m = FakeMgr()
    v = AlesisV25(m, "M-Track Plus", cc_remap={1: 16})

    assert ("in", "Alesis V25", "V25") in m.regs
    assert ("out", "M-Track Plus") in m.regs

    m.cb([0x90, 60, 100])       # key note ch1
    assert m.sent[-1] == ("M-Track Plus", [0x90, 60, 100])
    m.cb([0xB2, 20, 59])        # knob ch3 CC20
    assert m.sent[-1] == ("M-Track Plus", [0xB2, 20, 59])
    m.cb([0xB0, 1, 64])         # mod wheel CC1 -> CC16
    assert m.sent[-1] == ("M-Track Plus", [0xB0, 16, 64])
    m.cb([0xE0, 0, 64])         # pitch bend
    assert m.sent[-1] == ("M-Track Plus", [0xE0, 0, 64])
    print("  OK keys/knobs/mod-wheel/pitch-bend forward; mod wheel remapped")


def test_alesis_v25_velocity_default_is_identity():
    print("=== V25 default velocity = linear passthrough ===")
    from src.controllers.alesis_v25 import AlesisV25

    class FakeMgr:
        def __init__(self):
            self.sent = []
            self.regs = []
            self.cb = None

        def register_input(self, name, cb, pattern=None):
            self.regs.append(("in", name, pattern))
            self.cb = cb

        def register_output(self, name):
            self.regs.append(("out", name))

        def send_message(self, tgt, msg):
            self.sent.append((tgt, msg))

    m = FakeMgr()
    v = AlesisV25(m, "M-Track Plus", cc_remap={1: 16})
    m.cb([0x90, 60, 70])
    assert m.sent[-1] == ("M-Track Plus", [0x90, 60, 70])
    print("  OK velocities pass through untouched by default")


def test_alesis_v25_velocity_piano_curve():
    print("=== V25 piano curve boosts soft/medium hits, preserves hard ===")
    from src.controllers.alesis_v25 import AlesisV25

    class FakeMgr:
        def __init__(self):
            self.sent = []
            self.regs = []
            self.cb = None

        def register_input(self, name, cb, pattern=None):
            self.regs.append(("in", name, pattern))
            self.cb = cb

        def register_output(self, name):
            self.regs.append(("out", name))

        def send_message(self, tgt, msg):
            self.sent.append((tgt, list(msg)))

    m = FakeMgr()
    v = AlesisV25(m, "M-Track Plus",
                  cc_remap={1: 16},
                  velocity={"curve": "piano", "power": 2.0, "boost": 1.0, "floor": 8})

    m.cb([0x90, 60, 40])        # soft hit -> boosted well above 40
    assert m.sent[-1][1][2] == 71, f"got {m.sent[-1][1][2]}, expected 71"
    m.cb([0x90, 62, 127])       # full force stays maxed
    assert m.sent[-1][1][2] == 127
    m.cb([0x90, 60, 0])         # running-status note-off (vel 0) stays 0
    assert m.sent[-1][1][2] == 0
    m.cb([0xB0, 1, 64])         # CCs (mod wheel) untouched by velocity curve
    assert m.sent[-1][1] == [0xB0, 16, 64]
    print("  OK soft boosted (40->71), 127 intact, note-off 0, CCs untouched")


def test_alesis_v25_velocity_linear_boost_clamp():
    print("=== V25 linear curve with flat gain clamps at 127 ===")
    from src.controllers.alesis_v25 import AlesisV25

    class FakeMgr:
        def __init__(self):
            self.sent = []
            self.regs = []
            self.cb = None

        def register_input(self, name, cb, pattern=None):
            self.regs.append(("in", name, pattern))
            self.cb = cb

        def register_output(self, name):
            self.regs.append(("out", name))

        def send_message(self, tgt, msg):
            self.sent.append((tgt, list(msg)))

    m = FakeMgr()
    v = AlesisV25(m, "M-Track Plus", velocity={"curve": "linear", "boost": 1.3})

    m.cb([0x90, 60, 100])
    assert m.sent[-1][1][2] == 127, "100*1.3 must clamp to 127"
    m.cb([0x90, 60, 40])
    assert m.sent[-1][1][2] == 52, "round(40*1.3)=52 expected"
    print("  OK linear boost: 100->127, 40->52")


def test_input_output_only_registration():
    print("=== input-only / output-only device registration ===")
    from src.midi.manager import MidiManager
    m = MidiManager.__new__(MidiManager)
    m.devices = {}
    m._input_callbacks = {}
    m._device_configs = {}

    m.register_input("Alesis V25", lambda msg: None, pattern="V25")
    assert m._device_configs["Alesis V25"]["input_only"] is True
    assert m._device_configs["Alesis V25"]["input_pattern"] == "V25"

    m.register_output("M-Track Plus")
    assert m._device_configs["M-Track Plus"]["output_only"] is True
    print("  OK input_only/output_only flags set correctly")


if __name__ == "__main__":
    test_manager_force_routing()
    test_manager_force_registration()
    test_register_force_output_blank_is_noop()
    test_sequencer_notes_and_offs_to_force()
    test_sequencer_off_on_same_note_as_on()
    test_alesis_v25_forwarding()
    test_alesis_v25_velocity_default_is_identity()
    test_alesis_v25_velocity_piano_curve()
    test_alesis_v25_velocity_linear_boost_clamp()
    test_input_output_only_registration()
    print("\nOK ALL MIDI ROUTING TESTS PASSED")