#!/bin/bash
# force-usb-diagnostic.sh — why isn't the Akai Force enumerating over USB MIDI?
#
# Usage: plug the Force's USB-B into a DIRECT Mac port (no hub, DATA cable),
#        power the Force on, then run:  bash force-usb-diagnostic.sh
set -u

VENV="$HOME/Documents/projects/nova-script/.venv/bin/python"

echo "════════════════════════════════════════════════════════"
echo " AKAI FORCE — USB / MIDI ENUMERATION DIAGNOSTIC"
echo "════════════════════════════════════════════════════════"
echo

echo "── [1/3] MIDI ports (python-rtmidi) — the check that matters ──"
if [ -x "$VENV" ]; then
  "$VENV" - <<'PY'
import rtmidi
mi = rtmidi.MidiIn();  mo = rtmidi.MidiOut()
ins  = mi.get_ports()
outs = mo.get_ports()
print("  MIDI INPUTS :", ins)
print("  MIDI OUTPUTS:", outs)
force_ports = [p for p in (ins + outs) if any(k in p.lower() for k in ("force","akai","mpc"))]
mtrack_ports = [p for p in (ins + outs) if any(k in p.lower() for k in ("m-track","mtrack"))]
print()
if force_ports:
    print("  >>> AKAI FORCE / MPC MIDI PORT FOUND:", force_ports)
else:
    print("  >>> No Force / MPC MIDI port (", "M-Track present, Force absent" if mtrack_ports else "no M-Track either", ")")
PY
else
  echo "  (nova-script venv missing — run: python -m src.main list-ports)"
fi

echo
echo "── [2/3] USB tree (best-effort; often empty on Apple Silicon) ──"
USB=$(system_profiler SPUSBDataType 2>/dev/null)
if [ -n "$USB" ]; then
  if echo "$USB" | grep -qiE "Akai|MPC|M-Track|M-Audio|InMusic"; then
    echo "  >>> match at USB layer:"
    echo "$USB" | grep -iE "Akai|MPC|M-Track|M-Audio|InMusic" | sed 's/^/      /'
  else
    echo "  >>> no Akai / MPC / M-Track device in the USB tree"
  fi
else
  echo "  (SPUSBDataType empty — no USB devices enumerated, or macOS hid the tree)"
fi

echo
echo "── [3/3] Verdict ──"
echo "  • Force appears in [1] as a MIDI port    -> DONE, clock can ride USB."
echo "  • Nothing in [1] or [2]                  -> macOS never enumerated it:"
echo "      - use a DATA (not charge-only) USB-B cable"
echo "      - plug DIRECT into the Mac (no hub / dock)"
echo "      - try a different cable / both Mac ports"
echo "  • USB enumerates but no MIDI port         -> Force-side setting:"
echo "      Force -> Settings -> MIDI -> MIDI Sync / USB MIDI = ON"
echo "      (and check Force 'USB Mode' isn't storage/audio-only)"
echo "════════════════════════════════════════════════════════"
