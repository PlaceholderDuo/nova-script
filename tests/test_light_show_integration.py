"""Full-chain manual lighting integration test.

Virtual Launchpad (no hardware) -> Engine/LightShowMode -> temp feed file
-> lighting-system ShowDriver -> recorded scenes.

Verifies the manual cue chain AND the manual-release-restores-automatic
behavior end to end, using the same event contract the live stack uses.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, ".")

import src.engine as engine_mod  # noqa: E402
from src.controllers.base import LogicalColor  # noqa: E402

# Patch BEFORE Engine is instantiated (mirrors test_engine_integration).
from tests.test_engine_integration import EngineHarness  # noqa: E402

# Lighting engine under test (stdlib-only; outputs imported lazily).
LIGHTING_ENGINE = Path.home() / "Documents/projects/lighting-system" / "engine"
if str(LIGHTING_ENGINE) not in sys.path:
    sys.path.insert(0, str(LIGHTING_ENGINE))

from lighting_engine.driver import ShowDriver  # noqa: E402


def _read_feed(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(l) for l in f.read().splitlines() if l.strip()]


class RecordingOutput:
    def __init__(self):
        self.scenes = []

    def apply(self, scene, state=None):
        self.scenes.append(scene)

    def close(self):
        pass


def _make_driver():
    out = RecordingOutput()
    d = ShowDriver(outputs=[out], seed=7, async_render=False)
    return d, out


def test_light_show_manual_chain_virtual_to_driver():
    fd, feed_path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    direct = [
        {"name": "Base", "look": "Standard Performance", "cue": "snap", "fade_ms": 800},
        {"name": "Blinder", "look": "Crowd Blinder", "cue": "pulse",
         "fade_ms": 100, "pulse_beats": 1},
    ]
    moods = [{
        "name": "Standard",
        "peak": {"look": "High Energy", "fade_ms": 120},
        "scenes": [{"name": "Wash", "look": "Warm Ambient",
                    "cue": "snap", "fade_ms": 800}],
    }]
    cfg = {
        "ui": {"default_mode": "light_show"},
        "modes": {"light_show": {
            "feed": feed_path, "direct_cues": direct, "moods": moods,
        }},
    }
    h = EngineHarness(cfg)
    assert h.mode == "light_show"

    # Direct busking bank renders on row 0 (snap = amber).
    assert h.led(0, 0) == LogicalColor.AMBER_MED

    # Tap Base (0,0) -> FORCE_LOOK written to the feed.
    h.tap(0, 0)
    events = _read_feed(feed_path)
    assert events[-1]["event"] == "FORCE_LOOK"
    assert events[-1]["look"] == "Standard Performance"

    # Tap Blinder (1,0) -> pulse pending, fires on the next beat.
    h.tap(1, 0)
    mode = h.engine.mode_manager._modes["light_show"]
    mode.on_beat(1)
    events = _read_feed(feed_path)
    assert events[-1].get("pulse") is True
    assert events[-1]["look"] == "Crowd Blinder"

    # Now run the same FORCE_LOOKs against the real lighting driver.
    d, out = _make_driver()
    d.on_song_start("s", genre="rock", bpm=120, energy=0.5)
    d.on_section_change("verse", energy=0.4)
    d.on_beat(1, 1)
    auto_before = out.scenes[-1].look
    d.on_force_look("Standard Performance")
    d.on_beat(1, 2)
    assert out.scenes[-1].look == "Standard Performance"
    d.on_force_look("Crowd Blinder")
    d.on_beat(1, 3)
    assert out.scenes[-1].look == "Crowd Blinder"

    # Leaving the Launchpad light show page releases to auto.
    h.engine.mode_manager.switch_to("performance")
    events = _read_feed(feed_path)
    assert events[-1]["event"] == "FORCE_LOOK"
    assert events[-1]["look"] is None
    d.on_force_look(None)
    d.on_beat(1, 4)
    assert out.scenes[-1].look != "Crowd Blinder"
    assert out.scenes[-1].look != "Blackout"
    assert out.scenes[-1].look == auto_before

    d.close()
    os.remove(feed_path)