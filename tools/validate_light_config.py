#!/usr/bin/env python3
"""Validate the Light Show mode config against the lighting engine's looks.json.

Cross-checks every mood scene's `look` reference in
config/profiles/live-show.yaml against the real look names the lighting engine
can render (lighting-system/engine/looks/looks.json). Any unknown look would be
silently swallowed at show time (engine falls back to auto), so this catches it
before a gig.

Exit codes:
    0  all look references resolve
    1  at least one reference is missing
    2  config or looks file could not be loaded
"""
import json
import sys
from pathlib import Path

import yaml

NOVA_ROOT = Path(__file__).resolve().parents[1]
LIGHTING_LOOKS = Path.home() / "Documents/projects/lighting-system/engine/looks/looks.json"


def load_looks() -> set[str]:
    if not LIGHTING_LOOKS.exists():
        raise FileNotFoundError(f"looks.json not found at {LIGHTING_LOOKS}")
    data = json.loads(LIGHTING_LOOKS.read_text())
    return {look["name"] for look in data["looks"]}


def main() -> int:
    profile_path = NOVA_ROOT / "config" / "profiles" / "live-show.yaml"
    try:
        profile = yaml.safe_load(profile_path.read_text())
        moods = profile["modes"]["light_show"]["moods"]
        names = load_looks()
    except (FileNotFoundError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERROR loading config/looks: {exc}", file=sys.stderr)
        return 2

    missing = []
    total_scenes = 0
    for mood in moods:
        for scene in mood.get("scenes", []):
            total_scenes += 1
            ref = scene.get("look")
            if ref and ref not in names:
                missing.append((mood.get("name"), scene.get("name"), ref))

    if missing:
        for mood_name, scene_name, ref in missing:
            print(f"MISSING look {ref!r} (mood {mood_name!r}, scene {scene_name!r})")
        return 1

    print(
        f"OK: {len(moods)} moods, {total_scenes} scenes, "
        f"all look refs resolve against {len(names)} looks"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
