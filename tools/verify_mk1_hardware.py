#!/usr/bin/env python3
"""
verify_mk1_hardware.py — hands-on confirmation that the MK1 constants the
nova-script suite assumes actually match your physical Launchpad Mini MK1.

The browser suite (tools/browser-tests) hardcodes these values from the
virtualizer's "Launchpad Mini MK1" profile, and the engine's controller uses
the same ones. This script lights the real device and listens to real presses
so you can eyeball that everything lines up.

WHAT IT CHECKS (and the expected result on the physical device):

  1. ORIENTATION  — four corners light distinctly. Confirm that:
        bottom-left  (nearest you, left)  = RED
        bottom-right (nearest you, right) = GREEN
        top-left     (near the round buttons) = AMBER
        top-right    = ORANGE
     (App y=0 = bottom = the row nearest the player. Note 0 is the physical
      TOP-left, note 112 the physical BOTTOM-left — the engine's
      `(7 - y) * 16 + x` maps app-bottom to note 112, i.e. the real bottom.)

  2. COLOR MAP  — a colour swatch lights each of RED / GREEN / AMBER at
     LOW / MED / HIGH. Confirm the brightnesses step and the hues look right.
     MK1 encoding is `00gg00rr`:  RED=1/2/3, GREEN=16/32/48, AMBER=17/34/51.

  3. TOP ROW + RIGHT COLUMN — CC 104..111 (0x68..0x6F) and notes
     8,24,40,56,72,88,104,120 light top-to-bottom/left-to-right as labelled.

  4. BUTTON LISTENER — tap pads and round buttons; the decoded app
     coordinate / control id is printed so you can confirm the mapping.

USAGE:
    # stop the engine / test stack first (it holds the MIDI port), then:
    .venv/bin/python tools/verify_mk1_hardware.py
"""

import sys
import time

import rtmidi

SEARCH = "launchpad"          # case-insensitive substring for the device

# The exact constants nova-script assumes (src/controllers/color_map.py +
# launchpad_mk1.py). Verify these against what the hardware does.
MK1_COLORS = {
    "RED_LOW": 1, "RED_MED": 2, "RED_HIGH": 3,
    "GREEN_LOW": 16, "GREEN_MED": 32, "GREEN_HIGH": 48,
    "AMBER_LOW": 17, "AMBER_MED": 34, "AMBER_HIGH": 51,
    "ORANGE_MED": 33, "YELLOW_MED": 50,
}
TOP_ROW_CC = list(range(0x68, 0x70))            # 104..111
RIGHT_COL_NOTES = [8, 24, 40, 56, 72, 88, 104, 120]

GRID_NOTE = lambda x, y: (7 - y) * 16 + x       # app (x,y), y=0 = bottom


def find_device():
    midi = rtmidi.MidiOut()
    outs = midi.get_ports()
    midi_in = rtmidi.MidiIn()
    ins = midi_in.get_ports()
    out_idx = next((i for i, n in enumerate(outs) if SEARCH in n.lower()), None)
    in_idx = next((i for i, n in enumerate(ins) if SEARCH in n.lower()), None)
    if out_idx is None or in_idx is None:
        print(f"MIDI ports found:\n  in : {ins}\n  out: {outs}")
        print("\nNo Launchpad found. Is it plugged in — and is the engine or "
              "test stack STOPPED? (they hold the port)")
        return None, None
    return midi, midi_in


def send(out, msg):
    out.send_message(msg)
    time.sleep(0.012)           # let the MK1 keep up with bursts


def light(out, x, y, color):
    send(out, [0x90, GRID_NOTE(x, y), color])


def reset(out):
    send(out, [0xB0, 0x00, 0x00])
    time.sleep(0.3)


def phase_orientation(out):
    print("\n=== 1) ORIENTATION ===")
    print("Four corners should light. Confirm:")
    print("   bottom-left  (nearest you, left)  = RED")
    print("   bottom-right (nearest you, right) = GREEN")
    print("   top-left     (near round buttons) = AMBER")
    print("   top-right                         = ORANGE")
    reset(out)
    light(out, 0, 0, MK1_COLORS["RED_HIGH"])
    light(out, 7, 0, MK1_COLORS["GREEN_HIGH"])
    light(out, 0, 7, MK1_COLORS["AMBER_HIGH"])
    light(out, 7, 7, MK1_COLORS["ORANGE_MED"])
    time.sleep(6)
    reset(out)


def phase_colors(out):
    print("\n=== 2) COLOR MAP ===")
    print("Nine swatches light across the grid (RED, GREEN, AMBER at")
    print("LOW / MED / HIGH). Confirm hues + brightness steps look right.")
    reset(out)
    order = ["RED", "GREEN", "AMBER"]
    for row, base in enumerate(order):
        for step, suffix in enumerate(["LOW", "MED", "HIGH"]):
            color = f"{base}_{suffix}"
            for x in range(8):
                light(out, x, row, MK1_COLORS[color])
    # Top row + right column in amber-high so you can see those regions too.
    for i, cc in enumerate(TOP_ROW_CC):
        send(out, [0xB0, cc, MK1_COLORS["AMBER_HIGH"]])
    for i, note in enumerate(RIGHT_COL_NOTES):
        send(out, [0x90, note, MK1_COLORS["AMBER_HIGH"]])
    time.sleep(6)
    reset(out)


def phase_buttons(out, midi_in):
    print("\n=== 3) BUTTON LISTENER ===")
    print("Tap pads and round buttons for ~15s. Each press prints the raw")
    print("note/CC and how nova-script decodes it. Confirm e.g. the physical")
    print("bottom-left pad prints note 112 -> (0,0).")
    print("(right-column notes 8..120 -> control 100..107;")
    print(" top-row CC 104..111 -> control 200..207)")
    midi_in.ignore_types(sysex=False, timing=False, active_sense=False)
    deadline = time.monotonic() + 15
    seen = set()
    while time.monotonic() < deadline:
        msg = midi_in.get_message()
        if not msg:
            time.sleep(0.01)
            continue
        data = msg[0]
        if len(data) < 2:
            continue
        status, d1, d2 = data[0] & 0xF0, data[1], data[2] if len(data) > 2 else 0
        if d2 == 0:                               # release — skip
            continue
        if status == 0xB0 and d1 in TOP_ROW_CC:
            idx = d1 - 0x68
            key = ("top", idx)
            if key not in seen:
                seen.add(key)
                print(f"  top button {idx} (CC {d1}) -> control {idx + 200}")
        elif status == 0x90 and d1 in RIGHT_COL_NOTES:
            idx = RIGHT_COL_NOTES.index(d1)
            key = ("right", idx)
            if key not in seen:
                seen.add(key)
                print(f"  right button {idx} (note {d1}) -> control {idx + 100}")
        elif status == 0x90:
            x = d1 % 16
            y = 7 - (d1 // 16)
            if 0 <= x < 8 and 0 <= y < 8:
                key = ("grid", d1)
                if key not in seen:
                    seen.add(key)
                    print(f"  grid note {d1} -> app ({x},{y})")
        else:
            print(f"  (unexpected) status {status:#04x} data {d1}, {d2}")
    reset(out)
    print("\nListener done.")


def main():
    out, midi_in = find_device()
    if out is None:
        sys.exit(1)

    # Out-only open is enough for LEDs; the input port is opened in the
    # listener phase so presses aren't drained before then.
    out.open_port(out.get_ports().index(
        next(n for n in out.get_ports() if SEARCH in n.lower())))
    print("Opened Launchpad. Starting checks...")
    try:
        phase_orientation(out)
        phase_colors(out)
        midi_in.open_port(midi_in.get_ports().index(
            next(n for n in midi_in.get_ports() if SEARCH in n.lower())))
        phase_buttons(out, midi_in)
    finally:
        reset(out)
        try:
            out.close_port()
        except Exception:
            pass
        print("\nDevice reset. Done.")


if __name__ == "__main__":
    main()
