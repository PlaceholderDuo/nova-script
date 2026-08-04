# Nova-Script Pad Navigation Manual

**For:** Launchpad Mini MK1 | **Profile:** live-show

---

## Universal Controls (everywhere)

| Button | Action |
|--------|--------|
| **Top-1** | **Home** — returns to Menu mode. Orange blink at home, green blink elsewhere. Blinks at BPM tempo. |
| **Top-1+2** (hold both) | **Screensaver** — immediately display current screensaver image |
| **Top-1+3** (hold both) | **Fireworks** — BPM-synced particle display (8 bars) |

### Mode Shortcuts (any mode, when no overlay active)
| Button | Mode |
|--------|------|
| Top-1 | Home (Menu) |
| Top-2 | Performance Control |
| Top-3 | Clip Launcher |
| Top-4 | Sequencer |
| Top-5 | Mixer |

### Overlay Rules
- If a screensaver or HUD overlay is active, the **first button press dismisses it** (consumed).
- The **second press** acts normally in the restored mode.
- Fireworks auto-transition to screensaver after 8 bars.

---

## Menu Mode (Home)

**Layout:** 2×2 spatial blocks
- **RED** (top-left 2×2): Performance Control
- **DIM RED** (top-center 2×2): Clip Launcher
- **AMBER** (top-right 2×2): Sequencer
- **GREEN** (middle-left 2×2): Mixer

**Navigation:**
- Press any pad within a 2×2 block → activates that mode
- Press outside all blocks → ignored
- Top-row buttons 2-5 also work as shortcuts (see Universal Controls)

**Right column:**
- Page indicators (when modes have multiple pages)

---

## Performance Control Mode

**Purpose:** Track mute + FX toggles for live performance.

### Page 1: Mute + Core FX

**Top row (1-8):** Track mute toggles
| Button | Track | Color |
|--------|-------|-------|
| 1 | Vox | Amber (unmuted) / Red (muted) |
| 2 | GTR | Amber (unmuted) / Red (muted) |
| 3 | Bass | Amber (unmuted) / Red (muted) |
| 4-8 | Track 4-8 | Amber (unmuted) / Red (muted) |

**GTR hold:** Pressing GTR mute when unmuted activates **strobe tuner** on full 8×8.
Displays T-N-R intro animation (0.3s per letter orange), then tuner.
Press any button to dismiss.

**Right column (A-E):** FX toggles for the currently selected track
| Button | FX | Color |
|--------|-----|-------|
| A | Rev (Reverb) | Red=off, Green=on |
| B | Dly (Delay) | Red=off, Green=pulsing at BPM |
| C | Chor (Chorus) | Red=off, Green=pulsing at BPM |
| D | Hrm↑ (Harmonizer Up) | Red=off, Green=on |
| E | Hrm↓ (Harmonizer Down) | Red=off, Green=on |

**FX Hints:** When toggling an FX, the first letter flashes on the grid:
- Green = turning ON, Red = turning OFF
- 0.3 second display

### Page 2: Extended FX (coming soon)

**Right column (F-H):** Page navigation
- Amber = page exists, Green = current page
- H = Page 1 (mute + core FX), G = Page 2 (extended FX)

---

## Clip Launcher Mode

**Purpose:** Launch MIDI/OSC clips on an 8×8 session grid.

**Grid:** 8 tracks (columns) × 8 scenes (rows)
- Press a lit pad → launches clip (MIDI + OSC), turns GREEN while playing
- Press the same pad again → stops clip
- Press a different pad on the same track → replaces (stops old, launches new)
- Bottom row (row 0) → track stop (stops all clips in that track)
- **OFF pads** → silent, do nothing when pressed

**Right column (A-H):** Scene launch
- Press any right column button → launches all clips in that scene row

**Edit mode:** Hold Button 3 for 1 second → enter edit mode
- All lit pads pulse smoothly at BPM
- Press an unlit pad → activates it with AMBER color
- Press a lit pad → cycles color: AMBER → RED → GREEN → dim amber → dim red → dim green → OFF
- Short press Button 3 → save and exit edit mode

**Default layout:** Top 4 rows have active clips, bottom 4 rows blank.

---

## Sequencer Mode

**Purpose:** Step sequencer with MIDI output.

**Grid:** 7 rows of notes + 1 transport row
- Rows 0-6: step sequencer notes (press to toggle steps on/off)
- Row 7: transport controls

**Top row:**
| Button | Action |
|--------|--------|
| 1 | Home |
| 2 | Play/Pause |
| 3 | Reset to step 0 |
| 6 | Page left |
| 7 | Page right |
| 8 | Record/Overdub |

**Right column:** BPM and resolution controls

---

## Mixer Mode

**Purpose:** 8-track volume faders + mute toggles.

**Grid:** 8 columns (tracks) × 7-row faders + 1 mute row
- Rows 0-6: tap to set volume (7 levels of resolution)
- Row 7: mute toggle (Red=muted, Amber=unmuted)

**Top row:**
| Button | Action |
|--------|--------|
| 1 | Home |
| 2-3 | Bank navigation |

---

## BPM Clock & Visual Feedback

### Top-1 LED
- Blinks at BPM tempo on every page
- Orange at home (Menu mode), Green in all other modes
- Beat 1: blinks downbeat color (configurable in settings)
- Beats 2-4: blinks normal tempo color

### Visual Hints (configurable ON/OFF in settings)
- FX toggle in Performance mode: flashes first letter on grid (green=on, red=off)

### Press Feedback
- Any grid pad press: flashes bright amber for 120ms

---

## Screensaver & Visuals

### Screensaver
- Auto-activates after idle timeout (configurable, default 30s)
- Manual: Top-1+2
- 64 stored images, 8 quick-access slots on top row
- BPM cycling available (configurable)
- Any button press dismisses

### Fireworks
- Manual: Top-1+3
- BPM-synced particle display, 8 bars
- Auto-transitions to screensaver when complete
- Any button press dismisses

### HUD Messages
- Triggered by OSC (e.g., from Reaper)
- Displays text/character/image briefly
- Dismisses on timeout or button press

---

## TUI Companion

Launch with `nova-script --tui` or `nova-script --tui live-show`

| Key | Action |
|-----|--------|
| Q | Quit |
| P | Profiles (list, load, save) |
| S | Settings (clock sources, downbeat, hints, mixer) |
| M | Menu mode |
| 1-5 | Mode shortcuts |

---

## Settings Reference

Access via TUI → S key, or edit `config/profiles/live-show.yaml`

### Clock
- **Preferred source:** Reaper (OSC) / MIDI port name / Internal
- **Fallback source:** Reaper (OSC) / MIDI port name / Internal
- **Internal BPM:** 120 (default)

### Visual
- **Downbeat flash:** Tempo LED (beat 1 distinct) / 4 corners / Disable
- **Downbeat color:** GREEN_HIGH / RED_HIGH / AMBER_HIGH / etc.
- **Visual hints:** ON / OFF

### Mixer
- 16 channels configurable: alias, output (OSC/MIDI), curve, OSC address, MIDI channel+CC
