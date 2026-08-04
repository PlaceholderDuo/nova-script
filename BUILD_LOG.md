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

