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

## Entry Template (for future entries)

### Entry #X — YYYY-MM-DD — Title

#### Source
[Who requested / where did this come from]

#### Changes Made
- [Change 1]
- [Change 2]

#### Rationale
[Why these changes]

#### Files Affected
- `path/to/file.py` — [what changed]

#### Known Issues / Follow-ups
- [Issue 1]
- [Issue 2]
