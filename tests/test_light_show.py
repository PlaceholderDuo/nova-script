"""
Light Show mode tests — verifies mood selection, scene cueing, pulse
auto-return, and feed emission for the Launchpad lighting controller.
"""
import json
import os
import tempfile

from src.ui.modes.light_show import LightShowMode
from src.controllers.base import GridEvent, ControlEvent, EventType


class _Grid:
    def __init__(self):
        self.cells = {}

    def clear(self):
        self.cells = {}

    def set_cell(self, x, y, c):
        self.cells[(x, y)] = c

    def dirty_cells(self):
        return list(self.cells.items())

    def get_cell(self, x, y):
        return self.cells.get((x, y))


class _Controller:
    def __init__(self):
        self.right = {}

    def set_grid_color(self, x, y, c):
        pass

    def send_right_column_led(self, i, c):
        self.right[i] = c

    def clear_grid(self):
        pass


def _make_mode(scenes_per_mood=8):
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    moods = [{"name": f"Mood{i}", "scenes": [
        {"name": f"S{j}", "look": f"Look{j}", "cue": "snap", "fade_ms": 800}
        for j in range(scenes_per_mood)
    ]} for i in range(3)]
    # Give the last scene of mood 0 a pulse type for pulse tests
    moods[0]["scenes"][-1] = {"name": "Flash", "look": "LookFlash", "cue": "pulse",
                              "fade_ms": 150, "pulse_beats": 2}
    return LightShowMode(_Grid(), _Controller(), config={"moods": moods}, feed_path=path), path


def _read_feed(path):
    with open(path) as f:
        return [json.loads(l) for l in f.read().splitlines() if l.strip()]


def test_moods_load_and_default():
    m, _ = _make_mode()
    m.enter()
    assert len(m.moods) == 3
    assert m._current_mood()["name"] == "Mood0"
    print("  OK 3 moods loaded, default = Mood0")


def test_cue_snap_writes_look():
    m, path = _make_mode()
    m.enter()
    m._cue(0)
    events = _read_feed(path)
    assert events[-1]["event"] == "FORCE_LOOK"
    assert events[-1]["look"] == "Look0"
    assert m._current_scene == "S0"
    print("  OK snap cue emits FORCE_LOOK with correct look")


def test_mood_switch_via_right_column():
    m, _ = _make_mode()
    m.enter()
    m.handle_control_event(ControlEvent(102, 127, EventType.FUNCTION_PRESS))
    assert m._current_mood()["name"] == "Mood2"
    m.handle_control_event(ControlEvent(101, 127, EventType.FUNCTION_PRESS))
    assert m._current_mood()["name"] == "Mood1"
    print("  OK right-column A/B switch moods")


def test_pulse_fires_on_beat_and_returns():
    m, path = _make_mode()
    m.enter()
    m._cue(0)                      # snap to S0
    m.on_beat(1)
    m._cue(7)                      # Flash (pulse, pulse_beats=2)
    assert m._pending_pulse == "Flash"
    assert m._return_to == "S0"
    m.on_beat(2)                   # fires the pulse
    events = _read_feed(path)
    assert events[-1]["pulse"] is True
    assert events[-1]["scene"] == "Flash"
    m.on_beat(3)                   # decrement
    assert m._current_scene == "Flash"
    m.on_beat(4)                   # returns
    events = _read_feed(path)
    assert events[-1]["scene"] == "S0"
    print("  OK pulse fires on beat, returns to prior scene after pulse_beats")


def test_pulse_with_no_prior_returns_to_auto():
    m, path = _make_mode()
    m.enter()
    m._cue(7)                      # Flash with no prior scene
    m.on_beat(1)
    m.on_beat(2)
    m.on_beat(3)
    events = _read_feed(path)
    assert events[-1]["look"] is None
    print("  OK pulse with no prior scene releases to auto")


def test_exit_releases_to_auto():
    m, path = _make_mode()
    m.enter()
    m._cue(0)
    m.exit()
    events = _read_feed(path)
    assert events[-1]["look"] is None
    print("  OK mode exit releases to auto")


if __name__ == "__main__":
    for fn in sorted(globals()):
        if fn.startswith("test_"):
            print(f"\n=== {fn} ===")
            globals()[fn]()
    print("\nALL LIGHT SHOW TESTS PASSED")
