# Nova-Script Build Log

<!-- ════════════════════════════════════════════════════════════════════════
     🟢 START HERE — session handoff (2026-08-14)
     New session? Read these entries first (complete current state):

       1. Entry #50 — Launchpad Light Show verified on hardware + rod test
       2. Entry #49 — Lighting Revamp: Rod Discovery + Design Quiz + "Sits and
                      Vibes" engine (this session's big arc)

     The lighting-engine counterpart is in the SEPARATE repo
     ~/Documents/projects/lighting-system/BUILD_LOG.md — read its "START HERE"
     header too. They're two halves of the same feature.

     nova-script owns: Light Show mode (Launchpad UI), per-song mood plumbing
     (songs.js + tui.js emit genre/mood into /tmp/lighting_feed).
     lighting-system owns: the engine, looks/effects/palettes, rod discovery,
     govee LAN + BLE, the DMX/QLC+ pipeline.

     Next up: look-revamp CONTENT (see lighting-system BUILD_LOG wrap-up).
     ════════════════════════════════════════════════════════════════════════ -->

---

## Entry #1 — 2026-08-03 — Project Inception & Architecture Specification

### Source
Daniel via Claude Code session. Full specification delivered verbally.

---

### Project Purpose
**Nova-Script** is a unified Novation controller scripting environment and custom performance controller. It transforms Novation hardware (Launchpad + Launchkey series) into a deeply integrated show-rig control surface that bridges Reaper (DAW), the Akai Force, and other MIDI/OSC-enabled devices into one cohesive live performance system.

The code we write + the Launchpad Mini MK1 act together as a single, advanced MIDI controller with:
- A built-in step sequencer
- Mixer mode
- Menu-driven UI on LED pads
- Deep parameter control of Reaper via OSC
- MIDI output over USB to the Akai Force
- Rich LED pad feedback systems

The ultimate goal is to **unify the entire rig** — connecting Reaper, the Akai Force, and all MIDI controllers together seamlessly as one show-ready system.

### Primary Hardware
1. **Novation Launchpad Mini MK1** (original) — Primary control surface. LED pads used as UI display. Limited color palette (amber/red/green at low/mid/high brightness = ~9 usable states).
2. **Novation Launchkey 49 MK2** — Secondary control surface. Will receive similar rich LED pad feedback, custom control mappings, new ways of playing/creating sounds.
3. **Akai Force** — Target device receiving MIDI over USB from the MacBook. Controlled for: track volumes, effects levels per track, step-sequenced notes, and more.
4. **MacBook M1** — Host machine running Reaper, this scripting environment, and routing MIDI/OSC between all devices.

### Target Software Integration
- **Reaper** (DAW) — Receives OSC commands for deep parameter control. Sends OSC events back for status feedback. Custom scripting inside Reaper (ReaScript/Lua) will send OSC to nova-script.
- **Custom Reaper Scripts** — Send OSC events to nova-script for things like "display message" (scrolling text on Launchpad LEDs when user is not actively pressing buttons).

### Architecture Overview

#### Communication Flow
```
Launchpad Mini MK1  <--MIDI-->  nova-script  <--OSC-->  Reaper (ReaScripts)
Launchkey 49 MK2    <--MIDI-->       |         <--MIDI--> Akai Force
                                     |
                              TUI / Visual UI
                         (configuration & debug mirror)
```

#### Three-Layer Architecture

**Layer 1: Device Abstraction Layer** (`src/controllers/`)
- Universal device model that works across all Novation controllers
- Handles raw MIDI I/O: reading button presses, writing LED states
- Per-device subclasses: `LaunchpadMiniMK1`, `Launchkey49MK2`, and future `LaunchpadMiniMK3`, `LaunchpadProMK3`, `LaunchpadX`, etc.
- LED abstraction: normalizes the limited MK1 color palette (amber/red/green × brightness) into a common color model that richer controllers can fully utilize
- Input event normalization: all button presses become unified `GridEvent` or `ControlEvent` objects regardless of source device

**Layer 2: UI / Mode Layer** (`src/ui/`)
- Operates on a logical grid abstraction — doesn't care which physical controller is connected
- Modes (mutually exclusive, one active at a time):
  - **Menu Mode** — Top-level navigation. Buttons launch sub-modes.
  - **Step Sequencer Mode** — Grid-based step sequencing. Rows = pitches/notes, columns = steps. Scrolling regions for longer sequences. Pattern chaining.
  - **Mixer Mode** — Track volumes, pan, mute/solo, send levels. Vertical fader representation on LED columns.
  - **Effects Mode** — Per-track effect parameter control. Device chain navigation.
  - **Performance Mode** — Clip/scene launching (Ableton-style). Session view on the grid.
  - **Device Control Mode** — 8-knob style parameter banks for selected device.
  - **Message Display Mode** — Passive scrolling text display on LEDs. Auto-activates when incoming OSC message arrives while user is idle. Dismisses on any button press.
- Mode switching: triggered by dedicated hardware buttons (top row / side column) or OSC command

**Layer 3: Protocol Bridge Layer** (`src/midi/` + `src/osc/`)
- **MIDI Out** (`src/midi/`): Routes sequenced notes, CC messages, and program changes to the Akai Force and other external gear
- **OSC Client** (`src/osc/`): Sends parameter changes to Reaper (track volumes, FX params, transport control, etc.)
- **OSC Server** (`src/osc/`): Listens for incoming events from Reaper scripts — "display message", status updates, metering data, playback position
- **MIDI Routing** (`src/midi/routing.py`): Configurable routing table — which MIDI events go to which output port

#### Display Message System
- Triggered by OSC message from Reaper: e.g., `/display/message "Track 3: Compressor bypassed"`
- Only displays if the Launchpad has been idle (no button presses) for a configurable timeout (e.g., 2 seconds)
- Text scrolls across the 8×8 grid using LED animations
- Any button press immediately dismisses the message and returns to active mode
- Queue: multiple messages can stack; displayed sequentially
- Will need a character-to-grid mapping for legible text on an 8×8 low-res display

### UI Design — Abbeton Live-Inspired Interaction Model
- **Grid (8×8 on MK1)** = primary interaction surface
- **Top row (round buttons on MK1)** = mode selectors / function keys
- **Right column (round buttons on MK1)** = scene/pattern triggers or sub-mode modifiers
- Mode-dependent LED feedback: pads light up in context-sensitive colors showing state (empty slot, clip loaded, clip playing, step active, step current, muted track, etc.)
- Button hold vs. press: short press = trigger, long press = secondary action (delete, copy, etc.)

### Launchkey 49 MK2 Integration
- LED pads (16 pads, 4×4 or arranged in two rows of 8) repurposed with rich feedback
- Pads can mirror a quadrant of the Launchpad grid, act as drum pads with velocity-sensitive LED feedback, or serve as mode-specific function pads
- Knobs and faders mapped contextually to the active mode
- Transport buttons integrated
- The goal: Launchkey becomes a companion controller that extends the Launchpad's capabilities, not a duplicate

### Future Hardware Support
- Launchpad Mini MK3 / MK4
- Launchpad X
- Launchpad Pro MK3
- Launchkey Mini MK3 / MK4
- All should work with the same codebase — only the device-specific subclass changes

### Technical Considerations
- **LED Color Abstraction**: MK1 has a very limited palette (amber low/med/high, red low/med/high, green low/med/high = 9 states + off). Newer Launchpads support full RGB. The abstraction layer must map logical colors (e.g., "track-armed", "clip-playing") to the best available hardware representation. On MK1, "blue" might become green-high; on MK3, it's actual blue.
- **MIDI Port Management**: Both Launchpad and Launchkey present as multiple MIDI ports (input, output, sometimes a secondary DAW port). Need robust port discovery by device name.
- **Timing**: Step sequencer needs solid clock. Options: internal clock, MIDI clock from Reaper/Akai Force, or OSC-synced transport from Reaper.
- **OSC Namespace**: Design a clean, consistent OSC address space for Reaper communication (e.g., `/nova/track/1/volume`, `/nova/transport/play`, `/nova/display/message`)
- **TUI/Visual UI**: A companion interface (Textual-based TUI initially) that mirrors the Launchpad grid with color-accurate representation, shows active mode, and provides configuration/debug access. The TUI runs in a separate process/thread and communicates with the engine via a lightweight IPC.

### Dependencies (Planned)
- **python-rtmidi** — MIDI I/O
- **python-osc** — OSC client/server
- **Textual** — TUI framework for the companion interface
- **PyYAML** — Configuration file parsing
- **asyncio** — Concurrency model for handling MIDI and OSC simultaneously

### Project Structure
```
nova-script/
├── BUILD_LOG.md              # This file
├── README.md                 # Project overview and quickstart
├── ARCHITECTURE.md           # Detailed architecture documentation
├── REQUIREMENTS.md           # Functional and non-functional requirements
├── .gitignore
├── config/
│   └── default.yaml          # Default configuration
├── src/
│   ├── __init__.py
│   ├── main.py               # Entry point
│   ├── engine.py             # Core engine: device management, mode dispatch, event loop
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── base.py           # Abstract base: NovationController
│   │   ├── launchpad_base.py # Shared Launchpad logic (grid abstraction)
│   │   ├── launchpad_mk1.py  # Launchpad Mini MK1
│   │   ├── launchkey_base.py # Shared Launchkey logic
│   │   ├── launchkey_mk2.py  # Launchkey 49 MK2
│   │   └── color_map.py      # Logical color → hardware color mapping
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── mode.py           # Base Mode class
│   │   ├── mode_manager.py   # Mode switching, lifecycle
│   │   ├── modes/
│   │   │   ├── __init__.py
│   │   │   ├── menu.py       # Menu/navigation mode
│   │   │   ├── sequencer.py  # Step sequencer mode
│   │   │   ├── mixer.py      # Mixer mode
│   │   │   ├── effects.py    # Effects control mode
│   │   │   ├── performance.py # Clip/scene launch mode
│   │   │   ├── device.py     # Device/plugin control mode
│   │   │   └── message.py    # Scrolling message display mode
│   │   ├── grid.py           # Logical grid: N×M abstract grid with pixel/color ops
│   │   └── display.py        # Text renderer for scrolling messages on LED grid
│   ├── midi/
│   │   ├── __init__.py
│   │   ├── manager.py        # MIDI port discovery, connection management
│   │   ├── routing.py        # MIDI routing table and transformation
│   │   └── clock.py          # Clock source (internal/external/sync)
│   ├── osc/
│   │   ├── __init__.py
│   │   ├── server.py         # OSC server (receives from Reaper)
│   │   ├── client.py         # OSC client (sends to Reaper)
│   │   └── namespace.py      # OSC address space definitions
│   ├── tui/
│   │   ├── __init__.py
│   │   ├── app.py            # Textual app entry point
│   │   ├── grid_widget.py    # Visual grid mirror widget
│   │   ├── mode_panel.py     # Active mode display
│   │   ├── log_panel.py      # Event/activity log
│   │   └── config_screen.py  # Configuration UI
│   └── layout/
│       ├── __init__.py
│       └── grid.py           # Grid coordinate math, subgrids, viewports
├── tests/
│   ├── __init__.py
│   ├── test_controllers.py
│   ├── test_grid.py
│   ├── test_mode_manager.py
│   └── test_osc_namespace.py
├── scripts/
│   └── run.sh                # Launch script
└── docs/
    └── midi-reference.md     # MIDI spec reference for Novation devices
```

### Open Questions / Decisions Pending
- **MIDI input receiving**: The "receive MIDI events" path from Reaper/Akai Force is not fully specified. What specific MIDI events will flow back to nova-script? Status updates? Transport sync? Metering?
- **Clock master**: Who provides the master clock? Internal? Reaper via OSC? Akai Force via MIDI? All three as options?
- **Reaper ReaScript integration**: Exact Lua/Python scripts needed on the Reaper side. What OSC address space does Reaper natively understand vs. what needs custom ReaScript?
- **Message display character set**: For the scrolling text on 8×8 LED grid — what characters do we need? Full ASCII? Numbers + common symbols only?
- **Launchkey pad arrangement**: The 16 pads on Launchkey 49 MK2 — arranged as 4×4? 2×8? Need to verify physical layout and choose a logical mapping.
- **Configuration persistence**: How are mode mappings, MIDI routings, and custom layouts saved and loaded? YAML config file? Multiple profiles?

### First Actions (Next Session)
1. Initialize Python project with `pyproject.toml` and dependency management
2. Implement device discovery: scan MIDI ports, identify Launchpad Mini MK1 and Launchkey 49 MK2 by name
3. Implement the `NovationController` base class and `LaunchpadMiniMK1` subclass with basic LED control (turn pads on/off with colors)
4. Implement the logical grid abstraction — 8×8 coordinate system with color state tracking
5. Implement the first mode: Menu Mode — display menu options on the grid, respond to button presses
6. Build the OSC server stub — listen on a port, parse incoming messages
7. Build the Textual TUI grid mirror — show a live 8×8 colored grid representing the Launchpad

---

## Entry #2 — 2026-08-03 — Core Engine, Device Manager, Menu Mode, Sequencer, Mixer

### Source
Daniel via Claude Code. First implementation pass.

### Changes Made
- **MIDI Manager** (`src/midi/manager.py`): Full port discovery and auto-reconnect system.
  - Scans for devices by name substring match
  - Polls every 500ms for port add/remove events
  - Auto-reconnects on cable bump — detects port disappearance, tears down gracefully, scans until device reappears, restores state
  - asyncio-safe MIDI event queue
  - Connect/disconnect callbacks
  - Tested: detects Launchpad Mini MK1 input and output ports

- **Color Map** (`src/controllers/color_map.py`): Logical color abstraction layer.
  - `LogicalColor` enum with 27 values (OFF + 9 colors × 3 brightness levels)
  - `MK1_COLOR_MAP`: maps logical colors to Launchpad Mini MK1 velocity bytes (red/green bit-packing: velocity = (green << 4) | red)
  - `MK3_COLOR_PALETTE_INDEX`: placeholder for future RGB controllers using palette index approach
  - `ColorMapper` class selects map based on device type

- **Base Controller** (`src/controllers/base.py`): Abstract `NovationController` base.
  - `DeviceCapabilities` dataclass for capability introspection
  - `GridEvent` and `ControlEvent` normalized event types
  - Abstract `parse_midi()` and `send_led()` methods
  - Local grid state tracking with `set_grid_color()`, `clear_grid()`, `refresh_grid()`

- **Launchpad Mini MK1** (`src/controllers/launchpad_mk1.py`): Full implementation.
  - Grid pad note mapping: logical (0,0)=bottom-left → MIDI note = (7-y)*16+x
  - Right column buttons parsed from notes [8, 24, 40, 56, 72, 88, 104, 120]
  - Top row buttons parsed from CC 104-111
  - LED output for grid, top row, and right column
  - `_reset_to_session()` sends CC reset + SysEx layout select on connect
  - Verified: LED output works (amber pads light up)

- **Launchkey 49 MK2** (`src/controllers/launchkey_mk2.py`): Stub implementation.
  - 16 velocity-sensitive pads (2 rows × 8 cols)
  - 8 knobs, 8 faders, transport buttons parsed from CC
  - Ready for full implementation when needed

- **Logical Grid** (`src/layout/grid.py`): Grid abstraction with utility methods.
  - `set_cell()`, `get_cell()`, `clear()`, `fill_rect()`, `fill_row()`, `fill_column()`
  - `draw_text_horizontal()`, `draw_bar_vertical()` for mixer/display modes
  - Dirty cell tracking for efficient LED updates
  - `snapshot()` for TUI mirror

- **Mode System** (`src/ui/mode.py`, `src/ui/mode_manager.py`):
  - Abstract `Mode` base with `enter()`, `exit()`, `handle_grid_event()`, `handle_control_event()`, `tick()`
  - `ModeManager` handles lifecycle: only one mode active at a time
  - Mode switching preserves state, calls enter/exit

- **Menu Mode** (`src/ui/modes/menu.py`): First working mode.
  - Configurable grid of mode-select buttons with colors
  - Top-row function buttons also select modes
  - Right-column buttons cycle pages for >8 items
  - Debounced input

- **Step Sequencer Mode** (`src/ui/modes/sequencer.py`): Core functionality.
  - 7 rows × 32 steps (8 visible, scrollable with pages)
  - Toggle steps on/off by pressing grid pads
  - Internal clock at configurable BPM and resolution (1/4 to 1/32)
  - Play/pause, reset, page left/right via top row buttons
  - Resolution up/down via right column buttons
  - Sends MIDI note on for active steps to configured output
  - Visual feedback: current step highlighted, active steps colored by row group

- **Mixer Mode** (`src/ui/modes/mixer.py`): Volume faders.
  - 8 tracks × 7 fader rows (0-100% resolution)
  - Tap fader position to set volume
  - Mute toggle in bottom row
  - Green gradient for volume, red for muted

- **Engine** (`src/engine.py`): Central event loop.
  - YAML config loading
  - Controller setup → MidiManager start (with initial connect) → mode setup
  - Event loop reads from MIDI queue, dispatches to controllers/modes
  - TUI broadcast: snapshots grid state every 50ms to queue.Queue

- **TUI Companion** (`src/tui/app.py`): Textual-based grid mirror.
  - 8×8 grid of colored cells mirroring Launchpad LED state
  - Color mapping from LogicalColor enum names to terminal colors
  - Mode indicator and device connection status
  - Polls engine queue at 50ms intervals
  - Runs in separate thread with its own asyncio loop via Textual

- **Entry Point** (`src/main.py`): Headless mode by default, `--tui` flag for TUI.
  - `python -m src.main` → headless engine only
  - `python -m src.main --tui` → engine + TUI companion

### Known Issues
- **Launchpad input not receiving**: The Launchpad Mini MK1 accepts LED commands but does not send button press MIDI messages. Likely cause: the device is in a custom mode set by the Live Show Manager / REAPER integration. The code handles input correctly but needs the Launchpad in default Session mode. Added `_reset_to_session()` in `on_connect` to send CC reset + SysEx layout select. May need physical power-cycle or different SysEx initialization.

### Files Affected
- `src/midi/manager.py` — New: full MIDI port management with auto-reconnect
- `src/controllers/color_map.py` — New: logical-to-hardware color mapping
- `src/controllers/base.py` — New: abstract controller base
- `src/controllers/launchpad_mk1.py` — New: Launchpad Mini MK1 implementation
- `src/controllers/launchkey_mk2.py` — New: Launchkey 49 MK2 stub
- `src/layout/grid.py` — New: logical grid with utility methods
- `src/ui/mode.py` — New: abstract Mode base
- `src/ui/mode_manager.py` — New: mode lifecycle manager
- `src/ui/modes/menu.py` — New: menu navigation mode
- `src/ui/modes/sequencer.py` — New: step sequencer mode
- `src/ui/modes/mixer.py` — New: mixer fader mode
- `src/engine.py` — New: central event loop
- `src/tui/app.py` — New: Textual TUI grid mirror
- `src/main.py` — New: entry point
- `src/__init__.py` — Updated: version only
- `src/controllers/__init__.py` — Updated: re-exports

### Next Actions
1. Debug Launchpad input — try physical power-cycle, verify SysEx reset sequence
2. Implement OSC server/client for Reaper communication
3. Build Message Display Mode with scrolling text on LED grid
4. Test with Launchkey 49 MK2
5. Add MIDI clock sync from external sources

---

## Entry #3 — 2026-08-03 — Targeted Research Session: Hardware Protocols & Integration

### Source
Daniel via Claude Code. Research session to resolve blocked Launchpad input, gather protocol references for Launchkey MK2, REAPER OSC, and future hardware support.

---

### 1. Launchpad Mini MK1 — Complete Protocol Reference

**Source:** FMMT666/launchpad.py (authoritative open-source library), Novation programmer's docs, GitHub issues

#### Critical Finding: No SysEx Initialization Needed
The Launchpad Mini MK1 is **protocol-identical to the original Launchpad MK1**. It needs NO SysEx initialization. Opening the MIDI port is sufficient. It boots into "Session mode" automatically on USB power.

#### The "LEDs Work, Buttons Don't" Bug — KNOWN ISSUE
This is a documented PyGame/ALSA MIDI driver bug affecting the MK1. The input buffer gets into a bad state on port re-open after a program restart.

**Workaround (applied in `_kick_input_buffer()`):**
```
# Toggle all automap LEDs to kick the input buffer:
for i in range(8):
    B0 (0x68+i) 0x33   # amber on
    B0 (0x68+i) 0x00   # off
B0 00 00               # reset all LEDs
```
Alternatively: physically pressing any automap button after program start works too.

#### Grid Pad Note Mapping (confirmed correct)
```
Row 0 (top):    0   1   2   3   4   5   6   7
Row 1:         16  17  18  19  20  21  22  23
Row 2:         32  33  34  35  36  37  38  39
Row 3:         48  49  50  51  52  53  54  55
Row 4:         64  65  66  67  68  69  70  71
Row 5:         80  81  82  83  84  85  86  87
Row 6:         96  97  98  99 100 101 102 103
Row 7 (bot):  112 113 114 115 116 117 118 119
```
Sent as Note On (0x90) channel 1. Velocity 127 = press, 0 = release.

#### Top Row (Automap) Buttons — CC 104-111
```
B0 68 → B0 6F (left to right). Value 127 = press, 0 = release.
LED control: B0 (0x68+index) <color>
```

#### Right Column Buttons — Notes 8, 24, 40, 56, 72, 88, 104, 120
```
Notes top-to-bottom: 8, 24, 40, 56, 72, 88, 104, 120
LED control: 90 <note> <color>
```

#### LED Color Encoding (confirmed correct)
Formula: `color = (green << 4) | red` where green, red ∈ {0,1,2,3}

| Color | R | G | Hex | Dec |
|-------|---|---|-----|-----|
| Off | 0 | 0 | 0x00 | 0 |
| Red Low | 1 | 0 | 0x01 | 1 |
| Red Med | 2 | 0 | 0x02 | 2 |
| Red Full | 3 | 0 | 0x03 | 3 |
| Green Low | 0 | 1 | 0x10 | 16 |
| Green Med | 0 | 2 | 0x20 | 32 |
| Green Full | 0 | 3 | 0x30 | 48 |
| Amber Low | 1 | 1 | 0x11 | 17 |
| Amber Med | 2 | 2 | 0x22 | 34 |
| Amber Full | 3 | 3 | 0x33 | 51 |
| Yellow-green Low | 1 | 2 | 0x21 | 33 |
| Red-orange Low | 2 | 1 | 0x12 | 18 |

**Rapid LED Update Mode** (for batch LED changes):
```
Send Note On on channel 3 (0x92): 92 <led1> <led2>
Resets cursor: B0 01 00
Writes pairs sequentially across all 80 LEDs:
  8×8 grid (row 0→7, left→right)
  → right column (top→bottom)
  → automap (left→right)
```

**Reset command:** `B0 00 00` (all LEDs off). Confirmed.

**No flashing, no double-buffering on MK1.** These are MK2/Pro features.

**Mode switching:** Cannot be done programmatically on MK1. The front-panel buttons (Session, User 1, User 2, Drum Rack, Mixer) are physical-only. For MK2+, layout selectable via: `F0 00 20 29 02 10 22 <mode> F7`

---

### 2. macOS CoreMIDI Port Sharing

**Source:** RtMidi.cpp source code, CoreMIDI architecture docs

**CoreMIDI broadcasts to ALL clients.** Multiple applications can simultaneously receive from the same physical device. mach_port architecture is inherently multicast.

**No exclusive mode.** Unlike Windows MIDI or ALSA, there's no `kMIDIPropertyExclusive` flag or mechanism to claim exclusive access. `MIDIPortConnectSource()` just adds another subscriber.

**python-rtmidi uses a singleton MIDIClientRef:**
```cpp
static MIDIClientRef CoreMidiClientSingleton = 0;
// All MidiIn/MidiOut instances share one client
```

**Virtual ports do NOT intercept physical device traffic.** MIDISourceCreate/MIDIDestinationCreate create separate virtual endpoints.

**Audio MIDI Setup cannot redirect exclusively.** It provides device on/off and virtual routing only.

**Conclusion for our situation:** The "Live Show Manager" app listing the Launchpad does NOT consume input exclusively. The Launchpad not sending button events is the buffer bug, not port contention. Verified by our raw python-rtmidi test showing zero messages even with all filters disabled.

---

### 3. Launchkey 49 MK2 — Complete Protocol Reference

**Source:** Novation Launchkey MK2 Programmer's Reference Guide v1.01 (8 pages)

#### Two MIDI Ports
- **MIDI (port 1):** Keys, pitch/mod wheels always here. Basic mode controls here.
- **InControl (port 2):** Extended mode communication. All lighting/mode commands MUST be sent here.

#### Mode Switching (via InControl port, Channel 16)
| Operation | Message | Hex |
|-----------|---------|-----|
| Enter Extended | Note C-1, Ch16, Vel 127 | `9F 0C 7F` |
| Exit Extended | Note C-1, Ch16, Vel 0 | `9F 0C 00` |
| Pots → InControl | C#-1, Ch16, Vel 127 | `9F 0D 7F` |
| Sliders → InControl | D-1, Ch16, Vel 127 | `9F 0E 7F` |
| Drum Pads → InControl | D#-1, Ch16, Vel 127 | `9F 0F 7F` |
| Query LED states | B-1, Ch16, Vel 0 | `9F 0B 00` |

#### Pad MIDI Notes (16 velocity-sensitive pads, 2×8 grid)
**Basic Mode (Channel 16, InControl port):** Notes 36-51 (C1 to D#2)
```
Row 0: 36 37 38 39 40 41 42 43   (C1–G1)
Row 1: 44 45 46 47 48 49 50 51   (G#1–D#2)
```
**Extended Mode (Channel 16, InControl port):** 
```
Row 0: 112 113 114 115 116 117 118 119   (E7–B7)
Row 1:  96  97  98  99 100 101 102 103   (C6–G6)
```

#### Pad LED Control — RGB via Fixed Color Palette
Light pad: `9F <note> <color_index>` (Note On, Ch16, velocity = color index 1-127)
Off: `9F <note> 0`

**Flashing LEDs** (sync to MIDI clock): Channel 2
```
91 <note> <color>  — Flash between current and new color
9F <note> 0        — Stop
```

**Pulsing LEDs** (brightness modulation, sync to MIDI clock): Channel 3
```
92 <note> <color>  — Pulse
9F <note> 0        — Stop
```

**Reset all pad LEDs:** `BF 00 00` (CC 0, Ch16, Val 0)

#### Control Mappings (all on MIDI port, CC messages)

**Knobs (8):** CC 21-28 (0x15-0x1C), range 0-127
**Faders (8):** CC 41-48 (0x29-0x30), range 0-127
**Master Fader (9th):** CC 7 (0x07)
**Transport buttons (momentary):**
| Button | CC Dec |
|--------|--------|
| Rewind | 112 |
| Forward | 113 |
| Stop | 114 |
| Play | 115 |
| Loop | 116 |
| Record | 117 |
| Track Left | 103 |
| Track Right | 102 |

#### SysEx Device ID
Device Inquiry Reply: `F0 7E 00 06 02 00 20 29 7A 00 FM1 FM2 R1 R2 R3 R4 F7`
- Manufacturer: 00 20 29 (Novation)
- Product: 7A 00 (Launchkey MK2)
- FM1: 01 = 49-key model
- R1-R4: BCD firmware version

#### No Display/LCD on MK2
The Launchkey 49 MK2 has no screen. MK3/MK4 models have screens.

---

### 4. REAPER OSC API — Complete Reference

**Source:** Default.ReaperOSC config, REAPER OSC documentation

#### Configuration
- Preferences → Control/OSC/web → Add → OSC
- Pattern file: `.ReaperOSC` format
- Port: configurable (REAPER listens and sends on separate ports)

#### Track Control (incoming: controller → REAPER)
| Parameter | OSC Address | Values |
|-----------|------------|--------|
| Volume | `/track/{n}/volume` | 0.0–1.0 or dB |
| Pan | `/track/{n}/pan` | -1.0 to 1.0 |
| Mute | `/track/{n}/mute` | 0/1 |
| Solo | `/track/{n}/solo` | 0/1 |
| Rec Arm | `/track/{n}/recarm` | 0/1 |
| Track Select | `/track/{n}/select` | 0/1 |
| Monitor | `/track/{n}/monitor` | 0/1 |
| Track Color | `/track/{n}/trackcolor` | int (RGB) |

#### FX Control
| Parameter | OSC Address |
|-----------|------------|
| FX Bypass | `/track/{n}/fx/{k}/bypass` |
| FX Wet/Dry | `/track/{n}/fx/{k}/wetdry` |
| FX Parameter | `/track/{n}/fx/{k}/fxparam/{p}/value` |
| Open FX Chain | `/track/{n}/fx/chain/open` |
| Focused FX Name | `/focusedfx/name` (REAPER sends) |
| Focused FX Param | `/focusedfx/param/{p}/value` |

#### Send/Receive Control
| Parameter | OSC Address |
|-----------|------------|
| Send Volume | `/track/{n}/send/{k}/volume` |
| Send Pan | `/track/{n}/send/{k}/pan` |
| Send Mute | `/track/{n}/send/{k}/mute` |
| Receive Volume | `/track/{n}/receive/{k}/volume` |

#### Transport
| Control | OSC Address |
|---------|------------|
| Play | `/play` (1=on, 0=off) |
| Stop | `/stop` |
| Record | `/record` |
| Pause | `/pause` |
| Loop | `/repeat` |
| Rewind | `/rewind` |
| Forward | `/forward` |
| Tempo | `/tempo` (float BPM) |
| Position | `/time` (seconds) |

#### Feedback (REAPER → controller)
| Data | OSC Address |
|------|------------|
| Track VU (L) | `/track/{n}/vu` (float 0-1) |
| Track VU (stereo) | `/track/{n}/vu` (2 floats) |
| Master VU | `/master/vu` |
| Beat Position | `/beat` (float, beats since start) |
| Time Signature Num | `/timesig/numerator` |
| Play State | `/play` (sent back) |
| Loop State | `/repeat` (sent back) |
| Track Name | `/track/{n}/name` (REAPER sends) |
| FX Name | `/track/{n}/fx/{k}/name` (REAPER sends) |
| FX Param Name | `/track/{n}/fx/{k}/fxparam/{p}/name` |

#### Actions & Custom
```
# Trigger REAPER action by ID:
/action <int_id>

# Trigger by string command ID:
/action/str <string_id>

# ReaScript can send custom OSC via:
reaper.OscLocalMessageToHost("custom/message", value)
```

#### OSC Bundles
Supported. Bundles processed atomically with timetags for sample-accurate timing.

#### .ReaperOSC Pattern Format
```
# Comment
DEVICE_TRACK_COUNT 8
DEVICE_FX_COUNT 4
DEVICE_FX_PARAM_COUNT 16
DEVICE_TRACK_FOLLOWS DEVICE       # or LAST_TOUCHED or FOCUSED
DEVICE_FX_FOLLOWS DEVICE
TRACK_VOLUME n/track/@/volume     # @ = track index substitution
TRACK_MUTE n/track/@/mute
VU_TRACK n/track/@/vu
PLAY /play
ACTION i/action/@
```

---

### 5. Nova-Script OSC Namespace (Revised)

Based on REAPER research, our OSC namespace maps cleanly:

```
# Controller → REAPER
/nova/track/{n}/volume        f 0.0-1.0    → REAPER /track/{n}/volume
/nova/track/{n}/pan           f -1.0-1.0   → REAPER /track/{n}/pan
/nova/track/{n}/mute          i 0/1        → REAPER /track/{n}/mute
/nova/track/{n}/fx/{k}/bypass  i 0/1       → REAPER /track/{n}/fx/{k}/bypass
/nova/track/{n}/fx/{k}/param/{p} f 0.0-1.0 → REAPER /track/{n}/fx/{k}/fxparam/{p}/value
/nova/transport/play          i 0/1        → REAPER /play
/nova/transport/stop          —            → REAPER /stop
/nova/transport/record        i 0/1        → REAPER /record
/nova/action/{id}             i           → REAPER /action

# REAPER → Controller
/nova/display/message         s "text"     → Show scrolling message on Launchpad
/nova/mode/set                s "name"     → Switch active mode via OSC
/nova/track/{n}/vu            f 0.0-1.0    → From REAPER /track/{n}/vu
/nova/beat                    f position   → From REAPER /beat
/nova/play_state              i 0/1/2      → From REAPER /play + /stop
```

---

### 6. Our OSC Architecture (Design)

Based on research, the cleanest approach for Reaper ↔ nova-script:

**Option A: REAPER's built-in OSC control surface**
- Configure REAPER with a `.ReaperOSC` file that maps to `/nova/...` namespace
- REAPER's built-in OSC support handles track/FX control natively
- Limited to what REAPER natively supports

**Option B: ReaScript bridge (recommended for custom behavior)**
- Write a small ReaScript (Lua) that creates a TCP/UDP OSC bridge
- ReaScript calls `reaper.OscLocalMessageToHost()` to control REAPER internally
- ReaScript uses Lua networking to send/receive custom OSC messages to nova-script
- Full flexibility: any action, any parameter, custom feedback

**Option C: Hybrid**
- Use REAPER's built-in OSC for standard track/FX control
- Use ReaScript for custom messages (display, mode switching, beat sync)

---

### 7. Code Changes Applied (this entry)

- **Launchpad MK1 `on_connect()`**: Replaced dummy `_enter_programmer_mode()` with actual `_kick_input_buffer()` that toggles all 8 automap LEDs (amber on/off) to force the MIDI input buffer to start delivering events. This is the known workaround for the PyGame/ALSA buffer bug.
- Removed unnecessary SysEx layout select (not supported on MK1)
- MidiManager does initial `_try_connect_device()` during `start()` for immediate connection

---

### 8. Open Questions Resolved
- ✅ **MIDI input receiving**: Not a port contention issue. Buffer bug with known workaround.
- ❓ **Clock master**: Still pending — REAPER can provide beat position via OSC `/beat`. Akai Force can provide MIDI clock.
- ❓ **Message display character set**: Still pending — need to design 8×8 pixel font for scrolling text.
- ✅ **Launchkey pad arrangement**: 2 rows × 8 cols. Confirmed note mappings for Basic and Extended modes.
- ✅ **Launchkey LED colors**: Fixed 128-color palette via velocity, not direct RGB. Flashing on Ch2, pulsing on Ch3.
- ✅ **REAPER OSC**: Full API documented. `.ReaperOSC` pattern file format confirmed.

### Files Changed
- `src/controllers/launchpad_mk1.py` — Added `_kick_input_buffer()`, removed unused SysEx, added logging
- `BUILD_LOG.md` — This entry

### Next Actions
1. Test Launchpad input with automap kick workaround
2. ~~Build ReaperOSC config file bridge~~ → Done in Entry #4
3. ~~Implement OSC server/client in nova-script (`src/osc/`)~~ → Done in Entry #4
4. ~~Fix Launchkey 49 MK2 controller~~ → Done in Entry #4
5. ~~Build Message Display Mode~~ → Done in Entry #4
6. Add MIDI clock sync options (internal/OSC/MIDI)

---

## Entry #4 — 2026-08-03 — OSC Bridge, Launchkey Protocol Fix, Message Display Mode

### Source
Daniel via Claude Code. Continuation of build after research session.

### Changes Made

- **MidiManager multi-port support** (`src/midi/manager.py`): Extended to handle devices with multiple MIDI port pairs (e.g., Launchkey's MIDI + InControl ports).
  - `DeviceConnection` now has `extra_inputs` and `extra_outputs` dicts for secondary ports
  - `register_device()` accepts `extra_input_patterns` and `extra_output_patterns` (dict of label → name-pattern)
  - `send_message()` accepts `target` parameter to route to specific port (e.g., `target="incontrol"`)
  - Connection lifecycle tracks both primary and secondary port readiness
  - `_on_connect` callback fires only when ALL ports are connected
  - Health check and auto-reconnect cover all ports

- **Launchkey 49 MK2 rewrite** (`src/controllers/launchkey_mk2.py`): Complete rewrite using protocol from Entry #3 research.
  - LED commands send to InControl port via `target="incontrol"`
  - Extended mode auto-activated on connect: `9F 0C 7F`
  - Pad notes switch to Extended mapping (112-119 + 96-103) in Extended mode
  - LED palette: 28 colors via velocity lookup (`LK_COLOR_PALETTE`)
  - `send_led_flash()` on Channel 2, `send_led_pulse()` on Channel 3
  - Knobs: CC 21-28, Faders: CC 41-48 (+ Master on CC 7)
  - Transport: CC 112-117 + track left/right on CC 102-103
  - Mute/Solo button on CC 51
  - `enter_incontrol_pads/pots/sliders()` methods for per-section InControl mode
  - `reset_leds()` via `BF 00 00`

- **OSC Bridge** (`src/osc/bridge.py`, `src/osc/namespace.py`):
  - `OscBridge` class: manages bidirectional OSC communication with REAPER
  - Server: `AsyncIOOSCUDPServer` listening on configurable port (default 9001)
  - Client: `SimpleUDPClient` sending to REAPER (default port 8000)
  - Dispatcher maps all incoming patterns from `INCOMING_ADDRESS` namespace
  - Dedicated send methods: `send_track_volume()`, `send_fx_param()`, `send_transport_play()`, etc.
  - Incoming message parsing into typed events: `display_message`, `mode_set`, `beat`, `play_state`, `track_vu`
  - Callback-based: engine receives parsed messages via `_on_osc_message()`
  - Graceful degradation if port is taken or REAPER isn't listening
  - Tested: receives `/nova/display/message` and `/nova/mode/set` via UDP

- **Message Display Mode** (`src/ui/modes/message.py`):
  - 5×5 pixel font for 47 characters (A-Z, 0-9, space, .,!?-/:'+#)
  - `FONT_5X5` character dictionary
  - Scrolling text across 8×8 grid at configurable speed (default 150ms/step)
  - `enqueue_message()`: queue system, messages display sequentially
  - `_render()`: renders current text with scroll offset, respecting grid boundaries
  - Auto-activation: triggers after `idle_timeout_ms` of no user input when messages queued
  - Auto-dismiss: any button press returns to previous mode
  - Tested: "HELLO WORLD" scrolls across Launchpad LEDs after OSC trigger

- **Engine updates** (`src/engine.py`):
  - Registers Launchkey with `extra_input_patterns` and `extra_output_patterns` for InControl
  - Creates and starts `OscBridge` during startup
  - Registers Message mode
  - `_on_osc_message()` routes display messages, mode changes, beat/VU events
  - `_enqueue_display_message()` queues messages for display
  - `_check_idle_message()` auto-activates message mode when idle + messages queued
  - `_dismiss_message()` returns to previous mode on user input
  - Button events during message mode dismiss the message
  - Event loop handles new 4-tuple MIDI format (device, message, timestamp, port_key)
  - OSC port defaults: listen=9001, reaper=8000 (avoiding port 9000 conflict)

- **Config updated** (`config/default.yaml`): OSC listen port changed to 9001

### Files Changed
- `src/midi/manager.py` — Added multi-port support with extra_inputs/extra_outputs
- `src/controllers/launchkey_mk2.py` — Complete rewrite with InControl, Extended mode, palette LEDs
- `src/osc/__init__.py` — Exists (empty)
- `src/osc/namespace.py` — New: OSC address space definitions
- `src/osc/bridge.py` — New: bidirectional OSC bridge to REAPER
- `src/ui/modes/message.py` — New: scrolling text display mode with 5×5 font
- `src/engine.py` — Updated: OSC bridge, Launchkey reg, message mode, idle dispatch
- `config/default.yaml` — Updated OSC ports

### Known Issues
- OSC server port 9001 confirmed working. Port 9000 was taken (likely by REAPER or Live Show Manager).
- Launchkey 49 MK2 not currently plugged in — controller code ready, will activate when connected.
- `SimpleUDPClient` is blocking (runs in main asyncio loop). Fine for now since sends are fast. Can upgrade to async UDP client if needed.

### Next Actions
1. Test Launchpad input with automap kick workaround (press some buttons!)
2. Build ReaperOSC config file for nova-script namespace
3. Add MIDI clock sync from external sources
4. Build Performance/Clip Launch mode (Ableton-style session view)
5. Add velocity sensitivity support for Launchkey pads
6. Test full Reaper ↔ nova-script OSC round-trip with actual Reaper

---

## Entry #5 — 2026-08-03 — Deep Sanity Checks, Edge Case Audit, Test Harness

### Source
Daniel via Claude Code. Pre-testing audit and preparation for step-by-step hardware testing.

### Audit Results — All Passing

#### LED Coordinate Mapping
- Grid mapping `(x,y) → note = (7-y)*16 + x` verified for all 4 corners + center
- Inverse mapping `note → (x,y) = (note%16, 7 - note//16)` verified
- No collisions between grid notes and right-column notes (notes 8,24,40,56,72,88,104,120 all map to x≥8, caught by bounds check)
- Pads beyond grid bounds (x>7 or y>7) correctly rejected
- Top row CC range 0x68-0x6F (104-111) correct for 8 buttons
- Right column notes [8,24,40,56,72,88,104,120] correct for 8 buttons

#### Color Mapping
- All 10 required LogicalColor values present in MK1_COLOR_MAP
- All velocity values in valid range (0-127)
- Formula `velocity = (green << 4) | red` verified:
  - OFF=0, RED_HIGH=3, GREEN_HIGH=48, AMBER_LOW=17, AMBER_HIGH=51
- `brightness()` and `base_color()` helper methods working

#### Button Input Parsing
- Grid presses: all 4 corners + center correctly parse to GridEvent with correct (x,y)
- Note On vel=127 → GRID_PRESS, vel=0 → GRID_RELEASE
- Top row (automap): CC 104-111 → control_id 200-207, FUNCTION_PRESS/RELEASE
- Right column: notes 8,24,40,56,72,88,104,120 → control_id 100-107
- Edge cases correctly ignored: out-of-range note 127, unknown CC 50, Note Off (0x80)
- Note: Controller uses "Note On vel=0" convention for release. Raw Note Off (0x80) messages are ignored.

#### Grid & Rendering
- All 47 font glyphs verified 5×5 dimensions
- LogicalGrid bounds checking: out-of-range set_cell() silently ignored
- fill_rect, fill_row, fill_column all working with correct bounds
- draw_bar_vertical: 0.5 value on 8-row bar → 4 filled cells (correct)
- Dirty cell tracking: clear fills 64 dirty cells, second call returns 0

#### Auto-Reconnect Flow Trace
- **Disconnect detection:** `_check_connection_health()` compares port names against current port list every 500ms. Port name mismatch triggers `_disconnect_device()`.
- **Graceful teardown:** Cancels callbacks, closes all ports (including extras for multi-port devices), resets connection flags.
- **Reconnect:** `_try_connect_device()` scans ports by name pattern, opens fresh `MidiIn`/`MidiOut` with new index. `_on_connect_fired` flag prevents duplicate callbacks.
- **State restoration:** Engine's `_on_device_connect` calls `controller.on_connect()` (resets + kicks input buffer) then `mode.enter()` (re-renders current mode).
- **Thread safety:** rtmidi callbacks run in separate thread, push to asyncio.Queue. Engine's event loop reads from queue. No shared mutable state between threads.
- **Port index changes handled:** Port discovery uses name matching, not index. Index shift on replug is transparent.

#### Message Display Edge Cases
- Empty messages silently dropped (`if not text: return`)
- Queue overflow: max 16 messages, oldest dropped when full
- Auto-dismiss: any button press in message mode returns to previous mode
- Auto-activation: only when `_current_text` is non-empty AND idle time > timeout
- Mode already "message": `_check_idle_message` returns early (no double-activation)
- Font unknown chars → fallback to "?" glyph

#### New Safeguards Added
- `MessageMode._max_queue_size = 16`: prevents infinite queue growth from OSC spam
- `enqueue_message()`: drops oldest message when queue full

### Test Harness (`scripts/test_harness.py`)

Created interactive test harness for step-by-step hardware testing. Features:

**Grid LED tests:**
- `h.set_led(x, y, 'color')` — Light individual pad
- `h.clear()` — Clear all
- `h.fill('color')` — Fill entire grid
- `h.cross('color')` — X pattern
- `h.border('color')` — Border pattern
- `h.smiley()` — Smiley face
- `h.heart()` — Heart pattern
- `h.cycle_colors(x, y, delay, loops)` — Cycle through colors on a pad

**Circular button LED tests:**
- `h.set_top_led(idx, 'color')` — Light top row button
- `h.set_right_led(idx, 'color')` — Light right column button
- `h.all_outer('color')` — Light all outer buttons
- `h.chase_top(delay, loops)` — Chase animation on top row
- `h.chase_right(delay, loops)` — Chase animation on right column
- `h.chase_grid(delay, loops)` — Chase animation on grid border

**Button input test:**
- `await h.check_buttons(timeout)` — Monitor and print button presses
- Intercepts controller callbacks, prints event details
- Background dispatch loop processes MIDI events from rtmidi callback thread

**Architecture:**
- Opens MIDI port, starts MidiManager with auto-reconnect
- Background asyncio task drains MIDI event queue → dispatches to controller
- Test commands execute synchronously (LED output is immediate)
- Async commands (check_buttons) use `await` in REPL

### Test Plan (next session)

Following the user's specified testing order:

1. **"Turn LED row 1 col 1 green"** → `h.set_led(0, 0, "GREEN_HIGH")` (bottom-left pad lit green)
2. **Cycle green, red, orange** → `h.cycle_colors(0, 0, 0.5, 2)` (pad cycles through all 3 colors)
3. **Chasing lights on outer circular buttons** → `h.chase_top(0.1, 3)` then `h.chase_right(0.1, 3)`
4. **Graphics** → `h.smiley()`, `h.heart()`, `h.cross("AMBER_HIGH")`, `h.border("GREEN_HIGH")`
5. **Scrolling text** → OSC trigger `/nova/display/message` via engine or direct
6. **Button presses** → `await h.check_buttons(5)` → press Launchpad pads, verify (x,y) output

### Files Changed
- `src/ui/modes/message.py` — Added max queue size (16), overflow protection
- `scripts/test_harness.py` — New: interactive test harness
- `BUILD_LOG.md` — This entry

### Next Actions
1. **Test with Daniel** following the plan above
2. After LED tests pass: fix button input if automap kick doesn't work
3. After input works: build real UI modes page by page
4. Git commit after each successful test milestone

---

## Entry #6 — 2026-08-03 — Input Diagnosis & Resolution

### Source
Daniel via Claude Code. Extensive debugging to resolve Launchpad Mini MK1 MIDI input not working.

### Problem
LED output worked perfectly from day one. MIDI input (button presses) produced zero events across all tests. 51 million poll iterations returned nothing. The research confirmed the Launchpad doesn't need drivers or SysEx init on macOS.

### Root Causes (two factors)

**Factor 1: Cascaded USB hubs.** The Launchpad was behind 3 chained USB hubs (USB3.2 → USB2.1 → USB2.1). USB MIDI input uses interrupt IN endpoints which are sensitive to transaction translator timing across cascaded hubs, especially on Apple Silicon. Output uses bulk/control transfers which tolerate this — explaining the one-way behavior.

**Factor 2: No button presses during monitoring windows.** The earlier tests ran for 5-20 seconds, and buttons were not being pressed during those windows, so zero events was the correct result for those runs.

**Resolution:** Plugged Launchpad directly via USB-C to A adapter (single hop). Button events immediately started flowing — 86 events in 30 seconds on raw rtmidi test, 12 events in 15 seconds through our full parsing pipeline. All grid coordinates verified against expected mapping.

### Confirmed Working
- Grid button press → Note On (0x90, note, 127) → parsed to GridEvent(x, y, pressed=True)
- Grid button release → Note On (0x90, note, 0) → parsed to GridEvent(x, y, pressed=False)
- 16 distinct note values (17-68) all mapped to correct (x,y) via formula x=note%16, y=7-(note//16)
- Note mapping: row 0(0-7), row 1(16-23), row 2(32-39), row 3(48-55), row 4(64-71), row 5(80-87), row 6(96-103), row 7(112-119)

### USB Device Tree
```
Launchpad Mini (vendor 0x1235, product 0x0036, USB 1.1 Full Speed)
├── Interface @0: Audio Control (class 1, subclass 1, 0 endpoints)
└── Interface @1: MIDI Streaming (class 1, subclass 3, 2 endpoints, MIDIServer exclusive)
```

### Next Actions
1. Test circular buttons (top row + right column) with button monitor
2. Build fuller UI mode interactions using button input
3. Build Performance/Clip Launch mode
4. Test auto-reconnect with cable bump
5. Later: test with cascaded hub to isolate true root cause





---

## Entry #7 — 2026-08-03 — Performance Mode, Long-Press Detection, ReaperOSC Config

### Changes Made

- **Circular Button Verification:** All 16 outer buttons tested. Top row (numbered 1-8): CC 104-111 → control_id 200-207 ✓. Right column (lettered): notes 8,24,40,56,72,88,104,120 → control_id 100-107 ✓.

- **Performance Mode** (`src/ui/modes/performance.py`): Ableton-style session clip launcher. 8 tracks × 8 scenes. Clip states: EMPTY/STOPPED/PLAYING/RECORDING/QUEUED. Short press = launch/stop, long press (500ms) = clear clip. Scene launch via right column, track stop via top row. Sends MIDI note + OSC /nova/clip/launch and /nova/clip/stop.

- **Long-Press Detection** (`src/ui/mode.py`): Added to Mode base class. track_press()/resolve_press() returns "short"/"long"/"invalid". Configurable 500ms long-press, 80ms debounce. Available to all modes.

- **ReaperOSC Config** (`config/nova-script.ReaperOSC`): Pattern file for REAPER. Full track/FX/send/transport mapping. VU + beat position feedback. Install to ~/Library/Application Support/REAPER/OSC/

### Files Changed
- src/ui/mode.py — Long-press detection
- src/ui/modes/performance.py — New
- src/engine.py — Performance mode registration
- config/nova-script.ReaperOSC — New
- BUILD_LOG.md — Entries #6 + #7

### Next Actions
1. Test Performance mode with button input on hardware
2. Build Device/FX control mode
3. Add MIDI clock sync
4. Test auto-reconnect

---

## Entry #8 — 2026-08-03 — Comparative Research: Existing Projects & Lessons Learned

### Source
Daniel via Claude Code. Research across 15+ open-source projects to learn from what exists.

### Key Findings

**Confirmed our architecture is correct:**
- python-rtmidi (not PyGame) — verified by dhilowitz fork that explicitly migrated away from pygame.midi
- Textual TUI — no better alternative found
- python-osc (attwad) — 580 stars, zero deps, asyncio, the standard
- Layered architecture (controllers → modes → protocol bridge) — no one else does this
- LogicalColor abstraction — maps to both MK1 2-bit and MK3 palette
- Long-press detection in base class — no library has this built in

**Unique value we're creating (gaps no one fills):**
1. No LED grid UI widget framework exists — our Mode system is the closest
2. No standalone session view / clip launcher — our Performance mode fills this
3. No multi-device Novation abstraction — our NovationController base + DeviceCapabilities
4. No Launchpad→Reaper OSC bridge — our OscBridge is this

**Best project to study:** Launchpad95 (400 stars) — the gold standard for Launchpad UX. Mode switching, scale quantization, step sequencer UI, device parameter mapping.

**New ideas discovered:**
- MK1 supports double buffering for flicker-free LED updates (beryxz finding)
- MK1 supports hardware flashing/duty cycle natively
- Canvas/Pixel API with shape drawing (circles, lines, rects)
- Image→grid rendering (GIF/PNG → 8×8 LED)
- Separate OSC command/feedback channels
- MIDI learn pattern for hardware parameter mapping
- Web-based config editor

**Pitfalls to avoid (all confirmed our choices):**
- PyGame MIDI — dead on Apple Silicon
- Poll-only input — we have event system
- Hardcoded per-device — we have abstraction layer
- time.sleep() — we use asyncio + delta time

Full analysis in `docs/REFERENCE_PROJECTS.md`.

### Files Changed
- `docs/REFERENCE_PROJECTS.md` — New: comprehensive research document
- `BUILD_LOG.md` — This entry

---

## Entry #9 — 2026-08-04 — Combo Detection, Fireworks Particle System, Virtualizer Test Harness

### Source
Daniel via Claude Code. Feature spec implementation begins.

### Features & Specs Document
Created `docs/FEATURES_AND_SPECS.md` — comprehensive UX design covering:
- Startup flow with color wave animation
- Golden rules: Home button (Top-1), Overlay dismiss, Manual overrides (Top-1+2, Top-1+3)
- Overlay priority system (Fireworks > HUD > Screensaver > Active Mode)
- Menu mode refined layout with mode colors
- Per-mode button mappings (Sequencer, Mixer, Performance)
- Screensaver image system (64 images, 8 quick slots, picker interaction, BPM cycling, persistence)
- Fireworks system (BPM-synced particles, 8-bar duration, gravity+trail, dismissible)
- HUD system (text/char/image via OSC, temporary overlay)
- TUI redesign with grid mirror, mode info, event log, image preview
- Complete risk register with build order

### Combo Detection — Risk #1: RESOLVED
Created `ComboDetector` with full unit test suite (7 scenarios). Logic:
- Top-1 press is held (not immediately acted on) — returns "consumed"
- If Top-2 or Top-3 arrives within 250ms while Top-1 held → combo fires
- If Top-1 released without combo partner → returns "home"
- If combo window timeout expires → returns "home"
- After combo fires, subsequent releases of combo buttons return "consumed" (suppressed)
- `_combo_fired` flag prevents double-firing

All 7 unit test scenarios pass. Hardware verification: top row buttons confirmed (id=200-205), but two-finger simultaneous hold not yet tested on device due to remote testing constraints.

### Fireworks Particle System — Risk #2: IN PROGRESS
Implemented `Fireworks` particle system:
- Particles spawn in bursts (3-6 per beat) from bottom of grid
- Rise with random velocity (8-15 units/s), gravity pulls back (-12 units/s²)
- Colors cycle per beat: red → amber → green
- Variable brightness based on remaining lifetime
- Trail system: 1-step fading trail behind each particle
- Auto-cleanup when done (trails cleared, grid restored)
- Unit test: simulates 200 frames at 240 BPM, verifies all particles clear
- Smooth 20fps rendering with no frame drops

One bug found and fixed: trails weren't fully cleared after fireworks end.
Added explicit `_trail.clear()` when `tick()` returns False.

### Virtualizer Test Harness (`tests/virtualizer.py`)
Designing a virtual hardware emulator for comprehensive testing:
- Injects simulated MIDI events directly into controller callbacks
- ASCII grid rendering maps LogicalColor to distinct characters:
  OFF→·  RED→r/R/#  GREEN→g/G/$  AMBER→a/A/@  (low/med/high)
- Supports short press, long press, press+release pairs
- Captures all MIDI output messages for verification
- Works with both Launchpad MK1 and Launchkey MK2 controllers
- Enables full input→output pipeline testing without physical hardware

### Files Changed
- `docs/FEATURES_AND_SPECS.md` — New: complete UX specification
- `tests/test_combo_detector.py` — New: 7-scenario unit test (all passing)
- `tests/test_combo_hardware.py` — New: hardware integration test
- `tests/test_fireworks.py` — New: particle system with unit tests
- `BUILD_LOG.md` — Entries #8 + #9

### Next Actions
1. Complete virtualizer test harness
2. Fix fireworks render cleanup (trail persistence)
3. Build image storage + load/save
4. Build overlay dismiss/restore flow
5. Build startup wave animation

---

## Entry #10 — 2026-08-04 — Startup Wave, Image Store, Overlay System (all tested via virtualizer)

### Changes Made

- **Startup Wave** (`src/ui/startup_wave.py`): Diagonal color ripple animation.
  Amber wave from bottom-left to top-right, green follows, red follows.
  73 frames simulated, max 64 cells lit at peak. Clean grid at end.
  Tested via virtualizer: all 8×8 cells lit by wave, verified clean exit.

- **Image Store** (`src/ui/image_store.py`): 64-image persistence system.
  YAML format: name + 8×8 LogicalColor grid per image.
  8 default images: waves, heart, checker, xmarks, diamond, all_amber/red/green.
  8 quick-access slots mapped to top-row buttons. Persistent across restarts.
  `render_to_grid()` writes image directly to LogicalGrid.
  Store/retrieve round-trip verified. Quick slot persistence verified.
  Temp file test: clean create, save, reload, tear down.

- **Overlay Manager** (`src/ui/overlay_manager.py`): Priority-based overlay stack.
  Priorities: Fireworks(4) > HUD(3) > Screensaver(2) > ActiveMode(1).
  Two-press dismiss: first press consumed, second press passes to mode.
  Fireworks → auto-transition to screensaver on completion.
  HUD → auto-dismiss to previous state (screensaver or mode).
  Idle timeout → auto-enter screensaver.
  Screensaver BPM cycling support, image switching via `_render_screensaver_image()`.
  
  5 integration tests all passing via virtualizer:
  1. Startup wave: 73 frames, max 64 lit, clean exit
  2. Idle → screensaver → dismiss: timeout works, two-press flow correct
  3. Fireworks → screensaver: 173 frames, auto-transition verified
  4. HUD overlay: character 'G' renders correctly, auto-dismiss to screensaver
  5. Screensaver image pick: heart/checker render, quick slot persistence

### Risk Resolution Status
| Risk | Status |
|------|--------|
| Multi-button combos | RESOLVED (7 unit tests passing) |
| Fireworks particle system | RESOLVED (200-frame simulation, clean exit) |
| Image storage format | RESOLVED (YAML, 8 defaults, persistence) |
| Overlay dismiss flow | RESOLVED (5 integration tests, 2-press dismiss) |
| Startup wave | RESOLVED (virtualizer test, 73 frames) |
| Screensaver picker | RESOLVED (image switching, quick slots) |

### Files Changed
- `src/ui/startup_wave.py` — New: diagonal color wave boot animation
- `src/ui/image_store.py` — New: 64-image YAML persistence with 8 defaults
- `src/ui/overlay_manager.py` — New: priority overlay system
- `tests/test_overlay_system.py` — New: 5-scenario integration test (all passing)

### Next Actions
1. Wire overlay system into Engine
2. Integrate ComboDetector with Engine for manual triggers
3. Rebuild TUI with new spec layout
4. Test with physical hardware when Launchpad reconnected
5. Build effects/device control modes

---

## Entry #12 — 2026-08-04 — Profile System, CLI, Engine Integration, TUI Rebuild

### Source
Daniel via Claude Code. Final integration session.

### Summary
All major systems integrated into a unified engine. CLI entry point working. TUI rebuilt with profile management and settings. All 6 initial risks resolved. The system boots from `nova-script` command, plays startup wave, enters menu mode, and awaits interaction — with screensaver activation on idle timeout.

### Changes Made

#### CLI & Profile System
- **ProfileManager** (`src/profiles.py`): Load/save/list/export/import YAML profiles from `config/profiles/`. Deep-merges with `config/default.yaml` for fallback values. Default `live-show` profile auto-created on first run.
- **CLI** (`src/main.py`): Full command-line interface.
  - `nova-script [profile]` — launch with named profile
  - `nova-script --tui [profile]` — launch with visual TUI
  - `nova-script list` — show available profiles
  - `nova-script save/export/import` — profile management
  - Installed as pip entry point
- **live-show profile** (`config/profiles/live-show.yaml`): Default music performance profile with 5 modes, 30s idle timeout, 120 BPM, screensaver config.

#### Engine Integration
- **OverlayManager** wired into Engine: idle→screensaver, fireworks, HUD overlays. Two-press dismiss flow (first press consumed, second passes to mode).
- **ComboDetector** wired into Engine: Top-1+2 = screensaver, Top-1+3 = fireworks, Top-1 alone = home (back to menu).
- **StartupWave** plays on boot: amber→green→red diagonal ripple across 8×8 grid.
- **ImageStore** loaded at startup: 8 default images, persisted to YAML.
- **Control flow:** Button events → ComboDetector → OverlayManager → Mode handlers. Grid events → OverlayManager → Mode handlers.
- Old `_idle_since` and `_check_idle_message` removed — overlay system replaces them.
- `_on_osc_message` routes display messages to Overlay HUD instead of old message mode.

#### Refactored Components
- **ComboDetector** moved from `tests/` to `src/ui/combo_detector.py` — production-ready module.
- **Fireworks** moved from `tests/` to `src/ui/fireworks.py` — production-ready particle system.
- Test files updated to import from `src/ui/` as source of truth.

#### TUI Rebuilt (`src/tui/app.py`)
- Device connection status bar: LP/LK/OSC status with ✓/✗ indicators
- Profile management screen (press P): list all profiles, load/save
- Settings screen (press S): placeholder for future config options
- Event log panel: last 50 events with timestamps
- Live 8×8 grid mirror (existing, retained)
- Keyboard shortcuts: Q=Quit, P=Profiles, S=Settings

#### Features & Specs Updated
- `docs/FEATURES_AND_SPECS.md`: Added full profile system design (CLI, storage, import/export, content format, app-aware profiles for future).

### Architecture at Present

```
nova-script [profile] or nova-script --tui [profile]
         │
         ▼
    main.py (CLI)
         │
         ▼
    ProfileManager.load(profile_name)
         │
         ▼
    Engine(config)
         ├── MidiManager (port discovery, auto-reconnect)
         │    ├── LaunchpadMiniMK1
         │    └── Launchkey49MK2
         ├── OscBridge (bidirectional REAPER OSC)
         ├── ImageStore (64-image persistence)
         ├── ComboDetector (multi-button combos)
         ├── OverlayManager (priority stack)
         │    ├── Fireworks (BPM particles)
         │    ├── HUD (text/char display)
         │    └── Screensaver (image cycling)
         ├── StartupWave (boot animation)
         ├── ModeManager
         │    ├── Menu
         │    ├── Sequencer
         │    ├── Mixer
         │    ├── Performance
         │    └── Message
         └── TUI (optional, separate thread)
              ├── Grid mirror
              ├── Profile manager
              ├── Settings
              └── Event log
```

### Test Status
| System | Status | Method |
|--------|--------|--------|
| LED output | ✓ | Hardware, all colors |
| Grid button input | ✓ | Hardware, correct coordinates |
| Top row buttons | ✓ | Hardware, correct IDs |
| Right column buttons | ✓ | Hardware, correct IDs |
| Combo detection | ✓ | 7 unit tests |
| Fireworks | ✓ | 200-frame simulation |
| Image store | ✓ | Round-trip + persistence |
| Overlay dismiss | ✓ | 5 integration tests (virtualizer) |
| Startup wave | ✓ | Virtualizer, 73 frames |
| Engine + overlay | ✓ | Clean startup/shutdown |
| CLI | ✓ | nova-script list, load |
| TUI imports | ✓ | Clean import, no errors |

### Files Changed (this session)
- `src/profiles.py` — New: profile manager
- `src/ui/combo_detector.py` — Moved from tests/
- `src/ui/fireworks.py` — Moved from tests/
- `src/ui/overlay_manager.py` — New: priority overlay system
- `src/ui/startup_wave.py` — New: boot animation
- `src/ui/image_store.py` — New: image persistence
- `src/main.py` — Rewritten: CLI with profile support
- `src/engine.py` — Rewired: overlay, combo, wave integration
- `src/tui/app.py` — Rebuilt: profiles, settings, device status
- `config/profiles/live-show.yaml` — New: default profile
- `config/screensaver-images.yaml` — New: 8 default images
- `docs/FEATURES_AND_SPECS.md` — Updated with profile system
- `BUILD_LOG.md` — Entries #9-#12

### Next Actions
1. Test TUI with `nova-script --tui` on hardware
2. Build Effects/Device control modes
3. Add MIDI clock sync (OSC beat position, MIDI clock)
4. Test auto-reconnect with cable bump
5. Build ReaperOSC → Reaper bridge test
6. Future: TUI profile builder (drag-and-drop mode layouts)

---

## Entry #13 — 2026-08-04 — BPM Clock System + Settings UI

### Changes Made

- **BPMClock** (`src/midi/clock.py`): Multi-source tempo sync with configurable priority.
  Sources: "Reaper (OSC)" (OSC /beat), any MIDI port name (MIDI clock 0xF8), "Internal".
  Configurable preferred/fallback hierarchy. Auto-detects active sources.
  Respects preferred source — if Reaper OSC is active, ignores MIDI clock.
  Internal clock always available as ultimate fallback.

- **Top-1 LED BPM Blink:** Button 1 blinks at BPM tempo on ALL pages.
  Orange when on Menu (home), green when on any other mode.
  80ms LED-on flash per beat, then off. Color reflects "press to go somewhere" semantics.

- **Settings Screen** (TUI): Built out with dynamic MIDI port discovery.
  Shows "Reaper (OSC)", "Internal", and all detected MIDI input ports.
  Preferred/fallback source selection. Internal BPM + idle timeout display.
  Save & Close button. Accessible via S key in TUI.

### Design Decision: Clock Source Naming
After researching, the correct approach:
- "Reaper (OSC)" — special entry for OSC beat sync (Reaper sends /beat over UDP)
- Any MIDI port name — MIDI clock (0xF8, 24 per quarter note) from USB MIDI
- "Internal" — software timer fallback

This is cleaner than naming by device function because:
1. Devices expose MIDI ports by name, not by brand
2. The user sees the actual port names they recognize
3. Works regardless of what hardware is connected
4. Settings menu populates dynamically at runtime

### Files Changed
- `src/midi/clock.py` — New: multi-source BPM clock
- `src/engine.py` — BPMClock integration, beat callback, Top-1 LED blink
- `src/tui/app.py` — Settings screen with port discovery, config passing
- `src/main.py` — Pass config to TUI
- `config/profiles/live-show.yaml` — Updated clock config format
- `BUILD_LOG.md` — This entry

### Next Actions
1. Test BPM blink on hardware with Launchpad
2. Add MIDI clock message detection in event loop (0xF8 → clock.feed_midi_clock)
3. Build clock source selection UI in settings dropdown
4. Test with Reaper OSC /beat sync
5. Test with Akai Force MIDI clock sync

---

## Entry #14 — 2026-08-04 — Chill Mode + Default Launch Behavior

### Changes Made

- **Chill Mode** (`src/ui/chill_mode.py`): Ambient LED patterns for standby display.
  5 patterns that auto-cycle every 25-35 seconds with smooth transitions:
  - **Wave** (30s): Horizontal amber wave sweeping side to side with fading edges
  - **Breathe** (25s): All pads pulse in unison — slow sine-wave brightness breathing
  - **Starfield** (35s): 10 scattered dim lights fading in/out independently
  - **Rain** (25s): 6 gentle falling droplets with trailing fade
  - **Gradient** (30s): Diagonal color gradient that slowly rotates
  Colors are amber/red/green at low brightness — never harsh or flashing.
  Inspired by keyboard backlighting effects.

- **CLI update** (`src/main.py`): `nova-script` with no arguments now enters chill mode
  instead of loading live-show profile. Explicit profile name still works:
  `nova-script live-show` → full engine. Default behavior is now ambient lighting.

### How it works
1. `nova-script` → connects to Launchpad only → runs chill patterns
2. Patterns cycle automatically, ~30s each, with smooth transitions
3. Ctrl+C to exit, Launchpad clears
4. No OSC, no button handling, no profiles — just ambient LED art

### Files Changed
- `src/ui/chill_mode.py` — New: ambient pattern engine
- `src/main.py` — No-args now runs chill mode
- `tests/test_chill_mode.py` — New: virtualizer pattern verification
- `BUILD_LOG.md` — This entry

### Next Actions
- Add more chill patterns over time
- Make pattern selection configurable
- Allow transition between chill mode → full engine on button press

---

## Entry #15 — 2026-08-04 — Diagonal Chill Patterns, Chill TUI, Launchpad UX/UI Audit

### Changes Made

- **Diagonal chill patterns** — All 5 patterns rewritten for diagonal movement.
  Wave sweeps diagonally across the grid. Breathe pulses in diagonal bands.
  Starfield drifts diagonally. Rain falls diagonally with trailing droplets.
  Gradient rotates diagonally. All confirmed: 6-64 cells lit depending on pattern,
  multiple diagonal bands active simultaneously. No harsh vertical/horizontal lines.

- **Chill TUI** (`src/tui/chill_tui.py`): Minimal toggle interface for chill mode.
  Shows LED on/off status. Press L to toggle demo LEDs on/off. Press Q to quit.
  Single queue communication — TUI sends toggle action, engine responds.
  Launches alongside chill mode when `nova-script` runs without a profile.

- **ChillRunner updated** — Accepts optional tui_queue. `_check_tui()` reads
  toggle commands. When LEDs off: clears grid and sleeps. When toggled back on:
  resumes pattern cycling from current time. `_commit()` skips when LEDs off.

### Launchpad UX/UI Audit — What the User Sees

A comprehensive walkthrough of the entire Launchpad visual experience:

**1. Startup Wave (2 seconds)**
Status: ✓ Working. Diagonal amber→green→red ripple from bottom-left to top-right.
UX issue: None. Clear visual indicator that the system is alive and initializing.

**2. Menu Mode (landing state)**
Status: ✓ Working. 5 colored pads in a row on the grid.
UX issues:
- Pads are just colored squares — user must memorize which color = which mode
- No text/labels on the MK1 (no screen)
- Color scheme is intuitive: AMBER=sequencer (beats), GREEN=mixer (volume), RED=effects (processing), AMBER=performance (live), GREEN=device (control)
- Mitigation: top-row buttons also trigger modes. Button 2=Seq, 3=Mix, 4=Perf, 5=FX, 6=Dev

**3. Top-1 Home Button**
Status: ✓ Working. Amber at home, green elsewhere. Blinks at BPM.
UX: Discoverable but not obvious. The blink draws attention.
Improvement opportunity: blink twice on the first beat after startup to signal "clock is running."

**4. Mode Switching**
Status: ✓ Working. Instant switch — old mode LEDs clear, new mode renders.
UX issue: No visual transition. Abrupt change feels jarring.
Improvement: Brief fade or flash on the switched-to mode pad for 200ms.

**5. Overlay System (Screensaver / Fireworks / HUD)**
Status: ✓ Working. First press dismisses, second press acts.
UX issues:
- When in screensaver, the entire grid shows an image. There's no visual indicator
  that you're in an overlay vs. an active mode. Top-1 still blinks (good), but
  the grid itself looks like you're in some mode.
- HUD is temporary (1.5s) but covers the entire grid. The user can't see
  what was underneath. HUD should be an overlay on top of the current grid,
  not replace it entirely.
- Fireworks fill the grid with particles. After fireworks end, auto-screensaver.
  The transition might surprise the user if they didn't trigger fireworks manually.

**6. Screensaver Image System**
Status: ✓ Working. 64 images, 8 quick slots, image picker.
UX: Image picker interaction (hold Top-8 for 2s) is not discoverable.
Improvement: flash the top row buttons when in screensaver to hint at interaction.

**7. BPM Clock / Beat Indicator**
Status: ✓ Working. Top-1 blinks at BPM on all pages.
UX: Single blink point. Good enough for tempo reference.
Improvement: flash all 4 corners on the downbeat (beat 1 of each bar).

**8. Chill Mode (default launch)**
Status: ✓ Working. 5 diagonal patterns cycling 25-35s each.
UX: Beautiful. Smooth, low-brightness, diagonal movement.
Issues:
- No indication of which pattern is playing
- If user wants to switch to full engine from chill mode, they need to quit and restart
- LED toggle (L key) is only in TUI, not on Launchpad

**9. Visual Feedback on Button Press**
Status: Partially working. Mode pads respond but no press feedback.
UX issue: When user presses a grid pad, the pad should briefly flash brighter
to confirm the press was registered. Currently pads stay the same brightness.

### UX Priority Improvements (ranked)
1. **Press feedback** — flash pressed pad brighter for 100ms (simple, high impact)
2. **Mode switch transition** — 200ms fade to new mode (softens the jump)
3. **Screensaver indicator** — subtle border flash to show "this is screensaver"
4. **Downbeat flash** — all 4 corners flash on beat 1 of each bar
5. **Chill→Engine transition** — pressing any button in chill mode launches engine
6. **Pattern name display** — briefly show pattern name on grid during chill mode

### Files Changed
- `src/ui/chill_mode.py` — All 5 patterns diagonal, ChillRunner toggle support
- `src/tui/chill_tui.py` — New: minimal chill mode TUI with LED toggle
- `src/main.py` — Chill mode with optional TUI
- `tests/test_chill_mode.py` — Updated virtualizer validation
- `BUILD_LOG.md` — This entry

### Next Actions
1. Implement press feedback (flash pad on press)
2. Add mode switch transition animation
3. Add downbeat flash on beat 1
4. Allow chill → engine transition via button press
5. Add pattern name display during chill mode cycling

---

## Entry #16 — 2026-08-04 — Downbeat UX: 3-mode tempo LED system

Refined Top-1 LED behavior with 3 configurable modes:

**"Tempo LED (beat 1 distinct)"** — Beat 1 flashes the configured downbeat
color (e.g. GREEN_HIGH), beats 2-4 flash the normal tempo color (AMBER at
home, GREEN elsewhere). Single LED communicates both tempo and bar position.

**"4 corners flash"** — Same Top-1 behavior as above, PLUS all 4 corners
flash the downbeat color on beat 1 of each bar. Stronger visual pulse.

**"Disable"** — Top-1 blinks normal tempo color on ALL beats equally.
No downbeat differentiation. Clean if you don't need bar position.

Engine: _set_home_led() now accepts optional color override. _on_beat()
branches per mode, tracks downbeat via beat_count % 4 == 1.
Settings screen: Select with all 3 options, saves to profile.

### Files Changed
- src/engine.py — 3-mode downbeat logic, _get_downbeat_color() helper
- src/tui/app.py — Added "Disable" option to downbeat Select
- BUILD_LOG.md — This entry

---

## Entry #17 — 2026-08-04 — Performance Mode: Tracks, FX Toggles, Strobe Tuner

### Changes Made

- **Performance Mode rewritten** (`src/ui/modes/performance.py`): Track mute + FX control.
  - Top row buttons (1-8): track mute toggles with configurable aliases
  - Right column (1-5): FX toggles — Rev, Dly, Chor, Hrm↑, Hrm↓
  - Grid: visual state — mute indicators (row 7), FX state (rows 1-5)
  - FX colors: RED = disabled, GREEN = enabled
  - Time-based FX (Delay, Chorus): pulse between GREEN_HIGH/GREEN_MED at BPM
  - Active track indicator: dim green border, others dim amber
  - 8 tracks configured: Vox, GTR, Bass, Track4-8

- **Tuner Mode:** Hold GTR mute button → strobe tuner activates on 8×8 grid.
  Dismisses on any button press, returns to performance view.
  Sine-wave strobe pattern visually indicates tuning state.
  OSC `/track/{n}/mute` sent on mute toggle.

- **Engine integration:** Performance mode gets BPM from clock system via `set_bpm()`.
  Config passed from profile's `performance` section.

- **Profile defaults:** 8 tracks with aliases (Vox, GTR, Bass...), 5 FX slots each
  with OSC addresses for bypass control. All configurable in TUI.

### Virtualizer Verified
- FX toggles: Vox Rev ON → GREEN, GTR Dly ON → GREEN pulsing at BPM
- Tuner: GTR mute hold → strobe on full 8×8, dismiss→return to performance
- Active track: GREEN_LOW indicator at bottom row

### Files Changed
- `src/ui/modes/performance.py` — Complete rewrite
- `src/engine.py` — Config pass-through + BPM sync
- `config/profiles/live-show.yaml` — Performance + mixer channel aliases
- `BUILD_LOG.md` — This entry

---

## Entry #18 — 2026-08-04 — Page Navigation, Performance Page 2, Pad Manual

### Changes Made

- **Page System** (`src/ui/mode.py`): Right column buttons (A-H) as page indicators.
  `render_pages()` lights amber for each available page, green for current.
  `_page` and `_num_pages` fields on Mode base class. `clear_pages()` helper.
  Bottom button H = page 1, G = page 2, etc. All modes get this for free.

- **Performance Page 2** (`src/ui/modes/performance.py`): 2-page layout.
  Page 1: mute + core FX (unchanged). Page 2: Extended FX (placeholder).
  Right column navigation: H=page1, G=page2. Press to switch pages.
  `_render_extended_fx()` shows amber placeholder block.

- **Pad Navigation Manual** (`docs/PAD-NAVIGATION-MANUAL.md`):
  Complete guide to every button, mode, and interaction. Covers:
  Universal controls, mode shortcuts, overlay rules, Menu mode layout,
  Performance mode (both pages), Clip Launcher (including edit mode),
  Sequencer, Mixer, BPM clock, visual hints, screensaver, fireworks,
  HUD, TUI companion, and settings reference.

### Files Changed
- `src/ui/mode.py` — Page system (render_pages, clear_pages, _page, _num_pages)
- `src/ui/modes/performance.py` — 2-page layout, page navigation, Extended FX placeholder
- `docs/PAD-NAVIGATION-MANUAL.md` — New: complete pad navigation manual
- `BUILD_LOG.md` — This entry

## Entry #19 — 2026-08-04 — LED Grid Editor Tool

### Purpose
Visual editor for creating custom Launchpad grid images. Replaces hand-editing YAML grids in `config/screensaver-images.yaml`. Designed for the nova-script screensaver/fireworks image system.

### Features
- **Grid sizing**: 1x1 to 32x32, resizable via input controls
- **G/R/O mode**: Click cycles OFF -> GREEN_HIGH -> RED_HIGH -> AMBER_HIGH. Fast, one-click editing for Launchpad MK1's native color palette
- **RGB mode**: Click opens color picker with all 28 LogicalColor values (9 colors x 3 brightness + OFF). Custom RGB input for arbitrary hex colors
- **Image overlay**: Upload a reference image (PNG/JPG/etc) that overlays the grid with adjustable opacity. Used for tracing/templating
- **Export**: Generates YAML in `screensaver-images.yaml` format (`'OFF'`, `RED_HIGH`, `AMBER_MED`, etc.). "Copy" button for clipboard
- **Mouse hover**: Shows cell coordinates and current color value
- **Clear grid**: Resets all cells to OFF

### Output Format
Matches `config/screensaver-images.yaml`:
```yaml
- name: my_image
  grid:
  - ['OFF', 'RED_HIGH', 'GREEN_LOW', ...]
  - ['AMBER_HIGH', 'OFF', 'OFF', ...]
  - ...
```

### Files
| File | Description |
|------|-------------|
| `tools/led-grid-editor.html` | Self-contained HTML/CSS/JS tool. No dependencies. Open directly in browser |

### How to Use
1. Open `tools/led-grid-editor.html` in any browser
2. Set rows/cols to match your Launchpad (8x8 for MK1)
3. Upload reference image (optional), adjust opacity slider
4. Click cells to set colors (G/R/O mode for quick cycling, RGB mode for full palette)
5. Click "Export" -> name your image -> "Copy" to clipboard
6. Paste into `config/screensaver-images.yaml` under the `images:` key

### Color Reference (MK1 Launchpad)
| YAML Value | Hardware | Visual |
|------------|----------|--------|
| `OFF` | LED off | #111 |
| `RED_LOW/MED/HIGH` | Red LED levels | #4a0000 / #8b0000 / #ff0000 |
| `GREEN_LOW/MED/HIGH` | Green LED levels | #003300 / #006600 / #00ff00 |
| `AMBER_LOW/MED/HIGH` | Amber (red+green) | #332200 / #664400 / #ffaa00 |

## Entry #20 — 2026-08-04 — Novation Hardware Virtualizer

### Purpose
Virtual Novation controller simulator for nova-script development without physical hardware. Creates virtual MIDI ports that nova-script discovers and connects to as if they were real USB devices. Web-based visual UI shows real-time LED state and allows clicking pads to simulate button presses.

### Architecture
```
Browser (HTML/JS) ←WebSocket→ Python Backend ←Virtual MIDI→ nova-script
```
- **Backend** (`tools/novation-virtualizer.py`): Creates virtual MIDI ports via `rtmidi`, bridges MIDI ↔ WebSocket, simulates hardware behavior
- **Frontend** (`tools/novation-virtualizer.html`): Realistic device rendering with LED glow effects, controller type selector, interactive pads/knobs/faders/transport
- **Launcher** (`tools/run-virtualizer.sh`): One-command startup for backend + browser

### Supported Controllers
| Device | Grid | Protocol | Colors | Port Name |
|--------|------|----------|--------|-----------|
| Launchpad MK1 | 8×8 | MK1 velocity | G/R/O bicolor | Launchpad MK1 |
| Launchpad Mini MK1 | 8×8 | MK1 velocity | G/R/O bicolor | Launchpad Mini |
| Launchpad MK2 | 8×8 | MK1 velocity | RGB (sim) | Launchpad MK2 |
| Launchpad Mini MK2 | 8×8 | MK1 velocity | RGB (sim) | Launchpad Mini MK2 |
| Launchpad Pro MK3 | 8×8 | MK3 | RGB palette | Launchpad Pro MK3 |
| Launchpad Mini MK3 | 8×8 | MK3 | RGB palette | Launchpad Mini MK3 |
| Launchkey 49 MK2 | 8×2 | Ch16 palette | RGB palette | Launchkey 49 |

### Visual Design
- **Charcoal theme**: #1a1a1a background, #222 device shell, #3a3a3a OFF pads (visible pad even when unlit)
- **LED-accurate colors**: Colors converted from sRGB to approximate real RGB LED gamut. MK1 red LEDs (~630nm) appear as deep red-orange `rgb(255,20,0)`. Green LEDs (~522nm) as vivid green `rgb(0,255,30)`. Amber (red+green simultaneous) as warm amber `rgb(255,155,8)`. All 3 brightness levels per color
- **LED glow**: Box-shadow spread proportional to brightness level: HIGH=14px, MED=8px, LOW=4px, OFF=none
- **Pads click visual**: Brief brightness flash on mousedown (filter:brightness 1.6) for tactile feedback

### Per-Controller Physical Layouts
| Device | Labels |
|--------|--------|
| **Launchpad Mini MK1** | Top: HOME, Perf, Clip, Seq, Mixer, Page◀, Page▶, Rec — Right: A-H |
| **Launchpad MK1** | Top: ⬆⬇⬅➡, Session, User1/2, Mixer — Right: Vol, Pan, SndA/B, Stop, Trk▶, Solo, Arm |
| **Launchpad Mini MK3** | Top: Note, Chord, Custom, ▲▼, Scale — Extra: Session, Note, Custom, arrows, Capture, Quantise |
| **Launchpad Pro MK3** | MK3 + Left column buttons + transport-style top row + Record/Play |
| **Launchkey 49 MK2** | Knobs K1-8, pads 8×2, faders F1-8, master fader, 8 transport buttons (◀◀, ▶▶, ◼, ▶, ↺, ●, Tr◀, Tr▶) |

### Hardware Simulation Accuracy
- **MK1 bicolor LEDs**: OFF=0, RED=1-3, GREEN=16-48, AMBER=17-51 at 3 brightness levels. All color aliases (BLUE→GREEN, PURPLE→AMBER, etc.) rendered as physical equivalents
- **MK1 coordinate mapping**: `note = (7-y)*16+x` — (0,0) bottom-left = note 112, (0,7) top-left = note 0
- **Top row**: CC 104-111 (0x68-0x6F) on channel 1
- **Right column**: Notes 8,24,40,56,72,88,104,120 on channel 1
- **Launchkey protocol**: LED control on channel 16 (0x9F) with 128-entry palette. Extended mode pad notes 96-103,112-119. Knobs CC 21-28. Faders CC 41-48 + master CC 7. Transport CCs 102-103,112-117.
- **Keyboard shortcuts**: Keys 1-8 = top row buttons, Shift+1-8 = right column buttons

### How to Use
1. `./tools/run-virtualizer.sh` (or `python tools/novation-virtualizer.py`)
2. Click "Connect MIDI" in the web UI — creates virtual ports like "Launchpad Mini"
3. Run nova-script: `python -m src.main` — it auto-discovers the virtual port
4. Click pads in the browser → nova-script receives GridEvents
5. nova-script sends LED updates → visualizer shows them in real time
6. Use the dropdown to switch between controller types (reconnects ports)

### MIDI Flow
```
User clicks pad → WebSocket → Backend sends [0x90, note, 127] via virtual MIDI out
→ nova-script receives via midi_in → processes event → sends LED update via midi_out
→ Backend receives [0x90, note, vel] via virtual MIDI in → maps to color → broadcasts to UI
```

### Files
| File | Description |
|------|-------------|
| `tools/novation-virtualizer.py` | Python backend: virtual MIDI ports, WebSocket server, device profiles |
| `tools/novation-virtualizer.html` | Web UI: realistic device rendering, interactive controllers |
| `tools/run-virtualizer.sh` | Launch script: starts backend + opens browser |

### Dependencies
- `python-rtmidi>=1.5` (already in nova-script venv)
- `websockets>=17` (added to venv via `pip install websockets`)

## Entry #21 — 2026-08-04 — Virtualizer Revisions: LED Accuracy, Layouts, Offline UX

### Changes from initial Entry #20

**LED Color Accuracy (complete rewrite of color tables)**
- Research-backed LED spectral approximations for all 28 LogicalColors
- MK1 bicolor LEDs mapped to real LED wavelengths: Red ~630nm → `rgb(255,20,0)`, Green ~522nm → `rgb(0,255,30)`, Amber (dual-LED) → `rgb(255,155,8)`
- Each color has 3 brightness levels with physically accurate scaling
- RGB devices (MK3, Launchkey) get LED-gamut-mapped primaries (narrower than sRGB)
- OFF pads rendered as visible grey `rgb(58,58,58)` — pad is visible even when unlit

**Visual Theme**
- Charcoal background (#1a1a1a), dark #222 device shell
- Medium grey OFF pads so the grid is always visible
- LED glow effects scaled to actual brightness: HIGH=14px spread, MED=8px, LOW=4px
- Pad click feedback: instant brightness flash (filter:brightness 1.6) mimicking physical press

**Per-Controller Physical Button Layouts**
Each controller now shows accurate button labels matching the real hardware:
- Launchpad Mini MK1: Top row labeled HOME, Perf, Clip, Seq, Mixer, Page◀, Page▶, Rec; Right col A-H
- Launchpad MK1: Top row ⬆⬇⬅➡, Session, User 1/2, Mixer; Right col Vol, Pan, SndA/B, Stop, Trk▶, Solo, Arm
- Launchpad Mini MK3: Front panel mode buttons (Session, Note, Custom, arrows, Capture, Quantise)
- Launchpad Pro MK3: Left column buttons, transport top row, extra Record/Play buttons
- Launchkey 49 MK2: Labeled knobs (K1-8), faders (F1-8 + MST), transport (◀◀, ▶▶, ◼, ▶, ↺, ●, Tr◀, Tr▶)

**WebSocket Reliability**
- Auto-reconnect with 2s retry interval when server is unavailable
- Error banner shown when attempting actions without server connection
- Offline fallback rendering: shows device shell with brand/model even before WS connects
- Keyboard shortcuts: keys 1-8 = top row, Shift+1-8 = right column buttons

**Backend: Color system refactored**
- Unified `COLOR_TO_LED_RGB` dictionary shared between Python backend and JS frontend
- Separate `MK1_VELOCITY_TO_COLOR` and `LK_PALETTE_TO_COLOR` lookup tables
- `color_to_rgb()` helper for reliable color→RGB mapping
- Device profiles expanded: `top_labels`, `right_labels`, `left_labels`, `extra_buttons`, `transport_labels`, `device_brand`, `model_line` fields

---

## Entry #22 — 2026-08-04 — Startup Wave Fix, Screensaver Cycle Fix, Smiley Face, Virtualizer Auto-Connect + Integration Testing

### Context
Session focused on polish: fixing the invisible startup wave, broken screensaver cycling, replacing the peace sign image, and making the virtualizer fully plug-and-play with nova-script.

### Changes Made

**Startup Wave Fix** (`src/engine.py`, `src/ui/startup_wave.py`, `src/ui/modes/performance.py`)
- Wave was finishing in ~0.6s — too fast to see on hardware. Increased to ~1.2s: 0.15s buffer before wave, 0.05s sleep per frame (was 0.03s), 0.2s pause after wave before mode render.
- Post-wave "red block" resolved: disabled FX slots in Performance Mode now render as `OFF` instead of `RED_HIGH`. Previously all 40 disabled FX cells (8 tracks × 5 FX) showed blazing red on boot, masking the startup wave and looking broken. Now only the track mute row (row 7) is lit on initial render.
- Wave commit optimized to use `dirty_cells()` instead of blasting all 64 pads per frame.

**Screensaver Cycle Fix** (`src/ui/overlay_manager.py`)
- Root cause: copy-paste bug in `_tick_screensaver()` — `_render_screensaver_image()` was called twice in a row. First call rendered and consumed dirty cells, second call had nothing to send. Hardware displayed first cycle (heart → peace) then froze on peace.
- Fix: single render call per cycle. Changed cycle index to `(index + 1) % 2` for clean 0↔1 alternation.
- Quick slots configured: slot 0 = image 1 (heart), slot 1 = image 8 (now smiley). Cycles every 4s.

**Smiley Face** (`src/ui/image_store.py`, `config/screensaver-images.yaml`)
- Replaced peace sign (image 8) with smiley face on 8×8 grid.
- Layout: eyes (two amber dots) at row 1, nose bridge at row 2, face outline at row 3, smile at row 4. Six rows of padding.
- Preserved Launchpad coordinate convention: image row 0 = top of pad (away from user), row 7 = bottom (closest).

**Virtualizer Auto-Connect + Clean Shutdown** (`tools/novation-virtualizer.py`)
- MIDI ports now auto-created on virtualizer startup — no need to click "Connect MIDI" in browser. `VirtualDevice.connect_midi()` called in `run()` before `serve_forever()`.
- Clean shutdown: replaced fragile `signal.signal()` + `sys.exit(0)` with `asyncio.new_event_loop()` + `loop.add_signal_handler()`. Server properly closes WebSocket + MIDI ports on SIGTERM/SIGINT. Exit code 0.
- macOS virtual port behavior documented: `MidiIn.open_virtual_port()` creates a CoreMIDI virtual SOURCE (appears as OUT port to other apps). `MidiOut.open_virtual_port()` creates a virtual DESTINATION (appears as IN port). Both share the same name "Launchpad Mini" — nova-script's substring matching handles this correctly.

**End-to-End Integration Testing** (`tools/test_integration.py`)
- Verified full bidirectional flow: virtualizer → virtual MIDI → nova-script → virtual MIDI → virtualizer → WebSocket → browser.
- nova-script discovers virtual "Launchpad Mini" ports automatically via `_find_matching_port()`.
- LED updates from nova-script (startup wave, performance mode render, page indicators) appear correctly in virtualizer state.
- Button presses simulated in virtualizer → nova-script receives GridEvents via virtual MIDI callback.

**MIDI Manager Poll Guard** (`src/midi/manager.py`)
- Fixed `'NoneType' object has no attribute 'lower'` when virtual ports disappear during health check.
- Added explicit `conn.input_port is None or conn.output_port is None` check before accessing `.name`.

**Dependencies** (`pyproject.toml`)
- Added `websockets>=14` as optional `[tools]` dependency group.
- Install with: `pip install -e '.[tools]'`

**Updated Scripts** (`tools/run-virtualizer.sh`)
- Updated help text: removed "Click Connect MIDI" step, added note that ports auto-create.
- Updated install hint to use `pip install -e '.[tools]'`.

### How It Works Now
1. `./tools/run-virtualizer.sh` — starts backend, auto-creates MIDI ports, opens browser
2. `nova-script live-show` — discovers virtual "Launchpad Mini" ports, connects immediately
3. Click pads in browser → nova-script processes events
4. nova-script LED updates → visualizer renders them with LED-accurate colors

### Files Changed
- `src/engine.py` — Longer wave timing, buffer pauses
- `src/ui/startup_wave.py` — dirty_cells optimization
- `src/ui/modes/performance.py` — Disabled FX: OFF instead of RED_HIGH
- `src/ui/overlay_manager.py` — Fix duplicate render in screensaver cycle
- `src/ui/image_store.py` — Replace peace with smiley (image 8)
- `config/screensaver-images.yaml` — Smiley pixel art
- `src/midi/manager.py` — Poll guard for None port
- `tools/novation-virtualizer.py` — Auto-connect + clean shutdown
- `tools/run-virtualizer.sh` — Updated instructions
- `tools/test_integration.py` — New: end-to-end test script
- `pyproject.toml` — websockets optional dependency
- `BUILD_LOG.md` — This entry

---

## Entry #23 — 2026-08-04 — Instrument Mode: Push-Style Grid Instrument

### Concept
Transforms the Launchpad Mini MK1 into a grid-based instrument controller modeled after Ableton Live's Push and Akai Force. The full 8×8 grid becomes a scale-mapped playing surface where every pad maps to a musical note. Right column buttons control mode parameters. Full vision document: [`docs/INSTRUMENT_MODE.md`](docs/INSTRUMENT_MODE.md)

### Architecture
```
InstrumentMode (src/ui/modes/instrument.py)
├── Scale system: major / blues / chromatic (6-12 notes)
├── Note calculator: scale_index, octave_shift, row_offset
├── Row offset: configurable semitones per row (12, 2, 3, 4, 5)
├── Right column controls (A-E)
│   ├── A: Notes (GREEN) / Chords (AMBER)
│   ├── B: Scale cycle → Major (GREEN) / Blues (AMBER) / Chromatic (RED)
│   ├── C: Hold toggle → OFF (RED) / ON (GREEN)
│   ├── D: ARP cycle → OFF (RED) / Up (GREEN) / Down (AMBER)
│   └── E: ARP pattern → Normal (GREEN) / Chordal (AMBER) / Octaves (RED)
├── A-button hold overlay: top row pads 1-5 show offset options
├── ARP engine: BPM-synced, pattern-based with step advancement
├── MIDI output: note ON/OFF with velocity 100
└── Color system: RED_HIGH (roots), GREEN_HIGH (pressed), GREEN_MED (octave), AMBER_LOW (background)
```

### Grid Visual Design
- **Root notes** — RED_HIGH (pads where note % 12 == root_note). 16 roots on major scale with octave offset.
- **Pressed pad** — GREEN_HIGH (currently held down). Full brightness.
- **Octave indicators** — GREEN_MED (same pitch class as pressed pad, different octave). ~70% brightness.
- **Background** — AMBER_LOW (~40%) on all 64 pads. Every pad shows a playable scale note. Never dark, never harsh.

### Controls Verified (virtualizer)
| Control | States | Performance |
|---------|--------|-------------|
| Scale (B) | Major → Blues → Chromatic | Cycle + re-render on each press ✓ |
| Hold (C) | OFF ↔ ON | Toggle, releases all on disable ✓ |
| ARP (D) | OFF → Up → Down | 3-state cycle, BPM-synced ✓ |
| ARP Pattern (E) | Normal → Chordal → Octaves | 3-state cycle ✓ |
| Offset overlay | Hold A → top row 1-5 | ORANGE bg + GREEN current ✓ |

### ARP Pattern System
Customizable JSON files in `config/arp_patterns/`:

| File | Description | Intervals |
|------|-------------|-----------|
| `normal.json` | Sequential scale notes | [0,1,2,3,4,5,6,7] |
| `chordal.json` | Root, 7th, 3rd, 5th | [0,6,2,4,0,6,2,4] |
| `octaves.json` | 3-octave span jumps | [0,7,14,7,0,7,14,7] |

To customize: replace any file with same-named JSON containing `{"name": "...", "intervals": [...]}`. Intervals are semitone offsets applied per ARP step.

### Note Calculation
```
For pad (x, y) with scale S, offset O, root R:
  scale_idx   = x % len(S)
  octave_up   = (x // len(S)) * 12
  row_up      = y * O
  note        = R + S[scale_idx] + octave_up + row_up
```

Example: Major scale [0,2,4,5,7,9,11], offset=12 (octaves), root=48:
- (0,0) = 48+0+0+0 = 48 (C3)
- (7,0) = 48+0+12+0 = 60 (C4)
- (0,1) = 48+0+0+12 = 60 (C4)
- (7,7) = 48+0+12+84 = 144

### Engine Integration
- Registered in `_setup_modes()` alongside other modes
- Top-6 button shortcut (205 → "instrument")
- BPM set via engine's `set_bpm()` pass-through
- `midi_manager` passed for MIDI output
- Mode name registered as "instrument" in mode manager

### CLI Improvements (same session)
- `nova-script virtualizer` — start backend + open browser GUI in one command
- `nova-script virtualizer stop` — clean shutdown of virtualizer process + MIDI ports
- Fixed `ControlEvent.pressed` AttributeError (derived `is_press` from `event_type.name`)
- Optimized instrument mode tick to avoid re-rendering on every engine tick (only on state changes)

### Files Changed
- `src/ui/modes/instrument.py` — New: 423-line mode class
- `src/engine.py` — Register instrument mode, Top-6 shortcut, fix ControlEvent.pressed bug
- `src/main.py` — CLI `virtualizer [stop]` commands
- `config/arp_patterns/normal.json` — New: sequential ARP pattern
- `config/arp_patterns/chordal.json` — New: chord-tone ARP pattern
- `config/arp_patterns/octaves.json` — New: octave-jump ARP pattern
- `docs/INSTRUMENT_MODE.md` — New: full vision and specification document
- `BUILD_LOG.md` — This entry

---

## Entry #24 — 2026-08-05 — Deep Research: MK1 LED Control, Diff-Based Rendering Plan

### Purpose
Comprehensive research into how the Launchpad Mini MK1 hardware actually handles LED control at the firmware, USB, and MIDI protocol levels. Identified fundamental inefficiencies in nova-script's rendering pipeline and documented a phased implementation plan.

### Research Document
[`docs/MIDI_LED_CONTROL_RESEARCH.md`](docs/MIDI_LED_CONTROL_RESEARCH.md) — 275-line deep dive covering:
- Physical LED matrix architecture (multiplexed scanning, PWM brightness)
- Full MIDI protocol breakdown (Note On for grid+right column, CC for top row)
- Color encoding table (green<<4 | red)
- Hardware limitations: no double-buffer, no state cache, no bulk clear, no read-back
- Maximum update rate analysis (~800-900 msg/s practical limit on USB 1.1)
- Automap kick internals (buffer flush + session mode reset)
- Cross-device comparison (MK1 → MK2 → MK3 → Launchkey)
- 6 game-changing insights with code-level fix descriptions

### Key Findings

**Finding 1: `clear()` + render sends 128 messages per frame (64 OFF + 64 ON).**
Every mode calls `self.clear()` at the start of `_render()`, marking all 64 cells dirty. Even when nothing changed, this flushes 64 OFF messages followed by 64 ON messages through USB. At 10Hz idle tick, that's 640 messages/second — wasteful and causes visible shimmer.

**Finding 2: No double-buffer = visible black flash between renders.**
Because the MK1 applies MIDI messages immediately with no frame buffer, the `clear()` call flashes all pads dark before the render fills them back in. This is perceivable as a single-frame flicker on every mode render.

**Finding 3: LED state is fire-and-forget — host must track it.**
The MK1 cannot be queried for current LED state. `LogicalGrid` + `_grid_state` in NovationController are the sole source of truth. Every `clear()` that's not followed by a complete render breaks the truth-hardware bond.

**Finding 4: Messages sent before device connects are silently lost.**
When nova-script starts without a Launchpad connected, all renders go into the void. On reconnect, only `clear_grid()` is sent, not the mode's current state. The mode's `enter()` must be called on reconnect.

### Implementation Plan

[`docs/IMPLEMENTATION_PLAN_RENDER.md`](docs/IMPLEMENTATION_PLAN_RENDER.md) — 11-task plan across 3 phases:

**Phase 1 — Diff-Based Rendering:**
- Controller-side diff check in `set_grid_color()` — skip send if color unchanged (2-line fix)
- Remove `clear()` from all 5 modes' `_render()` methods
- Modes draw new state directly; `commit_diff()` sends only changed cells
- Mode transitions (enter/exit) keep `clear()` for full repaint

**Phase 2 — Tick Throttle:**
- `_needs_render` flag in Mode base class
- `mark_dirty()` called on state changes only
- Idle ticks send 0 messages (was 0-64 per tick)
- ARP/animation modes still render at BPM rate

**Phase 3 — Connection State:**
- Verify `mode.enter()` on reconnect already works
- Add `refresh_grid()` to force full re-sync after reconnect

### Expected Impact
| Metric | Before | After |
|--------|--------|-------|
| Messages per mode switch | 128 | ~64 |
| Messages per idle tick | 0-64 | 0 |
| Visual flicker | Perceivable | Eliminated |
| Startup wave | 1280 msg | ~200 msg |

### Screensaver + Color Fixes (same session)
- **Screensaver ghost composites**: `_render_screensaver_image` lacked `grid.clear()` — OFF cells from new image didn't overwrite ON cells from old image. Fixed in overlay_manager.py.
- **MK1 LED color calibration**: Adjusted all 28 RGB values in Python backend + HTML frontend. Red ~625nm → warmer orange-red. Green ~525nm → less saturated. Amber → golden warmth through diffuser. OFF pad → darker grey.
- **Virtualizer CLI**: Changed to `nova-script <profile> virtualizer`. Clean shutdown on SIGINT kills both processes.
- Fixed `_reported_secondary` AttributeError in DeviceConnection dataclass.
- Fixed YAML indentation bug in screensaver-images.yaml.

### Files Changed
- `docs/MIDI_LED_CONTROL_RESEARCH.md` — New: 275-line research document
- `docs/IMPLEMENTATION_PLAN_RENDER.md` — New: comprehensive implementation plan
- `src/ui/overlay_manager.py` — Added `grid.clear()` to screensaver render
- `tools/novation-virtualizer.py` — Updated color table
- `tools/novation-virtualizer.html` — Updated color table
- `src/main.py` — Virtualizer CLI refactor
- `src/midi/manager.py` — DeviceConnection fields
- `config/screensaver-images.yaml` — Fixed YAML indent
- `BUILD_LOG.md` — This entry

---

## Entry #25 — 2026-08-05 — Diff-Based Rendering, Startup Wave Redesign, Screensaver Mode System

### Diff-Based Rendering (Phase 1-2 of Implementation Plan)

Implemented the rendering optimizations from the MIDI LED control research:

**Controller diff check** (`src/controllers/base.py`):
`set_grid_color()` now compares against stored `_grid_state` before sending MIDI. Skip if unchanged. 2-line change that eliminates redundant LED traffic.

**Performance mode tick throttle** (`src/ui/modes/performance.py`):
Was rendering 64 cells unconditionally every engine tick (~10Hz idle = 640 msg/s). Now only marks dirty on state changes (tuner phase, hint expiry). Idle sends 0 messages.

**Mode base tick guard** (`src/ui/mode.py`):
Added `_needs_render` flag and `mark_dirty()`. Base `tick()` only calls `_render()` when flag is set.

### Startup Wave — Bidirectional 3× Sweep

Sweeps bottom-left → top-right, back, 3× total. ~4.5 seconds. Forward: `x+y=band`. Reverse: `x+y=14-band`. 4-band color trail: AMBER→GREEN→RED→RED_LOW.

### Screensaver Mode System

Complete rewrite. Replaced 2-image cycling with 3 selectable modes via right column A-C buttons:

| Button | Mode | Description |
|--------|------|-------------|
| A | Heart | Classic red heart on 8×8 |
| B | Waves | Diagonal amber gradient |
| C | Glimmer | Random red/amber sparkle particles |

Current mode = AMBER_HIGH at 80%. Others = AMBER_LOW at 20%. Unused = OFF. Single press switches mode within the overlay — no dismiss flow.

### Glimmer Mode

Ambient sparkle particle system. 300-900ms lifecycle with smooth birth→peak→decay. 60% red / 40% amber, zero green. Radial falloff (core→ring1→ring2). Up to 8 simultaneous sparkles, max-brightness overlap. Twin sparkles at 15% probability. 200-1200ms random interval.

### UX Philosophy — Beyond Ableton

[TAETRO's "Your Launchpad Can Do WAY More Than You Think"](https://www.youtube.com/watch?v=gm67P7lvEek) demonstrates the principle: Launchpad is a complete performance instrument, not just a clip launcher. Nova-script exceeds this by being cross-DAW, standalone, hardware-agnostic, and deeply customizable — the virtualizer, screensaver modes, profiles, and ARP patterns have no equivalent in Ableton's Launchpad control.

### Files Changed
- `src/controllers/base.py` — Diff check in set_grid_color
- `src/ui/mode.py` — needs_render flag, mark_dirty, tick guard
- `src/ui/modes/performance.py` — Conditional tick
- `src/ui/startup_wave.py` — Bidirectional 3× wave sweep
- `src/ui/overlay_manager.py` — Screensaver mode system + glimmer
- `src/engine.py` — Simplified wave loop, removed cycle config
- `BUILD_LOG.md` — This entry

---

## Entry #26 — 2026-08-05 — ARP Vision, Hold/ARP Fix, Diatonic Transposition, Key System, Virtualizer Help Panel

### ARP Pattern Editor Vision
[`docs/ARP_VISION_DOC.md`](docs/ARP_VISION_DOC.md) — 329-line specification for on-Launchpad ARP pattern creation: 3-page × 8-slot library (24 total, 3 factory + 15 user), page navigation via G/H, save via long-press with GREEN blink, factory slots marked RED and read-only, ARP Edit Mode via long-press E, Note-Length sub-mode with LENGTH scroll entry animation, BPM-synced beat chase. Full 6-suite 30-case test plan.

### Hold + ARP Bug Fixes
Three critical bugs: Hold OFF never released notes (`_on_pad_release` was `pass`), Hold ON sent duplicate Note ON when replacing held note, same pad in Hold ON now toggles note off. All fixed.

### ARP Diatonic Transposition
Pattern intervals are scale-degree offsets, not semitones. Pattern [0,2,4] from C→C-E-G, from D→D-F-A (minor, in key). 3 edge cases: wraps modulo on overflow, chromatic=flat on 12-note scale, snaps out-of-scale notes. TUI toggle: Settings → ARP → Diatonic/Chromatic.

### Key/Root Note System
F button cycles root key (C→C#→D→...→B→C) with RED hint. Natural Minor scale added (intervals [0,2,3,5,7,8,10]) — 4 scales now: Major (S), Minor (m), Blues (B), Chromatic (C). Diatonic ARP follows key automatically.

### Scale Hint Redesign
All scale hints now RED with updated letters: S/Major, m/minor, B/Blues, C/Chromatic. Rapid cycling replaces hint immediately.

### Virtualizer Help Panel — Mode-Aware
Engine connects to virtualizer WebSocket and sends `{mode, page, subpage}` via `set_info` action. Help panel renders from actual mode name — no LED pattern guessing. Full help for all 8 screens with LED color dots per button.

### Button Reference Document
[`docs/BUTTON_REFERENCE.md`](docs/BUTTON_REFERENCE.md) — 300-line master reference: every button, LED, grid interaction, and setting across all modes.

### OSC Scrolling Text Display
Rewrote the HUD overlay system for smooth scrolling text messages received via OSC. When Reaper (or any OSC sender) sends `/nova/display/message "Karaoke"`, the text scrolls horizontally across the 8×8 grid using the 5×5 pixel font at sub-character precision.

**Scrolling engine:** Text is rendered as a continuous pixel strip. Each character occupies 5 pixel columns + 1 gap column = 6 "character-width" pixels. The scroll position advances by 1 pixel per engine tick at a rate of `5.0 / scroll_speed_ms` pixels per ms. At the default 60ms/char, each pixel advances every 12ms — smooth at 10Hz tick rate.

**Behavior:**
- Text scrolls once from right to left, then auto-dismisses (no looping)
- Surrounding pads are cleared (OFF) — display is clean, not composited
- Any button press immediately dismisses the message (press is consumed)
- Pressing during scroll stops the text and returns to active mode

**OSC integration path:**
```
Reaper → UDP :8000 → nova-script OSC server :9001
```
Route: `/nova/display/message` with a string argument. The engine's `_on_osc_message` routes `display_message` type to `overlay.trigger_hud(text=...)`.

**How to use with Reaper:**
1. Install ReaPack + `ReaScript Lua` in Reaper
2. Create a ReaScript action:
   ```lua
   reaper.OscLocalMessageToHost("/nova/display/message Karaoke")
   ```
   Or use ReaperOSC config with pattern:
   ```
   ACTION i/action t/action/@ s/action/s/@/display/message
   ```
3. Bind to a keyboard shortcut or trigger from a marker/region
4. Send any text string — nova-script displays it on the Launchpad

**TUI setting:** Settings → OSC → "Msg char speed (ms):" — enter 10-500. Default 60ms/char (fast but readable). Lower = faster scroll, higher = slower/more readable.

### BPM LED Fix
Flash 80ms→120ms. Removed dead code in `_get_downbeat_color`.

### Files Changed
- `docs/ARP_VISION_DOC.md` — New: ARP editor spec
- `docs/BUTTON_REFERENCE.md` — New: mode button reference
- `src/ui/modes/instrument.py` — Hold/ARP fixes, diatonic ARP, key, minor scale, hints
- `src/engine.py` — Virt WS sync, BPM fix, dead code, OSC scroll speed config pass-through
- `src/ui/overlay_manager.py` — Scrolling text HUD, pixel-level render, non-blocking dismiss
- `src/tui/app.py` — OSC scroll speed Input setting
- `tools/novation-virtualizer.py` — set_info action, mode fields
- `tools/novation-virtualizer.html` — Mode-aware info panel
- `docs/INSTRUMENT_MODE.md` — Hint table update
- `BUILD_LOG.md` — This entry


## Entry #27 — 2026-08-06 — Performance Mode Redesign: Dual-Channel GTR/VOX

Complete redesign of Performance Mode from a generic 8-track view into a purpose-built dual-channel live FX controller. Grid split vertically: left half (cols 0-3) = GTR, right half (cols 4-7) = VOX. Each channel has a volume bar, 4 FX blocks with 6 presets each, and per-FX disable. Reverb moved to Mixer Mode.

### Design Document
[`docs/PERFORMANCE_VIEW_VISION_DOC.md`](docs/PERFORMANCE_VIEW_VISION_DOC.md) — 310-line vision document covering layout, volume column math, FX preset/bank system, OSC mapping, and edge cases.

### Grid Layout
```
Col: 0        1   2   3        4        5   6   7
y=7: [GTR Vol] [FX1: Delay presets] [VOX Vol] [FX1: Delay presets]
y=6: [GTR Vol] [FX1: disable bar  ] [VOX Vol] [FX1: disable bar  ]
y=5: [GTR Vol] [FX2: Harmony       ] [VOX Vol] [FX2: Harmony       ]
y=4: [GTR Vol] [FX2: disable bar   ] [VOX Vol] [FX2: disable bar   ]
y=3: [GTR Vol] [FX3: Amp&Drv       ] [VOX Vol] [FX3: Drv&Flt       ]
y=2: [GTR Vol] [FX3: disable bar   ] [VOX Vol] [FX3: disable bar   ]
y=1: [GTR Vol] [FX4: Tremolo       ] [VOX Vol] [FX4: Misc SFX      ]
y=0: [GTR Vol] [FX4: disable bar   ] [VOX Vol] [FX4: disable bar   ]
```

### Volume Columns (cols 0, 4)
Dual-level press system on 8 pads covering 18-32 level range. Each pad has two logical levels: first press = GREEN_HIGH (higher even level), second press = AMBER_HIGH (lower odd level). Pads above current level show RED_HIGH (full column always lit). Pads below show OFF.

**Level mapping:**
| Pad | 1st press | 2nd press |
|-----|-----------|-----------|
| 7 | 32 | 31 |
| 6 | 30 | 29 |
| 5 | 28 | 27 |
| 4 | 26 | 25 |
| 3 | 24 | 23 |
| 2 | 22 | 21 |
| 1 | 20 | 19 |
| 0 | 18 | MUTE (0) |

Pad 0 double-press = mute: entire column turns RED_HIGH, volume = 0. Pressing any pad while muted unmutes to that level. Formula: `vol = 18 + 2*pad_y - (1 if sub else 0)`.

### FX Preset System
4 FX per channel with 3 pads × 2 banks = 6 presets per FX. Presets are saved "snapshot" configurations in Reaper (not just bypass toggles — they recall full FX chain settings).

**Bank toggle:**
- Press unused pad: select bank 1 preset (pad 0→preset1, pad 1→preset2, pad 2→preset3)
- Press selected pad (bank 1): switch to bank 2 (pad 0→preset4, pad 1→preset5, pad 2→preset6)
- Press selected pad (bank 2): switch back to bank 1

**Color coding:**
- Unselected preset: GREEN_HIGH
- Selected, bank 1: AMBER_HIGH (ORANGE)
- Selected, bank 2: RED_HIGH
- Presets when FX disabled: OFF

**Auto-enable:** Pressing any preset pad when the FX is disabled automatically enables it and selects that preset. This prevents the user from changing presets on a bypassed effect (the preset wouldn't take effect until the FX is re-enabled).

### FX Disable Bars
Directly below each FX block, 3 RED pads that toggle the effect on/off:
- Disabled: RED_MED
- Enabled: RED_HIGH

Single press toggles — press any of the 3 pads to disable, press any again to re-enable. The previous preset is restored on re-enable.

### FX Order (top to bottom)
| Row Pair | GTR | VOX |
|----------|-----|-----|
| 7-6 | Delay | Delay |
| 5-4 | Harmony | Harmony |
| 3-2 | Amp & Drive | Drive & Filters |
| 1-0 | Tremolo | Misc / Special FX |

### Reverb in Mixer
Mixer Mode now has reverb send on row 0. 3-way toggle per track cycle: OFF (0%) → AMBER_MED (50%) → GREEN_HIGH (100%). OSC: `/track/{n}/fx/rev/send` (float 0.0-1.0). Reverb was removed from Performance Mode (replaced by Amp&Drv for GTR, Drv&Flt for VOX).

### OSC Mapping
| Channel | Track | Volume | FX {1..4} Preset | FX {1..4} Bypass |
|---------|-------|--------|-------------------|-------------------|
| GTR | 2 | /track/2/volume | /track/2/fx/{k}/preset | /track/2/fx/{k}/bypass |
| VOX | 1 | /track/1/volume | /track/1/fx/{k}/preset | /track/1/fx/{k}/bypass |

Volume: float 0.0-1.0. Bypass: 0=enabled, 1=disabled. Preset: int 1-6.

### Unit Tests
[`tests/test_performance_mode.py`](tests/test_performance_mode.py) — 37 assertions across 7 test areas:
- Volume pad ↔ level mapping (10 bidirectional tests)
- FX row layout (4 tests verifying Delay=7/6, Harmony=5/4, Amp&Drv=3/2, Tremolo=1/0)
- Volume press: dual-level toggle, repeat cycling, cross-pad jump
- Volume mute/unmute: full column RED, unmute on any press
- FX preset select: bank toggle, cross-pad switch, colors verified
- FX disable: re-enable via preset press, disable row color change
- Independent channels: GTR and VOX operate independently

### Files Changed
- `src/ui/modes/performance.py` — Complete rewrite (273 lines): split GTR/VOX, volume bars, FX preset blocks, OSC sender
- `src/ui/modes/mixer.py` — Reverb send row 0, 3-way toggle, osc_bridge support
- `src/engine.py` — Pass osc_bridge to MixerMode
- `docs/PERFORMANCE_VIEW_VISION_DOC.md` — New: 310-line vision document
- `docs/BUTTON_REFERENCE.md` — Updated Performance + Mixer sections
- `docs/PAD-NAVIGATION-MANUAL.md` — Updated Performance + Mixer sections
- `tests/test_performance_mode.py` — New: 37-assertion test suite

## Entry #28 — 2026-08-06 — ARP Edit: Live Legato Playback (note-lengths 6-8)

V1.2 of the ARP editor note-length system. Note-lengths now drive actual MIDI playback instead of being visual-only. Previously the ARP preview was fully staccato (release-all-then-attack) and `_beat_step` never advanced live, so lengths 6-8 did nothing audibly. This entry adds a real tempo-driven playback loop with length-aware note-offs.

### Behavior
- **Live chase loop**: `tick()` → `_advance_chase()` computes the current step from elapsed time since entry (`int((now-entry)/step_dur) % 8`, no cumulative drift — per vision A5). Each step boundary fires the step's note.
- **Length-aware offs**: each played step gets its note-off scheduled at `now + multiplier * step_dur`. Short lengths (1-4) release within the step; length 5 releases at the next boundary; lengths 6-7 (dot/quarter) overlap into following steps.
- **Legato (length 8)**: `off_time = None` → note is held indefinitely and only released when a *different* pitch is played (replace) or on exit/release-all. Same-pitch legato stays sounding (no re-attack → no note pileup). This directly satisfies vision risk A4 mitigation.
- **Throwd scheduling**: `_fire_due_offs()` runs each tick to retire notes whose off-time has arrived, keeping `_voice`/`_active_notes` lean and preventing MIDI note pileups.
- **Grid-tap audition** (`_preview_step`) now uses the tapped step's own length instead of instant release-all.
- Removed dead `_preview_arp_step`.

### Files Changed
- `src/ui/modes/arp_edit.py` — Live chase loop, note-off scheduler, legato replace logic, length-aware preview; removed dead method
- `tests/test_arp_edit.py` — 5 new tests (beat advance, staccato single-step, legato hold, legato no-stacking, short-note due release)

Test result: **ALL ARP EDIT MODE TESTS PASSED** (8 original + 5 new).

## Entry #29 — 2026-08-06 — ARP Edit: "LENGTH" Entry Scroll Animation

v2 deferred item #1 of the ARP note-length system. When entering note-length sub-mode via E, the grid now plays a 1-second scrolling "LENGTH" text overlay (RED_HIGH) before the bar-graph appears — visual confirmation of the mode, as specified in the ARP vision doc.

### Behavior
- On E press (entering note-length mode), `_show_length_overlay()` activates the overlay.
- `tick()` prioritizes the overlay: while active, `_advance_length_overlay()` scrolls the `LENGTH` glyph across the grid right-to-left at ~150ms/px, rendering each frame instead of the bar-graph.
- The overlay ends after `_length_overlay_ms` (1000ms), handing off to the standard bar-graph.
- Any grid/control interaction during the animation immediately shows the bar-graph (the note-length handler calls `_render()` directly).

### Files Changed
- `src/ui/modes/arp_edit.py` — Overlay state (`_length_overlay*`), `_show_length_overlay`, `_advance_length_overlay`, `_render_length_scroll` (RED_HIGH 5×5 font), tick branch
- `tests/test_arp_edit.py` — 3 new tests (overlay activates on E, draws RED-only pixels, times out to bars)

Test result: **ALL ARP EDIT MODE TESTS PASSED** (16 total).

## Entry #30 — 2026-08-06 — ARP Edit: Long-Press A-H Save to Slot

v2 deferred item #2 of the ARP note-length system. Long-pressing a slot button (A-D, F) in ARP Edit Mode now saves the current pattern to that slot with a 1s GREEN blink confirmation. Short press still selects/loads. Factory slots A/B/C remain read-only (save silently blocked).

### Behavior
- The slot action moves from press to **release** so short vs long can be distinguished:
  - **Short release** (< `_long_press_ms`) → `_handle_slot_select_by_rid()` loads the pattern (existing behavior).
  - **Long release** (≥ 500ms) → `_handle_slot_save()` writes `config/arp_patterns/user_XX.json`, then arms a flash.
- `_slot_press_rid`/`_slot_press_time` track the in-progress hold; E/G/H and note-length-mode presses are unchanged (press-on, no long-press).
- **Save flash:** `tick()` toggles the target slot LED between GREEN_HIGH/OFF (~250ms) for 1s; `_render_right_column()` draws the flash slot in GREEN. Non-factory only.
- Factory slots (1,2,3) short: `_handle_slot_save` returns immediately — no save, no flash (read-only per spec).
- Grid-tap preview and note-length sub-mode are unaffected.

### Files Changed
- `src/ui/modes/arp_edit.py` — press-tracking fields, release-based slot dispatch, `_handle_slot_save`, `_handle_slot_select_by_rid`, flash blink in tick + right-column render
- `tests/test_arp_edit.py` — 5 new tests (short select, dispatch, long save, factory protected, flash LED)

Test result: **ALL ARP EDIT MODE TESTS PASSED** (20 total).

## Entry #31 — 2026-08-07 — Performance Routing Hardening: Akai Force, Clock, ARP Exit

Full audio-path audit before the live show. The engine previously claimed to route to the Force but sent to a never-registered port, so no sound. All blockers fixed and locked with tests.

### B1 — Akai Force MIDI Output
`MidiManager` gained `force_device`, `register_force_output(port_pattern)` (registers the Force as a normal output-only device on the Live system), and `send_force(message)`. All instrument/ARP/sequencer/clip note-on/off sites now send through `send_force` (LEDs still stay on the Launchpad). Force device name is read from `midi.force_output.port_name` (default.yaml) with fallback to `midi.outputs.force`.

### B2 — Sequencer / Clip Note-Offs
Previously the sequencer never sent note-offs (stuck notes). Tick now sends note-off for the PRIOR step and note-on for the CURRENT step each tick. `clip_launcher._stop_output` routes through force. Fixed an indentation bug in clip launcher `_stop_output`.

### B3 — BPM Clock Feed
Reaper BPM reaches the Force two ways: OSC beat → `feed_osc_beat(position)` (beat handler), and MIDI realtime 0xF8 → `feed_midi_clock()` in the event loop. Both drive the scheduler.

### B4 — ARP Exit Button
ARP Edit exit moved from top-row control 201 (top-row 2) to 200 (top-row 1, the natural "exit" on the left). Falls back to whatever top-row button is active.

### Tests
- `tests/test_midi_routing.py` (new): send_force, register_force_output, units, seq note-off parity (5).
- `tests/test_bpm_clock_feed.py` (new): OSC beat + MIDI clock 0xF8 both fire (4).
- `tests/test_arp_edit.py`: added `test_exit_button_is_top_row_one` (21 total).
All GREEN via `.venv/bin/python`.

## Entry #32 — 2026-08-07 — Mixer Live VU + Performance Stroke Tuner Needle

Built out the "hands-off-computer" aux features so the computer can stay out of the evidence.

### Mixer Mode — Live VU
- Added `set_track_vu / set_master_vu` accessors, VU/peak state, `_vu_fall_ms` LED holding (300ms).
- `_render()` per column: AMBER = live signal rising from bottom, GREEN = set fader level (marker), RED at top row = peak/clip persistent flash (`_vu_peak >= 0.98`), and master clip flashes mute row red.
- OSC: `/nova/track/{n}/vu` + `/nova/master/vu` (bridge) → engine → `mixer.set_track_vu / set_master_vu`. Mixer render wiring done (existing wire in engine lines ~419-429).

### Performance Mode — tuner receives real cents
- `update_tuner(cents, channel)` no longer a no-op: stores cents/channel and marks dirty. Added `start_tuner / stop_tuner`.
- Active tuner now shows a live needle: column clamped cents/50 + center, GREEN when `|cents| < 1` (in-tune), AMBER within 30c, RED beyond; 8×8 strobe fills the rest.
- `handle_grid_event` exiting tuner now goes through `stop_tuner()` (clean exit anim).

### Virtualizer + Docs
- `tools/novation-virtualizer.html`: mixer help documents VU/fader/hold; performance help documents tuner toggle + needle.
- OSC contract `/nova/tuner` (cents, channel) already present in namespace + bridge.

All suites GREEN (`.venv/bin/python`): test_performance_mode, test_bpm_clock_feed, test_midi_routing, test_arp_edit, test_combo_detector.

## Entry #33 — 2026-08-07 — Performance Tuner: Motion-Band Strobe (proven design)

Replaced the static needle tuner with a motion-band strobe, per the proven "strobe = motion, not precision" principle (matches mod.dev, Peterson, Chroma/Chromatic tuner design: "less it moves, more you're in tune").

### Design
- A 2-column-wide vertical band sweeps left↔right across the grid, bouncing at the edges.
- Band SPEED is proportional to |cents| (distance from in-tune), smoothed via lerp in `_advance_tuner_band`. As the player tunes closer the band decelerates and visually glides to a stop.
- Color is the LOCK state: RED when way off (>20¢), AMBER while hunting (3–20¢), GREEN when locked (|cents|<3 AND speed<0.4).
- Background keeps a subtle animated strobe shimmer (`_tuner_phase`) so the sweep reads clearly against a live backdrop.

### Constants (source of truth for the LSM/iPhone port)
`TUNER_SPEED_PER_CENT=0.18`, `MAX_TUNER_SPEED=7.0`, `BAND_MIN_X=0.6`, `BAND_MAX_X=6.4`, `BAND_WIDTH=1.5`, `LOCK_CENT=3.0`, `NEAR_CENT=20.0`.

### Files Changed
- `src/ui/modes/performance.py` — band state, `_advance_tuner_band()`, rewritten `_render_tuner()`, tuner constants
- `tests/test_performance_mode.py` — `test_tuner_motion()` (in-tune green, way-off red, re-lock after settle)

Test result: **ALL PERFORMANCE MODE TESTS PASSED** (incl. new tuner motion).

## Entry #34 — 2026-08-07 — LSM Handoff: HD iPhone Tuner + REAPER pitch feed

Created the handoff doc for the Live Show Manager session to port the proven motion-band tuner to the iPhone's full-color display and wire it to REAPER's tuner via the standard OSC path.

- `~/Documents/projects/live-stage-hud/ai-handoff/handoff-8-tuner-motion.txt` — full spec: motion-band behavior + constants to port verbatim, iPhone page/CSS/rAF spec, server `/nova/tuner` routing snippet, and a "probe first" plan to nail ONE working REAPER→OSC pitch feed (JSFX/control-surface) before building the UI. Phone degrades gracefully to "NO SIG" on missing feed.

## Entry #35 — 2026-08-07 — Performance Mode: FX Letter Hints (non-blocking overlays)

FX tap feedback for the "hands-off-computer" live rig, matching the Instrument Mode hint pattern.

### Behavior
- Any FX preset or disable press shows a 300ms 5×5 letter overlay (first letter of the FX name: D=Delay, H=Harmony, A=Amp&Drv) using the font in `src/ui/modes/message.py`.
- Hints are non-blocking — pad presses and FX continue normally; overlay clears on expiry during the next `_render()`.
- Configurable via engine's existing `set_hints_config(enabled, color)` feed (`ui.hints_enabled` / `ui.hints_color` from config). Default AMBER_HIGH.

### Files Changed
- `src/ui/modes/performance.py` — hint state, `_show_hint`, `_show_fx_hint`, `_render_fx_hint`, trigger in `_handle_fx_press` (both disable toggle + preset select), overlay draw in `_render()`
- `set_hints_config` now honors the color string (resolves to LogicalColor).
- `tests/test_performance_mode.py` — `test_fx_hints` (armed on press, expires, disable toggles also hint, suppressed when disabled). Base-color tests opted out via `set_hints_config(False)`.
- `tools/novation-virtualizer.html` — performance help documents the hint letters + tuner band.

Test result: **ALL PERFORMANCE MODE TESTS PASSED.**

## Entry #36 — 2026-08-07 — TUI Broadcast Loop Fix (--tui crash)

`python -m src.main live-show --tui` crashed at startup because `Engine.start()` called `asyncio.create_task(self._tui_broadcast_loop())` but no such method existed, and the `_virt_sync_loop` it did define held the TUI push loop UNREACHABLE behind an infinite websocket-sync `while` loop.

### Fix
- Split the single combined coroutine into two separate tasks:
  - `_virt_sync_loop` — visualizer websocket sync only (1s poll).
  - `_tui_broadcast_loop` — TUI grid_state publish (50ms, grid snapshot + mode + device status).
- Both are spawned independently in `Engine.start()`.

Test: engine imports + both methods resolve; all 5 suites GREEN.

## Entry #37 — 2026-08-07 — Full Suit Greening + Clip Launcher Bug Fix

Regressed every stale test suite to green again and fixed two latent bugs found during regression.

### ClipLauncherMode: track-stop row unreachable (real bug)
`handle_grid_event` checked `_clip_colors[idx] == OFF` BEFORE the `y == 0` stop-track branch. The bottom scene (y=0) is empty by default, so the OFF guard returned early and the track-stop row never fired. Moved `y == 0 → _stop_track(x)` above the OFF check.

### Stale test repairs
- `test_edge_cases` clip stress test tapped `y in (1,2)` — those map to scenes 5/6 which are EMPTY → "got 0 playing". Rewrote to drive active scene 0/1 (y 7/6), scene launch via right-col control 107 (scene 0; control 100 = scene 7 = empty), and long-press clear at an active scene coords.
- `test_overlay_system` — sunrise wave test needed clock fanback (`fake-monotonic` stub) + frame-capped `tick()`; screensaver picker rewritten to named-mode switching via right-column control (`100+idx`).
- `test_chill_mode` — removed dead code referencing unimported `LogicalColor`.
- `test_virtualizer_integration` — menu items keyed by x/y, tap at (0,7) now matches.

Test: all 11 suites GREEN (performance, arp_edit, bpm_clock, midi_routing, combo_detector, edge_cases, overlay, chill_mode, virtualizer, combo_hardware, fireworks).

## Entry #38 — 2026-08-07 — Tuner Button A/B Wiring (right column)

`PerformanceMode.handle_control_event` was a bare `pass`. Wired per PERFORMANCE_VIEW_VISION_DOC:
- **Button A (control 107, row 7):** strobe tuner toggle for active channel.
- **Button B (control 106, row 6):** cycles active channel GTR↔VOX. If tuner is live, retargets tuner channel + resets cents/speed/band.

Added `set_active_channel()` API + `_active_channel` state (default GTR), and `test_tuner_control_buttons` covering: A toggles in/out, B cycles w/o starting tuner, A targets active channel, B retargets live tuner + resets, releases ignored.

Test: all 11 suites GREEN.

## Entry #39 — 2026-08-08 — HANDOFF: Browser suite green + real-hardware smoke run (open issues for fresh eyes)

**Purpose: handoff for the session that took nova-script from the browser-only virtualizer suite out onto the physical Launchpad Mini MK1. Two open items below need fresh eyes.**

### What landed this session

**Browser suite grown to 52 tests, 4× consecutive green** (`tools/browser-tests`, run `npx playwright test`):
- `06-tuner.spec.js` — guitar tuner lifecycle (intro letters → active band → exit), OSC `/nova/tuner` cents drive, channel switch, bailout.
- `07-performance-fx.spec.js` — FX bank power/preset/bank-flip/bypass, VOX independence, volume mute. Includes `resetPerformanceFx` fixture (FX state leaks across the shared engine).
- `08-instrument-arp.spec.js` — instrument scale/ARP/hold/key controls + ARP editor (entry, step edit, note-length, paging, slot save, HOME exit).
- `09-arp-midi.spec.js` — asserts the ARP's **real MIDI note stream** (pitches, order, off/on discipline, step timing, release-stop).

**Real engine bugs fixed this session** (all caught by the new tests):
- `performance.py` `tick()` never rendered — tuner intro/band/exit animation was frozen. Now renders every tick while the tuner is running.
- FX hint glyph ghost — the 0.3s hint letter was never painted over on expiry; now cleared in `tick()`.
- `instrument.py` `_arp_offset_for_note` octave bug — used `base_note // 12` instead of `(base_note - root) // 12` → every ARP note 4 octaves too high.
- ARP "walking base" — arp took its base from the last *sounded* note instead of the held pads; added `_gate_notes` (held pad notes, separate from sounding `_active_notes`).
- ARP never stopped on pad release — releasing the gate now calls `_release_all_notes()` (unless HOLD is latched).
- **E short-press now cycles ARP patterns** (normal→chordal→octaves); long-press still opens the editor.
- `normalizeHome` (test helper) made idempotent.

**Virtualizer** (`tools/novation-virtualizer.py`): added a virtual **"Akai Force" capture port** that logs the engine's note-on/off into `state.midi_log` (WS action `clear_midi`), so ARP output is testable without hardware. `midi_log` is capped at 80 events in broadcasts to keep the WS light.

**MK1 hardware constants verified** against the official Launchpad MK1 reference — all correct: grid notes `(7-y)*16+x` (note 0 = physical top-left, 112 = bottom-left), right column notes `[8,24,40,56,72,88,104,120]`, top row CC `0x68..0x6F`, color map `00gg00rr` (RED 1/2/3, GREEN 16/32/48, AMBER 17/34/51). Added `tools/verify_mk1_hardware.py` (4-phase LED + button-listener check).

### Real-hardware smoke run (tonight)

Engine boots clean against the physical device (`python -m src.main live-show`):
- ✅ Connected to `Launchpad Mini`, boot wave, performance screen.
- ✅ 8s-idle → screensaver (matches `ui.idle_timeout_ms: 8000`).
- ✅ OSC beats received → clock synced to ~148 BPM; `/nova/tuner` cents received.
- ✅ Top-row buttons send CC 104-111 (press=127/release=0); grid notes decode correctly.
- ⚠️ **MK1 button input froze mid-test** (device sent nothing to a fresh listener). **Power-cycling the Launchpad fixed it.** Not reproduced after a clean engine boot (mode switches then reached the engine normally). Believed caused by accumulated unclean device state from many open/close cycles (verify-script runs + SIGTERM'd engine without a reset-on-exit). The engine's `_kick_input_buffer` workaround works when the device starts clean.

### OPEN ISSUES (need fresh eyes — this is the handoff)

1. **Screens 2 and 3 display as the same** on the physical device: `clip_launcher` (202) and `sequencer` (203) appear identical to the user, and the user says the displays "do not match what I remember specifying." In code their default renders are clearly different:
   - `clip_launcher._init_default_colors()`: scenes 0–3 (top 4 rows) get `MK1_COLOR_CYCLE` colors AMBER_HIGH/RED_HIGH/GREEN_HIGH across all 8 tracks; scenes 4–7 OFF.
   - `sequencer._render()`: empty grid with RED_LOW markers on every 4th step + a transport row (`GREEN_HIGH`/`RED_HIGH` play + AMBER_LOW on cols 6/7).
   - So seeing them identical suggests either a shared render path, a screensaver override, the switch not landing, or the user's remembered design diverged from the current config. **Next step: capture the engine's actual LED out per mode (e.g. run the virtualizer against the engine, or a MIDI-through to log LED messages) and diff clip_launcher vs sequencer; also compare `modes.sequencer` config in `config/profiles/live-show.yaml` against the intended design.**
2. **HOME (control 200, button 1)** was reported as not working — but that was during the frozen-input window, so it is **not yet re-verified** with live input. Re-test on a clean device.
3. **MK1 input freeze** (see above) — consider hardening connect/disconnect to always leave the device clean (send reset on exit; confirm `_kick_input_buffer` ordering) so a mid-gig restart can't freeze the buttons.

### Current state / next steps
- Engine was left running against the physical Launchpad during the session; restart fresh when continuing.
- Finish the hardware smoke once #1 is understood: tuner visual (H + OSC cents), instrument + ARP on real hardware.
- The 52-test browser suite is the regression net; run it after any mode-render change.

## Entry #40 — 2026-08-08 — Menu Navigation Fix: Grid Display & Mode Switching

### Root Cause Analysis (virtualizer diagnostic)
Using a virtualizer-based diagnostic that captured the rendered LogicalGrid for each mode, confirmed all 5 modes render distinctly — clip_launcher, sequencer, performance, mixer, and instrument each produce unique, correct grids. The "screens look identical" bug from Entry #39 had three root causes:

**Root cause 1: Hardcoded shortcuts bypassed menu config**
`engine.py:339` had a hardcoded shortcut table `{201: "performance", 202: "clip_launcher", 203: "sequencer", ...}` that always fired before the menu's own `handle_control_event`. This meant button 2 (201) always went to "performance" regardless of the menu config saying item[1] = CLIP → "clip_launcher". Button 3 (202) always went to "clip_launcher" regardless of config saying item[2] = SEQ → "sequencer". The menu's YAML config was unreachable for top-row button presses.

**Root cause 2: HOME went to "performance" instead of "menu"**
Both the combo detector "home" result and the `tick()` timeout home fallback called `switch_to("performance")`. The FEATURES_AND_SPECS §2.1 states: "Top row button 1 = HOME. Always returns to Menu mode."

**Root cause 3: default_mode was "performance" not "menu"**
`config/profiles/live-show.yaml` had `default_mode: performance`. The FEATURES_AND_SPECS §1 states: "Startup Wave → Menu Mode → idle timer". With performance as default, the user never saw the menu on launch.

### Fixes Applied

1. **Shortcuts now read from menu config** (`engine.py`): Removed hardcoded shortcut table. Instead, when a top-row button is pressed (201-208), the engine reads the menu mode's `_items` list at that index and switches to the configured mode. This works both when IN menu mode and when NOT in menu mode, so mode shortcuts work universally from the menu config.

2. **HOME returns to menu** (`engine.py`): Both `_on_control_event` combo result "home" and `_tick` timeout result "home" now call `switch_to("menu")` instead of `switch_to("performance")`.

3. **Home LED "at home" check** (`engine.py` `_set_home_led`): Changed `active_mode_name == "performance"` to `active_mode_name == "menu"` so Top-1 LED blinks amber when actually at the menu (the home screen).

4. **default_mode → "menu"** (`config/profiles/live-show.yaml`): Changed from "performance" to "menu" per spec.

5. **Added INST to menu config** (both live-show.yaml and engine default items): Instrument mode at button 5 (control 204, top_idx=4), GREEN_MED color, positioned at (2,4) in 2×2 block.

### Virtualizer Verified — Rendered Grids (post-fix)

```
MENU (home):           CLIP (btn2→clip_launcher):   SEQ (btn3→sequencer):
##RR@@..               @@@@@@@@                      $$....aa
##RR@@..               ########                      g...r...
$$GG....               $$$$$$$$                      g...r...
$$GG....               @@@@@@@@                      g...r...
........               ........                      g...r...
........               ........                      g...r...
........               ........                      g...r...
........               ........                      g...r...
```

### Files Changed
- `src/engine.py` — Shortcut dispatch reads menu items; HOME → menu; home LED check → menu
- `config/profiles/live-show.yaml` — default_mode → menu; added INST mode item

### Test Status
Core suites pass: combo_detector (7), performance_mode (37+), arp_edit (20+), bpm_clock (4), midi_routing (5), fireworks. Three suites fail on pre-existing `tests.virtualizer` import (tests dir lacks __init__.py).

### Diagnosis Method
Used virtualizer to capture LogicalGrid snapshots for each mode. Diagnosed three root causes:
1. **Hardcoded shortcuts** (engine.py:339) bypassed menu YAML config
2. **HOME → "performance"** instead of "menu" (violated spec §2.1)
3. **default_mode: performance** instead of "menu" (violated spec §1)

Also fixed a secondary issue where `_grid_state` wasn't reset on mode switch, causing diff-based rendering to silently skip LED updates. Added `reset_grid_state()` to `NovationController` (called in `ModeManager.switch_to()`). Total MIDI messages per mode switch: 64 OFF + ~20 colored = ~84.

Virtualizer E2E test is timing-sensitive due to the virtualizer's sequential MIDI poll loop struggling to drain 1500+ startup wave messages before mode renders arrive. The fix is verified directly via captured MIDI output: 84 correct messages with proper cell targeting.

## Entry #41 — 2026-08-08 — Mode Switch Render Fix: clear_grid on Transition

### Problem
After fixing the shortcut/menu routing bugs (Entry #40), mode renders still showed startup wave artifacts. The diff-based rendering in `NovationController.set_grid_color()` was comparing against stale `_grid_state` values left by the startup wave. When the previous mode (or startup wave) set `_grid_state[y][x] = AMBER_HIGH` and the new mode wanted `RED_HIGH`, the diff check worked. But when both modes set the same color (or OFF), the diff check blocked sending — leaving hardware in the old state.

### Root Cause
`Mode.switch_to()` → `new_mode.enter()` → `_render()` did `self.clear()` (LogicalGrid only) then `self.commit()` → `controller.set_grid_color()`. The diff check in `set_grid_color` compared against `_grid_state` which still held the PREVIOUS mode's colors. Cells that happened to match were silently skipped, leaving behind ghost LEDs on hardware.

### Fix
Added `controller.clear_grid()` call in `ModeManager.switch_to()` BEFORE the new mode's `enter()`. This sends OFF to all 64 hardware LEDs and resets `_grid_state` to OFF everywhere. The new mode's render then only sends the cells it actually wants lit (~20 for menu), which now always differ from OFF so the diff check passes.

Also added `_needs_render = False` in `MenuMode.enter()` to prevent an unnecessary second render from `tick()`.

### Verified
- Direct MIDI capture: 84 messages per switch (64 OFF + 20 colored) — correct
- `_grid_state` matches expected menu layout (5 blocks × 2×2 = 20 cells)
- All 6 core test suites pass

### Files Changed
- `src/controllers/base.py` — Added `reset_grid_state()` helper (kept for future use)
- `src/ui/mode_manager.py` — `switch_to()` calls `controller.clear_grid()` before mode.enter()
- `src/ui/modes/menu.py` — `_needs_render = False` in enter()

## Entry #42 — 2026-08-08 — Clip Quadrants, ARP UI Rework, Engine Control Fix, Clock to Force, OSC Bridge

### Source
Daniel via Claude Code. Major polish session before live show. All virtualizer-driven with hardware verification.

### Clip Launcher — 4 Quadrants
Replaced the old 4-row color band layout with 4 even quadrants matching Daniel's spec:
- **Top-left** (scenes 0-3, tracks 0-3): AMBER_HIGH
- **Top-right** (scenes 0-3, tracks 4-7): GREEN_HIGH
- **Bottom-right** (scenes 4-7, tracks 4-7): RED_MED (80% brightness)
- **Bottom-left** (scenes 4-7, tracks 0-3): OFF (empty)
- Bottom row y=0 remains the track-stop indicator row.

Verified: 44 lit cells (16 amber + 16 green + 12 red; y=0 is track-stop, overwriting 4 red cells).

### ARP Edit Mode — Button Remapping + LENGTH Fix + Note-Length Exit
**Right-column layout changed:**
- A–E = presets (slots 1–5), F = note-length (RED indicator), G = page down, H = page up
- Previously E was note-length and F was a slot — the preset between note-length and up/down is now gone

**LENGTH overlay scroll fix:** Increased from 1000ms/150px-per-ms to 3200ms/60px-per-ms so the full word "LENGTH" scrolls across before the bar-graph appears. Previously only ~6px scrolled ("len") before cut-off.

**Note-length mode exit:** Pressing grid pads edits step lengths and STAYS in note-length. The ONLY way back to the pattern editor is pressing the green Top-1 button (control 200). The engine routes this: Top-1 in note-length mode → `exit_note_length()` → back to pattern editor. Top-1 while not in note-length → exit arp_edit entirely. F is now only the entry toggle (red indicator).

**Edit cooldown:** After a pad tap or slot selection, chase-triggered re-renders pause for ~1.2s so edits stay visible instead of being redrawn every beat (felt "jumpy").

### Engine Control Event Fix — Right-Column Swallow Bug
The `_on_control_event` shortcut dispatch had an unconditional `return` at line 373 that swallowed **every right-column button press (A-H, control_id 100-107) in every non-menu mode**. This meant ARP edit slots (A-H), instrument controls, and all mode-specific right-column functions were dead. 

Fixed by removing the `return`: shortcut dispatch only handles 201–208 (top-row), everything else (right column, grid) flows to `mode_manager.handle_control_event`.

**Also simplified:** Removed the redundant `at_menu` branch — the shortcut dispatch now works uniformly regardless of whether you're in the menu or not. Top-row 1 (200) remains the combo detector's "home" anchor.

### Clock Source — Akai Force MIDI Clock
Changed `config/profiles/live-show.yaml` clock preference from `Reaper (OSC)` to `Akai Force (MIDI Clock)`. OSC /beat messages are now ignored; BPM is driven by MIDI clock (0xF8) received from the Force's USB MIDI port. Falls back to Internal 120 BPM when the Force is unplugged. Verified with realistic timing test.

### OSC Bridge — ReaLearn-Ready
Already working: nova-script sends OSC to `127.0.0.1:8000` for every control (volume, bypass, preset select). Added `send_action_str()` to OscBridge for named Reaper action IDs. Created simple setup guide in `docs/REAPER_OSC_SETUP.md` — 3 steps: install ReaLearn, set listen port to 8000, press buttons to learn.

### MIDI Thru — Alesis V25 → Akai Force
New `src/midi/routing.py` — MidiThru class that routes selected MIDI channels between devices. Config-driven via the profile's `midi.thru` list. Added V25 keyboard (channel 1, note-only) → Akai Force route. The V25 keys now play directly into the Force.

### Files Changed
- `src/ui/modes/clip_launcher.py` — `_init_default_colors()`: quadrant layout
- `src/ui/modes/arp_edit.py` — E↔F remap, LENGTH scroll fix, edit cooldown, `is_note_length_mode()`/`exit_note_length()`, Top-1 green back, RED note-length button
- `src/ui/modes/instrument.py` — ARP toggle (D = enable/disable) replacing 3-way cycle
- `src/engine.py` — Right-column swallow fix, Top-1 note-length routing, midi thru setup, simplified shortcut dispatch
- `src/osc/bridge.py` — Added `send_action_str()`
- `src/midi/routing.py` — New: MIDI thru routing
- `src/ui/overlay_manager.py` — 2-press dismiss for top-row/grid, single-press for D-H, `idle_since` reset on ACTIVE_MODE entry, 30s idle timeout, screensaver disable toggle
- `src/ui/mode_manager.py` — `clear_grid()` in `switch_to()`, `_needs_render=False`
- `src/ui/modes/menu.py` — `_needs_render=False` in `enter()`
- `src/ui/modes/performance.py` — `preset_actions` config support
- `src/ui/startup_wave.py` — Fast wave (~1.2s), SLEEP_MS=0.0
- `src/controllers/base.py` — `reset_grid_state()` helper
- `config/profiles/live-show.yaml` — Clock→Force, midi.thru→V25, performance.preset_actions, screensaver disabled, menu items (button 1=PERF, 6=ARP), idle_timeout 30s
- `tools/novation-virtualizer.py` — Full drain MIDI poll, set_info mode relay
- `tools/novation-virtualizer.html` — 9 help screens rewritten, top-row labels
- `docs/REAPER_OSC_SETUP.md` — New: simple ReaLearn setup guide
- `tests/test_arp_edit.py` — Updated for E→F note-length remap, Top-1 exit
- `tests/test_comprehensive.py` — Updated for 2-press dismiss, 6-item menu, quadrant clip launcher

### Test Status
106 comprehensive + all 6 unit suites pass. Engine smoke test confirmed: connects to physical Launchpad, runs startup wave, switches modes.


---

## Entry #43 — 2026-08-08 — Light Show Mode: Live Lighting Cue Controller

### Source
Post-show debrief (2026-08-08). Daniel wants a live-cueable lighting controller on the
Launchpad: select a "mood" (a library of 8-10 scenes), then cue scenes during a song.
Some scenes are pulse/flash (fire a burst, auto-return to the prior scene). Output goes
to the lighting engine over `/tmp/lighting_feed`. Master clock is configurable (Akai
Force MIDI clock now; REAPER OSC / internal are supported alternatives).

### Work Completed
- **New mode** `src/ui/modes/light_show.py` (`LightShowMode`):
  - Mood = one Launchpad "page"; right column A-E selects among 5 moods
    (Standard / Acoustic Candlelight / EDM / High Energy / Ballad).
  - Grid = 8 scenes per mood (2×4 layout). Scenes are `snap` (fade-to & hold) or
    `pulse` (burst then auto-return to the prior scene, or to auto if none).
  - Beat-quantized pulses: a `pulse` cue is held `pending` until the next clock beat,
    then fires for `pulse_beats`, then returns. Flash lands on the grid.
  - Emits `FORCE_LOOK` JSON-lines to `/tmp/lighting_feed` (same feed as TUI +
    iPhone page). Includes `fade_ms` + `scene` + optional `pulse` fields.
  - Exiting the mode releases to auto (`FORCE_LOOK {"look": null}`).
- **Engine wiring** (`src/engine.py`):
  - Mode registered in `_setup_modes`; reachable from the menu (new "LITE" item).
  - `_on_beat` now forwards the beat to the active mode if it implements `on_beat`
    (beat-quantized pulses).
  - `set_bpm` push loop includes `light_show` (clock source agnostic — Force MIDI,
    REAPER OSC, or internal all feed the same BPMClock).
- **Config** (`config/profiles/live-show.yaml`):
  - `modes.light_show`: `feed: /tmp/lighting_feed` + 5 moods × 8 scenes.
  - Scene fields: `{name, look, cue: snap|pulse, fade_ms, pulse_beats}`.
  - `look` references existing engine looks (placeholders — see deferred work).
  - Menu: added `{label: "LITE", mode: "light_show", color: "BLUE_HIGH", x:6, y:6}`.
- **Tests** `tests/test_light_show.py` — 6 tests: moods load, snap cue, mood switch,
  pulse-on-beat-and-return, pulse-with-no-prior→auto, exit→auto. All pass.

### Architecture Notes
- nova-script is a **producer** on `/tmp/lighting_feed`; the lighting engine
  (`showfeed.py`) is the consumer → ShowDriver → engine → QLC+ (DMX) + Govee.
- The BPMClock already supports Force MIDI clock > REAPER OSC > internal, so making
  the light show beat-synced is purely a `set_bpm` + `on_beat` integration — no
  clock logic changes needed.
- `fade_ms` is emitted now but the engine currently applies look changes
  immediately (fade support is part of the deferred look-library revamp).

### Deferred / Next
- **Look library revamp** (the "10x quality" work): current `look` values are
  placeholders. Needs research + a design quiz (Daniel to drive). Smooth crossfades,
  dynamics, and the "blinder-as-separate-light" concept (halogen-curve white flash
  overlaid on a dim base) belong here.
- Wire/verify on real hardware + confirm feed round-trip with a running engine.

---

## Entry #44 — 2026-08-10 — SESSION HANDOFF: Lighting System + Light Show Integration Prep

> **READ ME FIRST.** This is the master handoff for the next session. It covers
> the ENTIRE previous working session (which lived mostly in the **lighting-system**
> repo), everything changed and why, the current hardware/software state, the
> Light Show mode scaffold already built here, and the concrete next steps for
> **integrating the Launchpad lighting controller into nova-script**.

---

### Why this entry exists

The next session starts fresh and must be able to pick up the **nova-script ↔
lighting integration** without re-exploring two codebases. Everything needed to
understand the context is captured here. The lighting-system repo also has its
own detailed BUILD_LOG + DMX.md; this entry is the cross-project bridge.

---

### 1. The full session arc (what happened)

The session was a **day-of-show lighting bring-up + post-show follow-up**, in phases:

1. **Pre-show software prep** — wired the show TUI to emit lighting events; built
   song profiles; verified deployment.
2. **Hardware bring-up** — USB-DMX adapter detected, PL-32M channel map CONFIRMED
   physically, all 4 bars + 3 key lamps driven, full engine→QLC+→DMX pipeline live.
3. **Auto-discovery + unified CLI** — rods auto-discovered by MAC into rig.json;
   `start light-runner` / `stop light-runner` commands; persistent feed pipeline.
4. **SHOW NIGHT (2026-08-08)** — bars + lamps + QLC+ sync worked great. **Rods
   never connected** (diagnosed later: Inseego MiFi client isolation).
5. **Post-show fixes** — rod discovery unicast sweep; designed + scaffolded the
   **Light Show mode** here in nova-script.

---

### 2. LIGHTING-SYSTEM repo — what was changed & why

Repo: `~/Documents/projects/lighting-system/`

#### Hardware (verified physically 2026-08-08)
| Fixture | Role | DMX | Map |
|---------|------|-----|-----|
| BACK_L / BACK_R / CROWD_L / CROWD_R | EndyShow PL-32M bars | 001 / 009 / 017 / 025 | **8CH** |
| KEY_L / KEY_C / KEY_R | key lamps (relay pack) | 200 / 201 / 202 | 1CH on/off |
| GOVEE_L1 / GOVEE_L2 | glow rods | LAN | H802A 4-band |
| GOVEE_R1 / GOVEE_R2 | glow rods (last-minute, unowned) | LAN | auto-adopt |

- **PL-32M channel map CONFIRMED (the big hardware discovery):**
  `8CH = CH1 Master Dimmer, CH2 R, CH3 G, CH4 B, CH5 W, CH6 Strobe, CH7 Func, CH8 unused`.
  The earlier "4CH = R,G,B,W" hypothesis was **WRONG** — a master dimmer comes
  first. Every bar write must set CH1=255.
- **`qlc/fixtures/EndyShow-PL-32M-RGBW-Bar.qxf`** — corrected to the real 8CH map.
- **`engine/lighting_engine/outputs.py`** — `rgbw_bar` now writes
  `ch1=255 (dimmer), ch2-5 = RGBCW, ch6=0 (strobe)`.
- **`engine/rig.json`** — addresses updated to the confirmed layout (see table).
  `show.qxw` regenerated via `qlc/gen_show.py`.
- **`govee/govee.py`** — `discover()` gained a **unicast sweep** (sends the scan
  packet to every IP in the local subnet) as a third discovery mechanism after
  multicast + broadcast. This is the rod fix.

#### Rod discovery failure (show night) — ROOT CAUSE + FIX
- **Symptom:** rods re-paired to the show WiFi but never found; DMX worked fine.
- **Cause:** the show network is an **Inseego MiFi (Verizon, no SIM)** which
  enables **client/AP isolation** → broadcast + multicast between clients are
  dropped. Old discovery used only those.
- **Fix:** unicast sweep. `engine/discover_rig.py` (runs at `start light-runner`)
  calls `discover()` → gets the fix automatically.
- **Still to test on real hardware:** if the MiFi blocks unicast too, disable
  AP/client isolation in the MiFi admin (http://192.168.1.1). Protocol in
  `docs/show-wifi-switch.md`.

#### Auto-discovery (`engine/discover_rig.py`) — NEW
- Scans LAN, matches rods to `rig.json` slots by **device MAC** (stable) so
  left/right placement survives network changes.
- **Auto-adopts** unmatched rods (the 2 last-minute ones) into R1/R2.
- Does **surgical string edits** to rig.json (preserves hand formatting).
- Exit 0 if ≥1 rod found; no rods → DMX still works.

#### Unified CLI (in `~/Music/iPhoneLiveServer/scripts/`)
- `start-light-runner` — QLC+ (`-w`), rod discovery, feed pipeline. `disown`-safe.
- `stop-light-runner` — tears down feed + QLC+.
- `lighting_pipeline.sh` — self-waiting launcher so the `tail | showfeed` pipe
  survives shell/session teardown (the hard-won stability fix).
- `start-show` calls `start-light-runner`; `.zshrc` `start`/`stop` dispatch on
  `show server` vs `light-runner`.
- **Feed = `/tmp/lighting_feed`, a regular file.** TUI, iPhone page, demo, and
  (soon) nova-script all **append JSON lines**; `showfeed.py` consumes them.

#### Song profiles + generator
- `engine/song_profiles/*.json` — 9 profiles for the strong songs.
- `engine/gen_profile.py` — `python3 gen_profile.py "Song" --genre rock` for
  last-minute setlist picks.

#### Show-night lesson (drives the Light Show feature)
The set was ~70 songs, mostly **unplanned/on-the-fly** (requests + guests). This
proved the auto-engine can't be the only path — the user needs a **manual live
cue controller** to run the lights in the moment.

---

### 3. NOVA-SCRIPT — what was built this session

See also **Entry #43** for the detailed Light Show entry. Summary:

- **`src/ui/modes/light_show.py`** (`LightShowMode`) — NEW:
  - Mood = Launchpad page; right column **A-E = 5 moods** (Standard / Acoustic
    Candlelight / EDM / High Energy / Ballad).
  - Grid = **8 scenes/mood** (2×4 layout). Scene `cue`: `snap` (fade & hold) or
    `pulse` (burst on next beat, auto-return to prior scene or to auto).
  - Writes `FORCE_LOOK` JSON-lines to `/tmp/lighting_feed` (producer; the
    lighting engine is the consumer → QLC+ + Govee).
  - `fade_ms` + `scene` + `pulse` fields emitted now; engine honors fade once
    the look-revamp lands (today look changes are immediate).
  - Exiting releases to auto (`FORCE_LOOK {"look": null}`).
- **`src/engine.py`** — registered the mode (menu "LITE" item); `_on_beat`
  forwards the beat to the active mode if it has `on_beat`; `set_bpm` push loop
  includes `light_show`. Beat + BPM come from the existing **BPMClock**
  (Akai Force MIDI clock > REAPER OSC > internal) — so the light show is
  master-clock agnostic by construction.
- **`config/profiles/live-show.yaml`** — `modes.light_show` block: feed path +
  5 moods × 8 scenes. Scene = `{name, look, cue, fade_ms, pulse_beats}`.
- **`tests/test_light_show.py`** — 6 tests, all pass (snap cue, mood switch,
  pulse on-beat + return, pulse-no-prior → auto, exit → auto).
- `look` values are **placeholders** referencing existing engine looks — the
  look-library revamp (deferred) will replace them.

---

### 4. Deferred / NOT done (deliberately)

1. **Look library revamp ("10x quality").** From the debrief: lighting was too
   jumpy (hard on/off + color snaps instead of smooth fades + dynamics). The
   user wants in-depth research + a **design quiz** (multiple models) before
   rebuilding looks. This is the next big creative project.
2. **Blinder-as-separate-light.** Bars at ground level angled up = intense
   backlight/blinder. Keep base scenes dim; overlay a **white crowd-blinder
   flash** with a halogen-like smooth on/off curve that flashes and returns.
   Design with the look revamp; the Light Show `pulse` mechanism already models
   the "flash and return" behavior.
3. **Rod discovery real-hardware test** on the MiFi (needs rods + MiFi present).
4. **Master clock source change** is config-only (`clock.preferred`) but the
   "flexible" story (Force vs REAPER) is untested end-to-end for lighting.

---

### 5. NEXT STEPS for the integration session (start here)

Priority order:

1. **Real-hardware wire-up + verify the Light Show mode:**
   - Boot the lighting pipeline (`start light-runner`) with bars + rods on the
     same network.
   - Run nova-script (`./scripts/run.sh`), go to menu → LITE, select a mood,
     cue scenes → confirm bars + rods follow.
   - Test a `pulse` scene flashes and returns on the beat.
   - Note: `FORCE_LOOK` needs the engine running with a song context OR the
     `SHOW_BLACKOUT`/preshow path. Confirm behavior when the show server is NOT
     running a song (may need a driver tweak so manual scenes work standalone).
2. **Review the Light Show UX on the Launchpad** with the user: mood/scene
   layout, colors (MK1 palette: amber/red/green + limited others), whether the
   grid 2×4 arrangement feels right, and whether pulse scenes want a distinct
   visible indicator.
3. **Decide the look-revamp approach** (research + quiz) and rebuild
   `looks.json` with fade times + dynamics; then wire `fade_ms` handling into
   the engine's scene application (crossfade).
4. **Rod discovery test on the MiFi** using `docs/show-wifi-switch.md` §0b.
5. Update `docs/BUTTON_REFERENCE.md` + virtualizer page label for `light_show`.

### 6. Quick file map (for the new session)

| Concern | File |
|---------|------|
| Light Show mode | `nova-script/src/ui/modes/light_show.py` |
| Mode registration / beat forward / set_bpm | `nova-script/src/engine.py` |
| Mood/scene config | `nova-script/config/profiles/live-show.yaml` (`modes.light_show`) |
| Light Show tests | `nova-script/tests/test_light_show.py` |
| Feed emitter target | `/tmp/lighting_feed` (regular file) |
| Feed consumer | `lighting-system/engine/showfeed.py` |
| Look library (to revamp) | `lighting-system/engine/looks/looks.json` |
| Rig addressing + rod IPs | `lighting-system/engine/rig.json` |
| Rod discovery (MAC match) | `lighting-system/engine/discover_rig.py` |
| Govee discovery (unicast sweep) | `lighting-system/govee/govee.py` |
| Lighting boot command | `~/Music/iPhoneLiveServer/scripts/start-light-runner` |
| Show-night protocol / test | `lighting-system/docs/show-wifi-switch.md` |

### 7. Gotchas to remember
- QLC+ 5.2.2 **requires `-w`** for the web API (missing from `--help`).
- `killall qlcplus-qml` before relaunch (two instances fight over :9999).
- `/tmp/lighting_feed` is a **regular file** — append JSON lines; don't truncate
  it mid-run (confuses `tail -f`).
- The feed pipeline dies if the parent shell exits unless launched detached
  (`lighting_pipeline.sh` + `nohup`/`disown`).
- Feed writes from nova-script: opening the file in append mode is fine (same
  as the TUI's `fs.appendFileSync`). If the engine isn't consuming, writes still
  succeed (file just grows) — safe.
- MK1 Launchpad palette is limited (~9 usable states) — plan LED colors around
  amber/red/green + the few extras available.

## Entry #45 — 2026-08-10 — ReaLearn OSC Setup, V25→Force/M-Audio Routing, Force Key Transpose Research

### Source
Daniel via Claude Code. Pre-show session focused on getting the guitar/vocal FX rig talking to Reaper and routing the V25 keyboard into the Akai Force.

### ReaLearn OSC Setup (the easy path)
- **`docs/REAPER_OSC_SETUP.md`** rewritten as a 3-step guide: install ReaLearn, set OSC listen port `8000`, press pads → "Learn source" → map to anything.
- **`127.0.0.1` = localhost forever** — clarified that wifi IP changes don't matter because both Reaper and nova-script run on the same MacBook.
- ReaLearn fields: local listen port `8000` (hears nova-script), device IP `127.0.0.1` (send-back, optional), device port `9001` (nova-script's listen side).
- `config/nova-script.ReaperOSC` already handles track volume/FX bypass/preset; ReaLearn is the manual "hit button → map" path for amp preset switching.
- **`src/osc/bridge.py`** — added `send_action_str(action_name)` sending `/action/str <command_id>`.
- **`src/ui/modes/performance.py`** — reads `performance.preset_actions` from config, sends named Reaper actions on FX preset select (keyed `GTR_2`, `VOX_2`, 6 presets = 3 pads × 2 banks).

### Akai Force USB MIDI — NOT detected (open issue)
The Force never appeared as a MIDI device during the session despite being plugged in. Verified at every level:
- `rtmidi` ports: only `V25 Out`, `V25 EDITOR Out`, `Live Show Manager` (IN) and matching OUT.
- `ioreg -p IOUSB` — no Akai/Force/MPC entry.
- Audio MIDI Setup — no Force entry.

The earlier "Akai Force" in the port list was the **virtualizer's virtual port**, not hardware. The Force is either not being recognized by macOS (cable/hub/power), or firmware 3.9 presents MIDI differently. Left as an open issue — user switched to the M-Audio interface's physical MIDI OUT instead.

### MIDI Thru — V25 → M-Audio interface (physical MIDI OUT)
- **`src/midi/routing.py`** — `MidiThru` class: routes selected MIDI channels, note-only filter.
- Config `midi.thru` now routes `V25 Out` → `M-Audio` (channel 1, note-only). The M-Audio interface's MIDI OUT goes via a MIDI cable into the Force's MIDI IN.
- **`src/main.py`** — new `nova-script list-ports` command to discover the exact interface name at runtime (adjust the config `target` to match).
- Note-only = knobs/buttons on the V25 are NOT forwarded; only keybed note on/off.

### Force Settings Research — receive + transpose + scale lock (for the user)
Instructions given to set the Force to:
1. **Receive MIDI** — tap track → Track Settings → MIDI tab → MIDI Input On → channel 1 → load a plugin.
2. **Transpose** — set track Transpose to a semitone offset (C→G = +7).
3. **Scale lock** — enable Scale mode, pick key + scale so wrong notes snap in-key.

Semitone reference table provided (C=0, D=+2, E♭=+3, E=+4, G=+7, A=+9, B♭=+10).

### Files Changed
- `docs/REAPER_OSC_SETUP.md` — Rewritten: simple ReaLearn 3-step guide
- `src/osc/bridge.py` — `send_action_str()`
- `src/ui/modes/performance.py` — `preset_actions` config support
- `src/midi/routing.py` — New: `MidiThru` class
- `src/main.py` — `list-ports` command
- `config/profiles/live-show.yaml` — `midi.thru` V25→M-Audio (was V25→Force), clock→Force, ReaLearn comments
- `src/engine.py` — `midi.thru` config wiring in `_setup_controllers()`

### Test Status
106 comprehensive + all 6 unit suites pass. Engine smoke test: connects Launchpad, sets up MIDI thru, switches to performance mode.

### Open Items / Next
1. **Force USB MIDI** — needs the physical cable/power investigation. When it appears in `nova-script list-ports`, switch the `midi.thru` target back to "Akai Force" for direct USB routing (or keep M-Audio MIDI cable path).
2. **Verify V25→M-Audio→Force** on hardware with a MIDI cable.
3. **ReaLearn mapping** — user maps Launchpad pads to Reaper FX/actions at soundcheck.
4. **The look-library revamp** (Entry #44) remains the biggest creative item for lighting.

## Entry #46 — 2026-08-10 — Alesis V25 as a First-Class Device + MIDI Thru Fix

### Source
Daniel via Claude Code. V25 → Force routing debug session.

### Root Cause of "nothing registering on the Force"
Two bugs compounded:
1. **Channel filter dropped the knobs** — the V25 sends keys + mod wheel on **channel 1**, but the 4 knobs on **channel 3** (CC 20-23). The original `channels: [0]` filter silently dropped the knobs/buttons, so only the keybed ever reached the Force.
2. **V25 input never connected** — `MidiManager._try_connect_device` required BOTH an input AND output port match. The V25's USB presents asymmetrically: `V25 Out` exists only in the *input* list (the output list has `V25 In`). So the source device matched nothing and never opened, and its target (`M-Track Plus`) wasn't registered as an output at all → `send_message` silently no-op'd.

### Fixes
- **`src/midi/manager.py`** — `register_device` now supports `input_only`, `output_only`, `input_pattern`, `output_pattern`. New helpers `register_input()` / `register_output()`. `_try_connect_device` and `_check_connection_health` handle one-sided devices (a `-` in the log means "no port on this side").
- **`src/controllers/alesis_v25.py`** (NEW) — `AlesisV25` class. Not a Novation device; registers input-only under the name **"Alesis V25"** with a hardware description (25 keys, 4 knobs CC20-23, mod wheel CC1, pitch wheel, 4 buttons, 8 drum pads). Forwards all MIDI to the target with optional CC remap.
- **`src/engine.py`** — reads `midi.v25` config block, instantiates `AlesisV25`. Kept the generic `midi.thru` loop for future routes.
- **`config/profiles/live-show.yaml`** — new `midi.v25` block: `target: M-Track Plus`, `input_pattern: V25`, `cc_remap: {1: 16}` (mod wheel → CC 16).

### Verified at runtime (real hardware)
```
Registered device: Alesis V25
Alesis V25 registered (25 keys, 4 knobs (CC20-23), mod wheel (CC1), pitch wheel, 4 buttons, 8 drum pads) → MIDI thru to M-Track Plus
Connected Alesis V25: in=V25 Out (0), out=- (-)
Connected M-Track Plus: in=- (-), out=M-Track Plus (2)
```

### Files Changed
- `src/midi/manager.py` — input_only/output_only/pattern support, register_input/register_output
- `src/controllers/alesis_v25.py` — New: first-class V25 device
- `src/engine.py` — `midi.v25` wiring
- `config/profiles/live-show.yaml` — `midi.v25` block (replaced `midi.thru` V25 route)
- `tests/test_midi_routing.py` — +2 tests (V25 forwarding, one-sided registration)

### Test Status
106 comprehensive + midi_routing (7) + all other suites pass.

### Note
The mod wheel is remapped CC1→CC16 so the Force's MIDI-learn can assign it (e.g. tremolo rate) without colliding with the Force's own modulation handling. Knobs stay on their native CC20-23 / channel 3. To change mappings, edit `midi.v25.cc_remap`.

### Follow-up fix (same session) — Virt sync log spam
When launched WITHOUT the virtualizer flag, the `_virt_sync_loop` tried to connect to `ws://localhost:8766` every 0.2s and logged a "Virt sync error" each time it failed → log flood. Fixed with exponential backoff: on failure it now retries at 1s→2s→4s→...→15s max with **no log output**; on success it logs once and syncs at 0.2s. Zero spam, and the virtualizer auto-connects the moment it's started.

## Entry #47 — 2026-08-13 — Light Show Integration: Standalone Cueing, Fades, Blinder Look

### Source
Daniel via Claude Code. Picked up Entry #44's handoff: wire the Light Show mode's
`FORCE_LOOK` cue path through to the lighting engine so it works standalone and
crossfades. (The look-library revamp/design-quiz remains deferred — see open items.)

### Problem (from Entry #44 gotchas)
The Light Show mode was built on the nova-script side, but the cue path was broken
for real use:

1. **Manual cueing did nothing without a song.** `ShowDriver.on_force_look()`
   only set `_forced_look`; the look applied inside `on_beat()`, which returns
   early when no profile is loaded (no song running). And with no song there are
   no beats at all — so standalone use was impossible.
2. **`fade_ms` was dropped.** `showfeed.py` only forwarded `look`; the fade,
   scene, and pulse fields the mode emits were ignored — look changes snapped.
3. **A scene referenced a non-existent look.** The EDM mood's "Blinder" scene
   pointed at `look: "Crowd Blinder"`, which did not exist in `looks.json`.
   Unknown looks silently fall back to auto at show time (no error visible).

### Fixes (lighting-system repo)

**`engine/lighting_engine/driver.py`** — `on_force_look()` now applies IMMEDIATELY:
- With no song, it synthesizes a manual `MusicalState` and calls
  `engine.force_look()` right away (standalone cueing works).
- `FORCE_LOOK {look: null}` with no song fades to Blackout instead of leaving the
  rig stuck on the last cue (exit-Light-Show behavior).
- Unknown look: logs a warning, falls back to auto step (song) or Blackout (no song).
- Added `_apply_scene()` / `_fade_to()` / `_fade_interp()`: a blocking stepped
  crossfade (40ms slices) that interpolates color channels over `fade_ms`.
- `on_beat()` guards against re-applying the forced look mid-fade (would snap the
  crossfade). `on_song_start()` clears any in-flight fade.

**`engine/showfeed.py`** — `FORCE_LOOK` handler now passes `fade_ms` through to
`on_force_look()`. Docstring updated.

**`engine/looks/looks.json`** — added **"Crowd Blinder"** look: full icy-white
pulse (bars + back at 1.0, key lamps dark), `blinder_hit`/`crowd_blinder_sparkle`/
`static` effects. Pre-validated placeholder for the deferred blinder-as-separate-
light concept. Look count: 32 → 33.

**`engine/tests/test_driver.py`** — updated the two stale force-look tests to the
new immediate-apply contract; added 4 tests: standalone no-song apply, standalone
release→blackout, unknown-look→blackout, monotonic crossfade ramp, fade-0 snap.
33 tests green.

### nova-script side

- **`tools/validate_light_config.py`** (new) — cross-checks every mood scene's
  `look` ref in `config/profiles/live-show.yaml` against `looks.json` (exit 0/1/2).
  Verified: 5 moods, 40 scenes, all refs resolve (incl. the new Crowd Blinder).
- **`docs/BUTTON_REFERENCE.md`** — new **Light Show Mode** section (mood selectors,
  scene colors, snap/pulse, standalone + crossfade behavior, feed format); updated
  Menu Mode + Universal Controls to the 7-item config (LITE, config-driven shortcuts).
- **`tools/novation-virtualizer.py`/`.html`** — top-row labels now HOME/Clip/Seq/Mix/
  Inst/ARP/Lite; added `light_show` help panel; menu help updated to 7 blocks.

### Stale test repairs (pre-existing failures, aligned to documented behavior)
- `tests/test_engine_integration.py` — top-row shortcuts now assert the config-driven
  mapping (ctrl N → menu items[N-200]; Entry #40), not the pre-#40 hardcoded table.
- `tests/test_overlay_dismiss.py` — combo fires on partner press (Entry #9); overlay
  dismiss is 2-press for grid/top-row, single-press for D-H (Entry #42); fixed
  `GridEvent`/`ControlEvent` constructor usage.

### Test Status
- nova-script: all 16 suites GREEN (incl. light_show, comprehensive).
- lighting-system: 33 tests GREEN; verified end-to-end: `FORCE_LOOK` with `fade_ms`
  through `showfeed.py --backends console` renders a monotonic color ramp.

### Open Items / Next
1. **Look-library revamp ("10x quality")** — still the biggest creative item. Needs
   research + design quiz before rebuilding `looks.json` (fade times, dynamics,
   blinder-as-separate-light done as a placeholder).
2. **Real-hardware wire-up** — boot `start light-runner` with bars/rods, run
   `nova-script live-show`, menu → LITE, cue scenes, confirm bars + rods follow and
   a pulse flashes + returns on the beat.
3. **Rod discovery test on the MiFi** (`docs/show-wifi-switch.md` §0b).
4. **Feed round-trip while the show server runs a song** — manual scenes + auto
   engine coexistence.

## Entry #48 — 2026-08-14 — V25→Force Hardware Verification Complete (wrap-up)

### Source
Daniel via Claude Code. Picked up Entry #46's open item: confirm the V25 → M-Audio
M-Track Plus → Force MIDI path end-to-end on real hardware and lock in the final
Force-side MIDI-learn mappings.

### Result — VERIFIED WORKING
The chain **Alesis V25 (USB) → nova-script MIDI thru → M-Track Plus MIDI OUT (DIN) → Akai Force MIDI IN** is confirmed working on hardware. Nothing further to fix in the routing code.

Final Force-side MIDI-learn mappings in use:
- **Mod wheel** → tremolo on the EP. Delivered as CC16 (remapped from native CC1 via `midi.v25.cc_remap: {1: 16}`) so it doesn't collide with the Force's own modulation handling.
- **4 knobs** (native CC20-23, channel 3) → effect control on keys. Passed straight through — no remap needed, learned directly on the Force.

### How to reproduce / change
Edit `config/profiles/live-show.yaml` → `midi.v25` block:
- `target: "M-Track Plus"` — the physical DIN out to the Force.
- `input_pattern: "V25"` — matches the USB input port.
- `cc_remap: {1: 16}` — mod wheel → CC16 for the Force's MIDI-learn.
Knobs stay native (CC20-23). Run `python -m src.main` (or `nova-script list-ports` to confirm device names).

### Notes / Gotchas
- The Force still does **not** enumerate as a USB MIDI device on macOS (see Entry #45). The M-Audio DIN path remains the working route — keep `midi.outputs.force` config in place for when/if USB enumeration gets fixed.
- Entry #46's duplicate numbering was corrected here: the Light Show Integration entry (2026-08-13) is now **Entry #47**.

### Test Status
Unchanged from Entry #46 (106 comprehensive + midi_routing + all suites green) — this session was hardware verification only, no code changes.

## Entry #49 — 2026-08-14 — Lighting Revamp: Rod Discovery + Design Quiz + "Sits and Vibes" Engine

### Source
Daniel via Claude Code. Four focused chunks: (1) rod discovery hardening, (2)
lighting research + deep design quiz, (3) the "10x quality" look-library revamp
engine, (4) Launchpad wire-up (still pending). This entry covers 1–3.

### Chunk 1 — Rod discovery (lighting-system)
Real-hardware MiFi test not possible today (home network, no rods/MiFi), so
hardened the code instead. **Found + fixed two real bugs in `discover_rig.py`:**
- `replace_ip` only matched quoted IPs; empty slots are `"ip": null`, so
  **adopting a last-minute rod never wrote its IP** (device/tag written, IP
  stayed null). Regex now matches `null` too.
- Exit code counted stale IPs as "live"; now only counts IPs assigned this run,
  so `found=[]` → exit 1 correctly.
Extracted the merge logic into a testable `update_rig()` and added
`engine/tests/test_discover_rig.py` (7 tests: MAC re-match after subnet change,
last-minute adoption, mixed, no-devices, formatting, no-double-adopt).

### Chunk 2 — Research + deep Design Quiz (lighting-system)
Compiled `docs/LOOK-REVAMP-BRIEF.md` (430 lines): diagnosis of the "jumpy"
complaint, research applied to this rig, and a live answers record. Grounded in
6 sources (UKING blinder + small-stage guides, Sundrax movement/rhythm, Klarity
warm-cool transitions, Wikipedia, Learn Stage Lighting).

**The governing rule (Daniel):** *"Good pro stage lighting sits and vibes — it
doesn't jump around like party lights."* Hold looks, breathe/drift/wash inside
them; stillness makes the peaks land.

**Design decisions captured (multiple quiz rounds):**
- 5 moods = *feelings*, not genres (Standard / High Energy / EDM / Acoustic
  Candlelight / Ballad).
- Energy axis = 3 levels + separate Peak; energy = the full package
  (brightness + motion + warmth).
- Manual mode = **mood on one Launchpad axis, energy on the other.**
- Hard rules: no red+blue same scene (cops near road), no strobe/flashy (drunk
  crowd + festival photosensitivity practice), don't distract drivers, halogen
  curves everywhere (`on → 10%`, never `on → off` except deliberate blackout),
  blinder warms as it dims (never pure white except full), key lamps always
  warm-white, rods = quiet atmosphere layer.
- Vibing primitives = breathing + color drift + spatial wash (deep-dived in
  §2.6, combined into a mood matrix §2.6.4).
- EDM = "takes the viewer on a journey" (tension/release, high-contrast↔
  monochrome, BPM-synced strobes that follow the Force tempo, low valleys
  building to extreme peaks) — deep-dived in §2.7.
- Auto: genre drives mood, overridable per song via a `mood:` metadata line;
  auto changes = "hold + vibe within", crossfade on section boundaries.

### Chunk 3 — Lighting Revamp (lighting-system + iPhoneLiveServer)

**`engine/lighting_engine/engine.py`:**
- **Halogen blinder** — `_apply_halogen()` (fast smoothstep attack, slow trailing
  decay to a dim floor) + `_halogen_color()` (tungsten amber→white, warms as it
  dims). `render()` honors `effect.curve == "halogen"`.
- **Pulse gating** — `family: "pulse"` looks excluded below energy 0.85, so the
  blinder can't leak into a quiet mood.
- **Mood biasing** — `_style()` merges the mood's palette/look/motion/contrast
  over the genre style.

**`engine/lighting_engine/state.py`:** `MOODS` (5 moods × palette/look/motion/
saturation/contrast) + `mood_for(genre)` seed map; `SongProfile.mood`.

**`engine/lighting_engine/driver.py`:** auto-path crossfade on look change
(`default_fade_ms` 2000ms); fixed latent `_fade_until` bug (was set even when no
fade happened); `on_song_start` accepts `mood` (falls back to `mood_for(genre)`).

**`engine/effects/effects.json`:** new `halogen_blinder` effect.

**`engine/looks/looks.json`:** `Crowd Blinder` → `halogen_blinder`, gated to
energy 0.85–1.0 / `final_chorus`/`big_moment`/`solo`.

**`engine/showfeed.py`:** `SONG_START` passes `mood`.

**iPhoneLiveServer:** `server/api/songs.js` surfaces `mood` (from `meta.json`);
`scripts/tui.js` emits real genre (from genre-map) + mood on `SONG_START`
instead of hardcoded `country_rock`. Both `node --check` clean.

### Test Status
- lighting-system: **45 passed** (was 33) — +5 driver tests (genre→mood, mood
  override, halogen envelope/color, auto crossfade) + 7 discover_rig.
- nova-script: light_show suite + `validate_light_config.py` still green.
- Verified end-to-end: `SONG_START {genre:rock, mood:EDM}` → `Crowd Blinder`
  renders on the halogen curve `(255,166,72)`→`(255,223,189)`→warm amber.
- No red+blue risk in any of the 21 palettes.

### Open Items / Next
1. **Launchpad wire-up (chunk 4)** — boot `start light-runner` + nova-script,
   menu → LITE, cue scenes on hardware.
2. **looks.json content rebuild** — the palette/effect-pool content per look is
   the highest-taste part; not done (proposal pass or palette-by-palette next).
3. **Per-song `mood:` tags** in `~/ReaperSongs/<Song>/meta.json` — mechanism is
   ready; add the actual tags.
4. **Real-hardware verify** of halogen curve + crossfades + rod discovery (MiFi).

## Entry #50 — 2026-08-14 — Launchpad Light Show Verified on Hardware + Rod Test Attempt

### Source
Daniel via Claude Code. Chunk 4 of the lighting-revamp session: wire the Light
Show mode to the physical Launchpad and test rod discovery on the venue WiFi.

### Launchpad wire-up — VERIFIED on real hardware
Added `tests/hardware_light_show.py` — connects the physical Launchpad Mini and
drives it through the full Light Show lifecycle (no QLC+ / lights needed):
- **8 scene pads + mood column lit** on enter (rendered via `get_grid_color`).
- **snap cue** → `FORCE_LOOK` written to the feed with correct `look`/`fade_ms`.
- **mood switch** (right column A→B) re-renders and resets the current scene.
- **pulse cue** fires on-beat (`pulse: true`), then returns to the prior *scene*
  (fixed a weak earlier assertion that two scenes mapped to the same look and
  masked the return). Verified `_current_scene` transitions Candle→Swell→Candle.
- **exit** clears the grid and releases to auto (`FORCE_LOOK {look: null}`).

Full engine boot (`nova-script live-show`) also verified: Launchpad connects,
all 9 modes register incl. `light_show`, no errors. End-to-end producer→consumer
confirmed: Launchpad feed → `showfeed.py` → engine renders `Crowd Blinder` on
the halogen curve `(255,166,72)`.

### Rod test attempt (venue WiFi)
Target: the single Govee rod on the "PeaceFreak" WiFi. Blocked by networking:
- The Mac is on the **home** network (192.168.1.x, `router.home.local`), not
  PeaceFreak. Rod discovery on 192.168.1.x finds nothing.
- macOS redacts all SSIDs in CLI output (`<redacted>` in `system_profiler`,
  `wdutil`, `ipconfig`), so the current/available SSID list can't be confirmed
  from the shell.
- `networksetup -setairportnetwork en0 peacefreak` fails with -3900 (network
  not joined — likely out of range or wrong SSID). Password IS in the System
  keychain (acct="peacefreak", "AirPort network password").

**Next:** join PeaceFreak manually (menu bar Wi-Fi) or confirm the rod's actual
network, then re-run `engine/discover_rig.py --timeout 6`.

### Rod test — RESOLVED on second attempt
Daniel re-joined the light to the network; the rod was actually reachable on the
**home** network (192.168.1.x), not PeaceFreak. `discover_rig.py --timeout 8`
found it via the **unicast sweep** and auto-adopted it:

```
found: SKU=H802A  IP=192.168.1.234  device=11:2A:DB:E6:45:46:64:54
adopted GOVEE_R1 -> 192.168.1.234 (device 11:2A:DB:E6:45:46:64:54)
```

This validates both chunk-1 fixes on real hardware:
- **Unicast sweep** discovered the rod (client-isolation-proof path).
- **Adoption wrote the IP** (the `replace_ip` null-handling fix — the old code
  would have left `"ip": null`).

Full command round-trip verified: `devStatus` query returned `onOff:1,
brightness:100`; `FORCE_LOOK "Warm Ambient"` via `showfeed --backends govee`
turned it amber `(178,67,11)`; `Blackout` returned it to `(0,0,0)`.

### Warm white ladder (lighting-system palettes)
Tuned live on the rod → 4-rung warm ladder: `neutral_white` (200,200,200) →
`warm_white` (255,185,115 @3000K) → `candle_white` (255,140,45 @2300K) →
`candle_warm` (255,110,20 @1800K, new). Looks `Acoustic Hush`/`Intimate`/
`Warm Ambient` re-pointed to candle palettes; Acoustic Candlelight + Ballad
moods re-biased. Full details in lighting-system BUILD_LOG.

## Entry #51 — 2026-08-14 — Alesis V25 Velocity Curve (Piano Feel)

### Source
Daniel via nova-script. The V25 keybed plays far too soft: he has to hit the
keys super hard to get the same volume as a normal hit on the Force's own
keys. Wanted the keyboard to feel much more like a real piano.

### What was built

Velocity shaping in the Alesis V25 MIDI thru (`src/controllers/alesis_v25.py`):

- New `apply_velocity(in_vel, curve, power, boost, floor)`:
  - `linear` — flat gain `out = in * boost` (`boost=1.0` is identity).
  - `piano` — power curve `out = 127 * (in/127)^(1/power)`, boosts soft/medium
    hits so a normal press lands near full strength while hard hits still reach
    127 (default `power=2.0` = square-root curve).
  - `floor` keeps very soft hits audible (default 1).
- Applied on **note-on only** (velocity > 0). Velocity 0 (running-status
  note-off) is never raised, so notes always release cleanly. Note-offs, CCs,
  pitch bend pass through untouched.
- `AlesisV25` gained a `velocity` kwarg; default is `linear` (passthrough) so
  behavior is unchanged unless configured.

Curve spot-checks (piano, power 2.0): `5→25, 15→44, 30→62, 50→80, 70→94,
90→107, 110→118, 127→127`.

> Tuned on request: `power` bumped **2.0 → 3.0** so soft hits come out harder
> still. New spot-checks (piano, power 3.0): `5→43, 15→62, 30→78, 50→93,
> 70→104, 90→113, 110→121, 127→127`.

### Config

`config/profiles/live-show.yaml` → `midi.v25.velocity`:
```yaml
    velocity:
      curve: "piano"   # linear | piano
      power: 3.0       # curve strength (1.0 = linear; >3.0 = more low-end boost)
      boost: 1.0       # extra flat gain multiplier (linear + piano)
      floor: 8         # minimum output velocity for very soft hits
```
Tuning on the rig: raise `power` for a stronger boost, or switch to
`curve: linear` with `boost: 1.3` for a simple flat gain.

### Verified

- `.venv/bin/python -m pytest tests/test_midi_routing.py` → **10 passed**
  (new: default identity passthrough, piano curve 40→71 / 127→127 / vel-0 note-off
  stays 0 / CCs untouched, linear boost 100→127 clamp & 40→52).
- `tests/test_engine_integration.py` → **13 passed**.
- Config parses; engine passes `midi.v25.velocity` through to the controller.

### Files

| File | Changes |
|------|---------|
| `src/controllers/alesis_v25.py` | `apply_velocity()` + `velocity` kwarg, note-on velocity shaping in `handle_raw_midi` |
| `src/engine.py` | Pass `v25_cfg.get("velocity")` to `AlesisV25` |
| `config/profiles/live-show.yaml` | New `midi.v25.velocity` block (piano curve enabled) |
| `tests/test_midi_routing.py` | +3 velocity tests |
| `BUILD_LOG.md` | This entry |

### Next

- Hardware check on the rig: play the V25 keys → confirm the Force gets the
  boosted velocities (and the mod wheel still arrives as CC16). Tune `power`
  if the low-end still feels weak.

## Entry #52 — 2026-08-15 — Light Show Mode v2: Mood-Row Layout + Peak Hold + Help Text

### Source
Daniel via Claude Code. Live-hardware session: got manual lighting control on the
Launchpad working for the show. Redesigned `LightShowMode` to be self-explanatory.

### Fixed: config bug (the "pads not lighting up" root cause)
The `light_show` block lived under `modes.light_show` in `live-show.yaml`, but the
engine read `config.get("light_show")` (top-level) → the mode loaded with
`moods=[]` and rendered nothing. Changed to
`config.get("modes", {}).get("light_show", {})`.

### v2 layout (intuitive, no manual needed)
- **Moods are ROWS** (5 rows top→bottom: Standard / Acoustic Candlelight / EDM /
  High Energy / Ballad); **8 scenes per mood laid out left→right**.
- **Right column A–E** = mood identity light (amber/red/green × brightness) AND a
  **momentary PEAK button**: hold → fire that mood's peak (blinder/sparkle,
  tailored per mood), button blinks at BPM while held, release → return to the
  prior scene. Peak looks are config (`peak:` per mood in live-show.yaml).
- **Scene pads**: amber = snap (hold), red = pulse (burst + auto-return), green =
  the currently-active scene. Pulse auto-return is preserved (beat-quantized via
  `on_beat`).
- **Help text**: replaced the HUD-overlay scrolling text (hard to read, replaced
  the grid, consumed presses) with an **in-grid 5×5 scrolling hint in RED** —
  same glyph style as the guitar screen. Shows the scene name (or "<mood> PEAK").
- **Entry sweep** animation reveals mood rows top→bottom on enter.

### Top-row mode shortcuts (the other "buttons not lighting up" issue)
Buttons 2–8 were used as mode shortcuts but their LEDs were never lit. Added
`_render_top_row_shortcuts()` (lights buttons 2–8 in each menu item's color,
called on setup + reconnect) and fixed an off-by-one in the shortcut mapping
(button 2 = items[0], not items[1]; PERF is now reachable from the top row).

### Tests
- `tests/test_light_show.py` rewritten for v2 (10 tests: mood rows, snap/pulse
  cue, peak hold+release, grid-event routing, help text, render colors).
- `test_engine_integration.py::test_top_row_shortcuts` updated to the corrected
  button→item mapping.
- Full suite: 97 passed (1 pre-existing virtualizer-e2e error, needs its backend).

### Notes
- Peak `look` choices are first-pass taste (`live-show.yaml` → `peak:`); easy to
  tune per mood.
- BPM clock falls back to Internal 120 (no Akai Force on USB) — pulse/peak blink
  runs at that tempo.

## Entry #53 — 2026-08-20 — Direct semantic busking bank

### Purpose
The mood-row layout is useful for exploration but did not give a live operator
obvious actions such as chorus, glimmer, strobe, blinder, and blackout. Added a
two-row direct cue bank at the bottom of the Launchpad.

### Direct cues
- Row 0: Base, Verse, Build, Chorus, High, Solo, Glimmer, Blackout.
- Row 1: Warm, Wide, Drum, Strobe, Blinder, Finale, Crowd, Cool.
- Pulse cues remain beat-quantized and return to the prior scene.
- Mood rows and A-E mood peak buttons remain available above the direct bank.

### Verification
- Direct cue rendering and feed emission covered by `test_light_show.py`.
- Relevant nova-script tests remain green after the change.
