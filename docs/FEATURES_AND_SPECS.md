# Nova-Script Features & Specifications

**Last updated:** 2026-08-03 | **Status:** Build Phase

---

## 1. Startup Flow

```
Launch → MIDI discovery → Connect devices → Startup Wave (2s) → Menu Mode → idle timer
```

### 1.1 Startup Wave
Orange ripple from bottom-left (0,0) diagonally to top-right (7,7). Green follows. Red follows. All three color waves cascade across the 8×8 grid over ~2 seconds total.

Implementation: wave propagates along diagonal bands (x+y = constant). Band 0 = (0,0), band 1 = (0,1)(1,0), ... band 14 = (7,7). Orange sweeps delay 0.4s, green 0.8s, red 1.2s. Each band stays lit briefly then fades.

### 1.2 Device Discovery
- Scan MIDI ports every 500ms
- Auto-connect by name pattern match
- Kick input buffer on connect
- TUI shows connection status in real time
- Works headless or with TUI

---

## 2. Golden Rules

### 2.1 Home Button
**Top row button 1 = HOME.** Always returns to Menu mode. Every mode, every state. In Menu mode itself, button 1 blinks amber to indicate "you are home."

### 2.2 Overlay Dismiss
**First button press on any overlay consumes the event.** It does NOT pass through to the underlying mode. Only the second press (after dismiss) acts normally.

### 2.3 Manual Overrides
- **Top-1 + Top-2 together** → Enter screensaver immediately (anywhere)
- **Top-1 + Top-3 together** → Launch fireworks immediately (anywhere)

---

## 3. Overlay System

Overlays sit on top of active modes. Priority system ensures only one overlay runs at a time.

| Priority | Name | Trigger | Dismisses On | Duration |
|----------|------|---------|-------------|----------|
| 4 (highest) | Fireworks | Top-1+3 or OSC | Any button press | 8 bars or touch |
| 3 | HUD | OSC text/char/image | Any button press | Brief (configurable) |
| 2 | Screensaver | Idle timeout OR Top-1+2 | Any button press | Indefinite |
| 1 (base) | Active Mode | Normal operation | N/A | Indefinite |

### 3.1 Fireworks → Screensaver Transition
When fireworks reach 8 bars → auto-enter screensaver (not back to active mode).

### 3.2 HUD → Return
When HUD is dismissed: if screensaver was showing before HUD, return to screensaver. If active mode was showing, return to mode.

### 3.3 Dismiss Logic (Implementation)
The engine intercepts ALL button events before the active mode sees them. If an overlay is active:
1. Overlay's `handle_event()` is called
2. If overlay returns "dismissed": engine clears overlay, returns to prior state
3. Event is consumed — never reaches mode handlers
4. Next event flows normally to the active mode

---

## 4. Menu Mode (Refined)

### 4.1 Layout
```
┌───T─O─P──R─O─W───┐  Top button 1 = HOME (amber blink)
│ 1   2   3   4   5   6   7   8  │  Buttons 2-6 = quick mode select
├─────────────────────┤
│ ·  ·  ·  ·  ·  ·  ·  ·  │
│ ·  ·  ·  ·  ·  ·  ·  ·  │
│ ·  ·  · DEV ·  ·  ·  ·  │  ← Mode pads (2×2 or 3×2 blocks)
│ ·  ·  · FX  · PERF ·  ·  │      each with label pattern
│ ·  ·  · MIX ·  ·  ·  ·  │
│ ·  ·  · SEQ ·  ·  ·  ·  │
│ ·  ·  ·  ·  ·  ·  ·  ·  │
├─────────────────────┤     Right column:
│ ·  A                                    │     page navigation (when >5 modes)
│ ·  B                                    │
│ ·  C                                    │
│ ·  D                                    │
│ ·  E                                    │
│ ·  F                                    │
│ ·  G                                    │
│ ·  H                                    │
└─────────────────────┘
```

### 4.2 Mode Colors
| Mode | Color | Reason |
|------|-------|--------|
| Sequencer | AMBER_HIGH | beats/steps |
| Mixer | GREEN_HIGH | volume/mixing |
| Performance | AMBER_HIGH (flash) | live/playing |
| Effects | RED_HIGH | processing |
| Device | GREEN_MED | control |

### 4.3 Activation
- Grid pads: press the mode block to activate
- Top row buttons 2-6: instant mode select
- Right column: page forward/back (when >5 modes)
- Feedback: mode pad flashes briefly before switching

---

## 5. Per-Mode Button Mappings

### 5.1 Universal (all modes)
```
Top-1 = HOME (back to Menu)
Top-1+2 = Enter screensaver
Top-1+3 = Launch fireworks
```

### 5.2 Sequencer Mode
```
Top: [HOME] [▶/■] [⟲reset] [·] [·] [◀page] [page▶] [●rec]
Right: [BPM+] [BPM-] [res+] [res-] [·] [·] [·] [·]
Grid: rows 0-6 = note rows, row 7 = transport/status bar
```

### 5.3 Mixer Mode
```
Top: [HOME] [bank◀] [bank▶] [·] [·] [·] [·] [·]
Grid: columns = tracks (0-7), rows 0-6 = fader, row 7 = mute/solo
```

### 5.4 Performance Mode
```
Top: [HOME] [stopT1] [stopT2] ... [stopT7]
Right: [scene0] [scene1] ... [scene7]
Grid: columns = tracks (0-7), rows = scenes (0-7 bottom→top)
Short press = launch/stop clip, Long press (500ms) = clear clip
```

---

## 6. Screensaver System

### 6.1 Activation
- **Auto:** After `idle_timeout_ms` (configurable, default 30s) of no button presses
- **Manual:** Top-1+2 from anywhere
- **Post-fireworks:** automatically after 8-bar fireworks display ends

### 6.2 Image System
- **64 stored images** — each is an 8×8 grid of LogicalColor values
- **8 quick-access slots** mapped to top row buttons 1-8, persist across restarts
- Stored in `config/screensaver-images.yaml` (64 entries, each 8×8 color grid)
- Loaded at startup, editable via TUI or OSC

### 6.3 Image Storage Format
```yaml
images:
  0:
    name: "waves"
    grid:
      - [OFF, OFF, OFF, OFF, OFF, OFF, OFF, OFF]
      - [OFF, OFF, AMBER_HIGH, AMBER_HIGH, OFF, OFF, OFF, OFF]
      # ... 8 rows of 8 colors each
  1:
    name: "heart"
    grid: ...
  # ... up to 63

quick_slots:  # maps top-button index to image ID
  0: 12
  1: 5
  2: 0
  3: 42
  4: 7
  5: 3
  6: 8
  7: 21

last_image: 12  # persists across restarts
```

### 6.4 Image Picker Interaction
**Enter:** Hold top button 8 for 2+ seconds while in screensaver mode.

**Picker view:** All 64 pads light up, each showing a preview color (dominant color of that image). Active top-row slots blink.

**Navigation:**
- Tap any grid pad → select that image, display it full-screen
- Tap same pad or any grid pad again → back to 64-image picker
- Hold any top button 1-8 for 2s → assign CURRENTLY DISPLAYED image to that slot
- Press top button 1 → exit picker, keep current image, continue screensaver
- Any other button → exit picker (same as top-1)

### 6.5 BPM Cycling
When BPM is available (from OSC/MIDI clock):
- Cycle through 8 quick-access images once per bar (or configurable: 1/2 bar, 2 bars, 4 bars)
- Configurable per image: `cycle_enabled: true/false`
- When no BPM: show static image

### 6.6 Persistence
- `last_image` saved on every change
- `quick_slots` saved on every assignment
- Loaded at startup, screensaver shows `last_image` on first activation

---

## 7. Fireworks System

### 7.1 Activation
- **Manual:** Top-1+3 from anywhere
- **OSC:** `/nova/fireworks` (optional intensity param)

### 7.2 Behavior
- Particle system on 8×8 grid
- Particles spawn randomly, move upward, fade
- Synced to BPM — new burst on each beat
- Runs for 8 bars (configurable), then auto-enters screensaver
- Any button press kills fireworks immediately, enters screensaver

### 7.3 Particle Design
- Each particle: (x, y, color, velocity, lifetime)
- Burst: spawn 3-5 particles at random bottom positions on beat
- Colors: cycle through RED/AMBER/GREEN per beat
- Gravity: particles "fall" slightly as they rise (y increases, then decreases)
- Trail: particles leave a 1-step fading trail

---

## 8. HUD System

### 8.1 Purpose
Temporary visual feedback when changing settings on screenless MIDI devices. Used sparingly — only for intentional status changes, not mapped to everything.

### 8.2 OSC Interface
```
/nova/hud/text "KARAOKE"     → scroll text horizontally
/nova/hud/char "G"           → single large character centered
/nova/hud/image 42           → display stored image by ID
```

### 8.3 Behavior
- Overlays on top of current mode (priority 3)
- Dismisses after configurable timeout (default 1.5s) or any button press
- After dismiss: return to screensaver if that was showing, otherwise active mode
- Multiple rapid HUD messages queue (show sequentially, no overlap)

---

## 9. TUI Companion (Redesigned)

```
┌──────────────────────────────┬────────────────────────────────┐
│  NOVA-SCRIPT    Mode: Menu   │  LP:✓  LK:✗  OSC:✓  BPM:120  │ ← status bar
├──────────────────────────────┼────────────────────────────────┤
│                              │  MODE: Menu                     │
│                              │  Press a pad to select          │
│   8×8 GRID MIRROR            │                                 │
│   (live LED state,           │  Active bindings:               │
│    20fps)                    │  Top-1    = Home                │
│                              │  Top-2..6 = Quick select        │
│  ┌───TOP───┐                 │  Top-1+2  = Screensaver         │
│  │1 2 3 4 5│ ← top row      │  Top-1+3  = Fireworks           │
│  └─────────┘                 │  Grid     = Mode select         │
│  ┌─────────┐                 │                                 │
│  │A B C D E│ ← right col    ├────────────────────────────────┤
│  │F G H I J│                 │  IMAGE PREVIEW (when in picker) │
│  └─────────┘                 │  ┌──────────┐                   │
│                              │  │  8×8 img  │                  │
│                              │  └──────────┘                   │
│                              │  Image #12: "waves"             │
│                              │                                 │
│                              ├────────────────────────────────┤
│                              │  EVENT LOG:                     │
│                              │  22:30:01 LP connected           │
│                              │  22:30:01 OSC listening :9001    │
│                              │  22:30:05 Mode → Sequencer       │
│                              │  22:30:08 Fireworks!            │
│                              │  22:30:12 Screensaver active    │
├──────────────────────────────┴────────────────────────────────┤
│  Q=Quit  M=Menu  S=Seq  X=Mix  P=Perf  F=FX  D=Dev           │
└──────────────────────────────────────────────────────────────┘
```

---

## 10. Edge Cases & "What Ifs"

### 10.1 Startup with no devices
Engine starts. OSC bridge starts. TUI functional. No Launchpad = menu doesn't render on hardware. Auto-connects when device appears.

### 10.2 Cable bump
MidiManager detects disconnect → reconnects in <1s → kicks input buffer → re-renders current mode/overlay. OSC bridge and internal state unaffected.

### 10.3 Rapid overlay triggers
Overlay queue processes one at a time. If fireworks requested during screensaver: screensaver dismissed, fireworks start. If HUD requested during fireworks: queued, plays after fireworks → screensaver transition.

### 10.4 Image loading fails
Corrupt image → replaced with default "X" pattern. Missing image ID → shows empty grid. Config file missing sections → sensible defaults.

### 10.5 BPM not available
Screensaver BPM cycling disabled, shows static image. Fireworks uses internal 120 BPM default.

---

## 11. Risk Register (Build Order)

| Risk | Severity | What could go wrong |
|------|----------|-------------------|
| Multi-button combos | HIGH | Can we reliably detect Top-1+2 and Top-1+3? Simultaneous press detection on a single MIDI stream is tricky |
| Fireworks particle system | HIGH | 8×8 resolution with smooth particle motion at BPM. Need efficient rendering |
| Image storage format | MEDIUM | YAML might be slow for 64 images. Need validation on load |
| Overlay dismiss flow | MEDIUM | Complex state transitions between overlay priorities. Must not leak button events |
| Startup wave timing | LOW | Simple animation, already have LED control working |
| Image picker interaction | LOW | State machine with tap/hold detection. Existing long-press code should handle |
