"""
Light Show mode v2 tests — mood-row layout, scene cueing (snap/pulse),
momentary peak hold, and feed emission for the Launchpad lighting controller.
"""
import json
import os
import tempfile

from src.ui.modes.light_show import LightShowMode, MOOD_ROWS, MOOD_COLORS
from src.controllers.base import GridEvent, ControlEvent, EventType, LogicalColor


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


class _Overlay:
    def __init__(self):
        self.texts = []

    def trigger_hud(self, text=""):
        self.texts.append(text)


def _make_mode(n_moods=3, scenes_per_mood=8, overlay=True):
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    moods = []
    for i in range(n_moods):
        moods.append({
            "name": f"Mood{i}",
            "peak": {"look": f"Peak{i}", "fade_ms": 120},
            "scenes": [
                {"name": f"S{j}", "look": f"Look{j}", "cue": "snap", "fade_ms": 800}
                for j in range(scenes_per_mood)
            ],
        })
    moods[0]["scenes"][-1] = {"name": "Flash", "look": "LookFlash",
                              "cue": "pulse", "fade_ms": 150, "pulse_beats": 2}
    m = LightShowMode(_Grid(), _Controller(),
                      config={"moods": moods}, feed_path=path)
    return m, path


def _read_feed(path):
    with open(path) as f:
        return [json.loads(l) for l in f.read().splitlines() if l.strip()]


def _press(control_id):
    return ControlEvent(control_id, 127, EventType.FUNCTION_PRESS)


def _release(control_id):
    return ControlEvent(control_id, 0, EventType.FUNCTION_RELEASE)


def test_moods_load():
    m, _ = _make_mode()
    m.enter()
    assert len(m.moods) == 3
    assert m.moods[0]["peak"]["look"] == "Peak0"
    print("  OK moods + peaks loaded")


def test_snap_cue_writes_look():
    m, path = _make_mode()
    m.enter()
    m._cue(0, m.moods[0]["scenes"][0])
    ev = _read_feed(path)[-1]
    assert ev["event"] == "FORCE_LOOK"
    assert ev["look"] == "Look0"
    assert m._current_scene == "S0"
    print("  OK snap cue emits FORCE_LOOK + tracks current scene")


def test_grid_event_routes_to_mood_row():
    m, path = _make_mode()
    m.enter()
    # mood 0 = row 7; press scene index 3 (col x=3)
    m.handle_grid_event(GridEvent(3, MOOD_ROWS[0], True, EventType.GRID_PRESS))
    ev = _read_feed(path)[-1]
    assert ev["look"] == "Look3"
    print("  OK grid press on mood row cues the right scene")


def test_pulse_fires_on_beat_and_returns():
    m, path = _make_mode()
    m.enter()
    m._cue(0, m.moods[0]["scenes"][0])     # snap S0
    m._cue(0, m.moods[0]["scenes"][-1])    # pulse Flash (pulse_beats=2)
    assert m._pending_pulse is not None
    m.on_beat(1)                            # fires the pulse
    ev = _read_feed(path)[-1]
    assert ev.get("pulse") is True
    assert ev["scene"] == "Flash"
    m.on_beat(2)                            # countdown 2 -> 1
    m.on_beat(3)                            # countdown 1 -> 0 -> return to S0
    ev = _read_feed(path)[-1]
    assert ev["scene"] == "S0"
    print("  OK pulse fires on beat, returns after pulse_beats")


def test_pulse_with_no_prior_returns_to_auto():
    m, path = _make_mode()
    m.enter()
    m._cue(0, m.moods[0]["scenes"][-1])     # pulse with no prior snap
    m.on_beat(1)
    m.on_beat(2)
    m.on_beat(3)
    assert _read_feed(path)[-1]["look"] is None
    print("  OK pulse with no prior scene releases to auto")


def test_peak_hold_fires_and_release_returns():
    m, path = _make_mode()
    m.enter()
    m._cue(0, m.moods[0]["scenes"][0])      # snap S0
    m._start_peak(1)                        # hold mood 1 peak
    assert m._held_mood == 1
    ev = _read_feed(path)[-1]
    assert ev["look"] == "Peak1"
    m.on_beat(1)                            # blink toggles
    assert m._blink_on is False             # toggled from True -> False
    m._end_peak(1)                          # release -> return to S0
    assert m._held_mood is None
    assert _read_feed(path)[-1]["scene"] == "S0"
    print("  OK peak hold fires peak, blinks, release returns to prior scene")


def test_peak_release_with_no_prior_returns_to_auto():
    m, path = _make_mode()
    m.enter()
    m._start_peak(0)
    m._end_peak(0)
    assert _read_feed(path)[-1]["look"] is None
    print("  OK peak with no prior scene returns to auto")


def test_render_colors_scene_pads_and_moods():
    m, _ = _make_mode()
    m.enter()
    m._entry_row = len(m.moods)             # skip entry sweep
    m._cue(0, m.moods[0]["scenes"][0])      # make S0 active
    m._clear_hint()                          # help text already asserted elsewhere
    m._render()
    g = m.grid
    # S0 active = green, S1..S6 snap = amber, Flash (last) pulse = red
    assert g.get_cell(0, MOOD_ROWS[0]) == LogicalColor.GREEN_HIGH
    assert g.get_cell(1, MOOD_ROWS[0]) == LogicalColor.AMBER_MED
    assert g.get_cell(7, MOOD_ROWS[0]) == LogicalColor.RED_MED
    # right column: mood 0 lit in its color
    assert m.controller.right[0] == MOOD_COLORS[0]
    print("  OK scene pads + right column render with color/brightness")


def test_help_text_on_scene_and_peak():
    m, _ = _make_mode()
    m.enter()
    m._cue(0, m.moods[0]["scenes"][0])
    assert m._hint_text == "S0"
    m._start_peak(0)
    assert m._hint_text == "MOOD0 PEAK"
    print("  OK help text fires on scene cue + peak hold")


def test_exit_releases_to_auto():
    m, path = _make_mode()
    m.enter()
    m._cue(0, m.moods[0]["scenes"][0])
    m.exit()
    assert _read_feed(path)[-1]["look"] is None
    print("  OK mode exit releases to auto")


if __name__ == "__main__":
    for fn in sorted(globals()):
        if fn.startswith("test_"):
            print(f"\n=== {fn} ===")
            globals()[fn]()
    print("\nALL LIGHT SHOW TESTS PASSED")
