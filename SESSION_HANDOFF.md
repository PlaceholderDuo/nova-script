# Nova-Script Session Handoff

**Date:** 2026-08-04 | **Branch:** main | **Last commit:** b7ced3e

---

## How to Launch

```bash
cd ~/Documents/projects/nova-script
source .venv/bin/activate

# Chill mode (default, ambient LED patterns):
nova-script

# Full engine (live-show profile):
nova-script live-show

# With TUI:
nova-script --tui live-show

# List profiles:
nova-script list
```

**IMPORTANT:** Before launching, kill stale processes: `pkill -f "src.engine"`

The Launchpad Mini MK1 must be plugged directly into the Mac (not through cascaded USB hubs — interrupt IN endpoints fail through chained hubs).

---

## Dev Tools (new — no hardware needed)

All tools live in `tools/` and are independent of the main nova-script engine.

### Virtual Hardware Simulator
Develop and test without a physical Launchpad:

```bash
# Terminal 1: start the virtual MIDI bridge
./tools/run-virtualizer.sh
# Or: .venv/bin/python tools/novation-virtualizer.py

# Browser: opens novation-virtualizer.html automatically
# Click "Connect MIDI" → creates virtual ports like "Launchpad Mini"

# Terminal 2: start nova-script
nova-script live-show
# nova-script auto-discovers the virtual port and connects
```

The browser shows a realistic Launchpad/Launchkey visual. Click pads → sends MIDI events → nova-script reacts. LED updates from nova-script appear in real time on the virtual device.

**Controller presets:** Launchpad Mini MK1 (default), Launchpad MK1, Launchpad Mini MK3, Launchpad Pro MK3, Launchkey 49 MK2. Each renders accurate physical button layouts with labels.

**Keyboard shortcuts:** `1-8` = top row buttons, `Shift+1-8` = right column buttons.

**Stop:** `pkill -f novation-virtualizer`

### LED Grid Editor
Create custom Launchpad grid images visually:

```bash
open tools/led-grid-editor.html
```

- Set grid size, upload reference image for tracing
- G/R/O mode: click cycles OFF → GREEN → RED → AMBER
- RGB mode: click opens full color picker
- Export: generates YAML for `config/screensaver-images.yaml`

---

## Architecture

```
Engine
├── MidiManager (port discovery, 500ms auto-reconnect polling)
│   ├── LaunchpadMiniMK1
│   └── Launchkey49MK2 (InControl port support)
├── BPMClock (OSC beat → MIDI clock → Internal, solid until sync)
├── OscBridge (bidirectional REAPER OSC on :9001/:8000)
├── ComboDetector (Top-1+2=screensaver, Top-1+3=fireworks, Top-1=home)
├── OverlayManager (priority: Fireworks(4) > HUD(3) > Screensaver(2) > Mode(1))
├── StartupWave (amber→green→red diagonal ripple, runs before mode setup)
├── ImageStore (9 images, YAML persistence, 8 quick slots)
├── ModeManager
│   ├── Performance (HOME page — track mutes + FX toggles + strobe tuner, 2 pages)
│   ├── ClipLauncher (8×8 session grid, edit mode with BPM pulsing)
│   ├── Sequencer (7 rows × 32 steps)
│   ├── Mixer (8 tracks × 7-row faders)
│   ├── Menu (spatial 2×2 blocks, not default)
│   └── Message (scrolling 5×5 text display)
└── TUI (Textual, separate thread, profile/settings management)

Dev Tools (independent of engine, in tools/)
├── novation-virtualizer.py (virtual MIDI + WebSocket bridge)
├── novation-virtualizer.html (browser-based hardware visualizer)
├── run-virtualizer.sh (one-command launcher)
└── led-grid-editor.html (visual YAML grid creator)
```

### Mode Shortcuts (global, any mode)
| Button | Mode |
|--------|------|
| Top-1 | Home (Performance) |
| Top-2 | Performance |
| Top-3 | Clip Launcher |
| Top-4 | Sequencer |
| Top-5 | Mixer |

### Top-1 LED Behavior
- Orange at home (Performance mode), green in other modes
- Stays **solid** until external BPM sync arrives (OSC `/beat` or MIDI clock)
- After sync: blinks at BPM with downbeat distinction (configurable in settings)

### Page Navigation
- Right column A/B = page indicators (amber = available, green = current)
- Performance mode: page 1 = mute+FX, page 2 = Extended FX (placeholder)

---

## Key Files

| File | Purpose |
|------|---------|
| `src/engine.py` | Central event loop, all system wiring |
| `src/midi/manager.py` | Port discovery + auto-reconnect |
| `src/midi/clock.py` | Multi-source BPM with priority hierarchy |
| `src/controllers/launchpad_mk1.py` | MK1 protocol (LED + input parsing) |
| `src/controllers/launchkey_mk2.py` | Launchkey MK2 protocol |
| `src/controllers/color_map.py` | LogicalColor enum + hardware mapping |
| `src/ui/mode.py` | Mode base class (long press, pages, debounce) |
| `src/ui/overlay_manager.py` | Priority overlay stack |
| `src/ui/image_store.py` | 64-image YAML persistence |
| `src/ui/startup_wave.py` | Boot animation |
| `src/ui/fireworks.py` | BPM-synced particle system |
| `src/ui/combo_detector.py` | Multi-button combo detection |
| `src/ui/chill_mode.py` | Default ambient LED patterns |
| `src/tui/app.py` | Full TUI (settings, profiles, grid mirror) |
| `src/tui/chill_tui.py` | Minimal TUI for chill mode |
| `tests/virtualizer.py` | Virtual hardware for testing |
| `config/profiles/live-show.yaml` | Default music performance profile |
| `config/nova-script.ReaperOSC` | REAPER OSC pattern config |
| `docs/PAD-NAVIGATION-MANUAL.md` | Complete button reference |
| `docs/FEATURES_AND_SPECS.md` | Full UX specification |
| `docs/REFERENCE_PROJECTS.md` | Comparative research |
| `tools/novation-virtualizer.py` | **New** — Virtual MIDI + WebSocket backend |
| `tools/novation-virtualizer.html` | **New** — Browser-based hardware visualizer |
| `tools/run-virtualizer.sh` | **New** — One-command virtualizer launcher |
| `tools/led-grid-editor.html` | **New** — Visual grid image creator/editor |
| `BUILD_LOG.md` | 21 entries of development history |

---

## Known Current State

### Working (verified on hardware)
- LED output (all colors, patterns)
- Grid button input (correct coordinates)
- Top row + right column button input
- Startup wave animation
- Performance mode renders correctly
- Screensaver cycling (heart ⇄ peace)
- Page indicators (A/B)
- Mode shortcuts (Top row 2-5)
- BPM clock LED (solid until sync)
- Press feedback (flash on press)

### Working (virtualizer — no hardware needed)
- Virtual MIDI port creation
- Browser-based pad press simulation → MIDI events
- Real-time LED state visualization in browser
- Device switching (Launchpad/Launchkey)
- LED-accurate color rendering with glow effects
- Per-controller physical button layouts with labels

### Needs Hardware Verification
- Combo detection (Top-1+2/3) — logic verified, not tested with simultaneous press
- Strobe tuner — renders but needs actual OSC tuner data from Reaper
- FX hints — renders but needs OSC feedback to confirm
- Clip Launcher edit mode — needs user testing

### Known Issues
- Peace sign image may need further refinement
- Screensaver images were upside down (Y-flip fixed in b7ced3e)
- Startup wave was showing "red block" (fixed: wave now runs before mode setup)
- Stale Python processes can hold MIDI port — use `pkill -f "src.engine"` before launch
- Launchpad must NOT be behind cascaded USB hubs (interrupt endpoints fail)

---

## Next Priorities

1. **Extended FX page** — populate page 2 of Performance mode with vocal filters, fuzz, song-specific FX
2. **Akai Force MIDI integration** — connect Force USB MIDI for clock sync + track control
3. **Multi-device architecture** — simultaneous Launchpad + Launchkey control with device profiles
4. **Color picker in TUI** — hardware-aware palette (MK1 discrete vs MK3 RGB), custom RGB picker
5. **Reaper OSC testing** — send actual OSC messages, verify round-trip
6. **Cascaded hub test** — determine if the input issue was purely hub chain or also user-action
7. **More screensaver images** — build out the image library using the new LED grid editor tool

---

## Settings Reference

Settings are in `config/profiles/live-show.yaml` and editable via TUI (S key).

### Clock Sources
- Preferred: "Reaper (OSC)", any MIDI port name, "Internal"
- Fallback: same options
- Internal BPM: 120 (default)

### Visual
- Downbeat flash: "tempo_led" (beat 1 distinct) / "4 corners" / "disable"
- Downbeat color: GREEN_HIGH, RED_HIGH, AMBER_HIGH, etc.
- Visual hints: ON/OFF (default ON)

### Mixer
- 16 channels: alias (spaces ok), output (OSC/MIDI), curve, OSC addr, MIDI channel+CC

### Screensaver
- Brightness: 0-100% (maps to LOW/MED/HIGH for MK1)
- Cycle enabled: true/false
- Idle timeout: ms
