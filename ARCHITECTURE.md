# Nova-Script Architecture

## Overview

Three-layer architecture bridging Novation hardware ↔ Reaper ↔ Akai Force.

```
┌─────────────────────────────────────────────────────────────────┐
│                        NOVA-SCRIPT ENGINE                       │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Controllers  │  │   UI / Modes  │  │  TUI Companion App  │  │
│  │  (Layer 1)   │  │  (Layer 2)   │  │     (Textual)        │  │
│  │              │  │              │  │                      │  │
│  │  MK1, MK2,   │  │  Sequencer,  │  │  Grid Mirror,        │  │
│  │  MK3, etc.   │◄─┤  Mixer, Menu,│──┤  Config Screen,      │  │
│  │              │  │  Effects...  │  │  Activity Log        │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────────┘  │
│         │                 │                                     │
│  ┌──────┴─────────────────┴──────────────────────────────────┐ │
│  │                    Protocol Bridge                         │ │
│  │  ┌──────────┐  ┌──────────┐  ┌────────────────────────┐   │ │
│  │  │ MIDI Out │  │ OSC Client│  │     OSC Server         │   │ │
│  │  │ (Force)  │  │ (Reaper)  │  │  (from Reaper scripts) │   │ │
│  │  └──────────┘  └──────────┘  └────────────────────────┘   │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Layer 1: Device Abstraction (`src/controllers/`)

### Class Hierarchy
```
NovationController (ABC)
├── LaunchpadBase
│   ├── LaunchpadMiniMK1
│   ├── LaunchpadMiniMK3 (planned)
│   ├── LaunchpadProMK3 (planned)
│   └── LaunchpadX (planned)
└── LaunchkeyBase
    └── Launchkey49MK2
```

### Key Abstractions
- **GridEvent**: (x, y, pressed, velocity) — normalized button event
- **ControlEvent**: (control_id, value, type) — knob/fader/transport event
- **LEDColor**: Logical color enum → hardware-specific byte sequence
- **DeviceCapabilities**: grid_size, color_depth, has_velocity, has_aftertouch

### Color Mapping Strategy
MK1 has ~9 usable states (3 colors × 3 brightness levels + off). Newer pads have full RGB.
Logical colors (e.g., `TRACK_ARMED`, `CLIP_PLAYING`, `STEP_ACTIVE`) map via `ColorMap` to
the best available hardware representation. On MK1, blue-adjacent logical colors map to green-high.
On MK3, they render as actual blue.

## Layer 2: UI / Modes (`src/ui/`)

### Mode Lifecycle
```
enter() → handle_event(events...) → [tick()] → exit()
```
- Only one mode active at a time
- `ModeManager` handles transitions
- Modes own the grid — they decide what each LED shows
- Modes receive normalized events from the active controller

### Mode Registry
| Mode | Description | Grid Usage |
|------|-------------|------------|
| Menu | Top-level navigation | Icons + labels on pads |
| Sequencer | Step sequencer | Rows=notes, Cols=steps |
| Mixer | Track mixer | Columns=faders, indicators |
| Effects | Per-track FX | Parameter banks |
| Performance | Clip/scene launch | Session grid |
| Device | Plugin control | 8-knob style mapping |
| Message | Scrolling text | Text display on grid |

### Idle Detection & Message Display
- Engine tracks time since last physical button press
- When OSC `/display/message` arrives AND idle_time > threshold → auto-switch to Message mode
- Any button press in Message mode → return to previous mode, dismiss message
- Message queue for stacked incoming messages

## Layer 3: Protocol Bridge (`src/midi/` + `src/osc/`)

### MIDI Output Routing
- Configurable routing table: map logical targets to physical MIDI ports
- Target: Akai Force (track volumes, effects, sequenced notes, program changes)
- Future: other external gear

### OSC Namespace (draft)
```
/nova/track/{1-n}/volume        f 0.0-1.0    → Reaper track volume
/nova/track/{1-n}/pan           f -1.0-1.0   → Reaper track pan
/nova/track/{1-n}/mute          i 0/1        → Reaper track mute
/nova/track/{1-n}/solo          i 0/1        → Reaper track solo
/nova/track/{1-n}/fx/{id}/param/{n}  f       → FX parameter
/nova/transport/play            —            → Transport play
/nova/transport/stop            —            → Transport stop
/nova/transport/record          —            → Transport record
/nova/display/message           s "text"     → Show scrolling message
/nova/mode/set                  s "name"     → Switch active mode
/nova/beat                      i position   → Beat clock position
```

### OSC Receiving (from Reaper)
```
/reaper/track/{1-n}/volume/dB   f            → Metering feedback
/reaper/track/{1-n}/mute        i 0/1        → Mute state feedback
/reaper/transport/play_state    i 0/1/2      → 0=stopped, 1=playing, 2=paused
/reaper/beat_position           f            → Current beat position
```

## TUI Companion (`src/tui/`)
- Textual-based terminal UI
- Runs in separate process (or thread), communicates via queue/pipe
- Grid mirror: live visual of Launchpad LED state with proper colors
- Mode indicator: shows active mode name
- Event log: scrollable log of MIDI/OSC events
- Config screen: edit settings live

## Concurrency Model
- asyncio event loop as the main runtime
- MIDI I/O: rtmidi callbacks → asyncio queue
- OSC server: aioosc or python-osc with asyncio adapter
- TUI: Textual runs its own asyncio app — share the same loop or use subprocess
