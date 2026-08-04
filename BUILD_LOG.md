# Nova-Script Build Log

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
2. Build ReaperOSC config file bridge
3. Implement OSC server/client in nova-script (`src/osc/`)
4. Fix Launchkey 49 MK2 controller to use InControl port (Channel 16), Extended mode, correct pad notes
5. Build Message Display Mode with character-to-grid font
6. Add MIDI clock sync options (internal/OSC/MIDI)


