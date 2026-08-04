# Nova-Script Project CLAUDE.md

## Project Identity
- **Name:** nova-script
- **Purpose:** Unified Novation controller scripting environment + custom performance controller
- **Location:** `~/Documents/projects/nova-script/`
- **Language:** Python 3.11+
- **GitHub:** PlaceholderDuo/nova-script

## Architecture (3 layers)
1. **Controllers** (`src/controllers/`) — Device abstraction (Launchpad MK1, Launchkey MK2, future models)
2. **UI/Modes** (`src/ui/`) — Mode system (sequencer, mixer, effects, performance, menu, message display)
3. **Protocol Bridge** (`src/midi/` + `src/osc/`) — MIDI out to Akai Force, OSC bidir with Reaper

## Key Docs
- `BUILD_LOG.md` — Full development history with detailed decisions
- `ARCHITECTURE.md` — System architecture diagrams and descriptions
- `REQUIREMENTS.md` — Functional and non-functional requirements (FR1-FR15, NFR1-NFR4)

## Connected Hardware
- Launchpad Mini MK1 (primary — limited colors: amber/red/green × 3 brightness)
- Launchkey 49 MK2 (secondary — 16 velocity pads, 8 knobs, 8 faders, transport)
- Akai Force (MIDI target over USB)
- Reaper DAW (OSC bidir communication)

## Dev Commands
- Run: `python -m src.main` or `./scripts/run.sh`
- Run with TUI: `python -m src.main --tui`
- Test harness: `python scripts/test_harness.py` (interactive Launchpad testing)
- Config: `config/default.yaml`

## Key Patterns
- Controllers extend `NovationController` abstract base
- Modes extend `Mode` base class, only one active at a time
- LED colors use logical enums, mapped to hardware capabilities
- All events normalized through `GridEvent` / `ControlEvent` dataclasses
- Concurrency via asyncio + rtmidi callbacks
