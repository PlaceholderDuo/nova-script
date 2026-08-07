"""
BPM clock feed tests — verifies that OSC /beat and MIDI clock (0xF8) reach
the BPMClock and drive beat firing. Guards the fix that neither source was
ever routed into the clock, so no beat ever fired.
"""
import time

from src.midi.clock import BPMClock


def test_osc_beat_fires_on_beat():
    print("=== OSC beat feeds clock and fires on_beat ===")
    clock = BPMClock(default_bpm=120.0, preferred="Reaper (OSC)", fallback="Internal")
    beats = []
    clock.set_on_beat(lambda n: beats.append(n))

    clock.feed_osc_beat(0.0)
    time.sleep(0.2)
    clock.feed_osc_beat(0.5)

    assert clock.source == clock.SOURCE_OSC
    assert len(beats) == 2, "each OSC beat should fire on_beat"
    print(f"  OK source=OSC, on_beat fired {len(beats)} times")


def test_midi_clock_fires_on_beat():
    clock = BPMClock(default_bpm=120.0, preferred="Reaper (OSC)", fallback="Internal")
    beats = []
    clock.set_on_beat(lambda n: beats.append(n))

    # 24 clock pulses = one quarter note
    for _ in range(24):
        clock.feed_midi_clock()
    import types
    # feed_midi_clock fires once every 24 pulses.
    assert len(beats) == 1, f"expected 1 beat after 24 pulses, got {len(beats)}"
    print(f"  OK MIDI clock fires on_beat after 24 pulses ({len(beats)} beat)")


def test_engine_wires_osc_beat_feed():
    print("=== engine._on_osc_message wires feed_osc_beat ===")
    import re
    src = open("src/engine.py").read()
    handler = src.split("elif msg_type == \"beat\":")[1].split("elif msg_type == \"track_vu\"")[0]
    assert "feed_osc_beat" in handler, "beat OSC handler must feed the clock"
    print(f"  OK beat handler calls feed_osc_beat")


def test_engine_wires_midi_clock_feed():
    print("=== engine._event_loop wires feed_midi_clock ===")
    src = open("src/engine.py").read()
    assert "0xF8" in src and "feed_midi_clock" in src
    event_block = src[src.index("_event_loop"):]
    assert "feed_midi_clock" in event_block
    print("  OK event loop feeds MIDI clock on 0xF8")


if __name__ == "__main__":
    test_osc_beat_fires_on_beat()
    test_midi_clock_fires_on_beat()
    test_engine_wires_osc_beat_feed()
    test_engine_wires_midi_clock_feed()
    print("\nOK ALL BPM CLOCK FEED TESTS PASSED")