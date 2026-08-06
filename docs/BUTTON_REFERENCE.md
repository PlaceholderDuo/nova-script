# Button Reference — All Modes

Master reference for every button, LED, and grid interaction across all nova-script modes. Virtualizer help labels and mode info panels derive from this document.

---

## Performance Mode (Top-1 shortcut, default)

**Dual-channel FX controller.** Grid is split vertically: **left half = GTR** (cols 0-3), **right half = VOX** (cols 4-7). Each channel has a volume bar, 4 FX blocks with 6 presets each, and per-FX disable.

### Top Row (1-8)
| Button | LED | Action |
|--------|-----|--------|
| 1 | AMBER (home) / GREEN (away) / Blinks at BPM | Home — return to Performance |
| 2 | OFF | Switch to Clip Launcher |
| 3 | OFF | Switch to Sequencer |
| 4 | OFF | Switch to Mixer |
| 5 | OFF | Switch to Instrument |
| 6-8 | OFF | Unused |

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
- 8 pads, dual-level press system. 16 levels (18-32) + mute.
- **First press on pad:** GREEN_HIGH, higher level (even: 18, 20, 22, ... 32).
- **Second press on same pad:** AMBER_HIGH, lower level (odd: 17, 19, 21, ... 31).
- **Pad 0 double-press:** MUTE (entire column turns RED_HIGH).
- **Pads above current level:** RED_HIGH (full column always shows level position).
- **Pads below current level:** OFF.
- **Press any pad while muted:** Unmutes to that level.

### FX Preset Pads (cols 1-3 GTR, cols 5-7 VOX)
- 4 FX per channel, top to bottom: Delay, Harmony, Amp&Drv, Tremolo (GTR) / Delay, Harmony, Drv&Flt, Misc SFX (VOX).
- 3 pads per FX with 2 banks = **6 presets per FX.**
- **Unselected preset:** GREEN_HIGH.
- **Selected preset, bank 1:** AMBER_HIGH (ORANGE).
- **Selected preset, bank 2:** RED_HIGH.
- **Press unused pad:** Select bank 1 preset for that pad.
- **Press selected pad (bank 1):** Switch to bank 2 preset.
- **Press selected pad (bank 2):** Switch back to bank 1 preset.
- **Press preset when FX disabled:** Auto-enables the FX and selects that preset.

### FX Disable Pads (directly below each FX block)
- 3 RED pads. Press any to disable/re-enable the FX.
- **Disabled:** RED_MED.
- **Enabled:** RED_HIGH.

### OSC Mapping
| Channel | Track | Volume | Delay | Harmony | Amp&Drv/Drv&Flt | Tremolo/Misc |
|---------|-------|--------|-------|---------|-----------------|--------------|
| GTR | /track/2 | /track/2/volume | /track/2/fx/1/preset | /track/2/fx/2/preset | /track/2/fx/3/preset | /track/2/fx/4/preset |
| VOX | /track/1 | /track/1/volume | /track/1/fx/1/preset | /track/1/fx/2/preset | /track/1/fx/3/preset | /track/1/fx/4/preset |

All FX also send `/track/{n}/fx/{k}/bypass` (0 = enabled, 1 = bypassed). Volume sends float 0.0-1.0.

### Settings (TUI)
- `ui.downbeat_flash` — tempo_led / 4_corners / disable
- `ui.downbeat_color` — beat 1 color

---

## Instrument Mode (Top-5 shortcut)

### Top Row (1-8)
| Button | LED | Action |
|--------|-----|--------|
| 1 | GREEN (home) / AMBER (away) | Switch to Performance |
| 2 | OFF | Switch to Clip Launcher |
| 3 | OFF | Switch to Sequencer |
| 4 | OFF | Switch to Mixer |
| 5 | OFF | Current mode (Instrument) |
| 6-8 | OFF | Unused |

### Right Column (A-H)
| Button | LED | States / Options | Action (short) | Action (long) |
|--------|-----|-----------------|----------------|---------------|
| **A** | GREEN | Notes | GREEN = Notes mode | Hold → shows offset overlay on top row 1-5 |
| | AMBER | Chords | AMBER = Chords mode | |
| **B** | GREEN | Major scale | Cycle: Major → Blues → Chromatic | — |
| | AMBER | Blues scale | | |
| | RED | Chromatic scale | | |
| **C** | GREEN | Hold ON | Toggle Hold | — |
| | RED | Hold OFF | | |
| **D** | RED | ARP OFF | Cycle: OFF → Up → Down | — |
| | GREEN | ARP Up | | |
| | AMBER | ARP Down | | |
| **E** | GREEN | Pattern 1 (Normal) | Cycle: 1 → 2 → 3 | **Long: Enter ARP Edit Mode** |
| | AMBER | Pattern 2 (Chordal) | | |
| | RED | Pattern 3 (Octaves) | | |
| **F-H** | OFF | Reserved | — | — |

### A-Button Hold Overlay
Hold A → A button flashes → top row pads 1-5 show offset options (ORANGE except current = GREEN):
- Pad 1: Octaves (12 semitones)
- Pad 2: 2 semitones
- Pad 3: 3 semitones
- Pad 4: 4 semitones
- Pad 5: 5 semitones

### Visual Hints (300ms RED overlay)
| Control | Hint | Color |
|---------|------|-------|
| Scale (B) | S / B / C | RED_HIGH |
| Hold (C) | H | GREEN (ON) / RED (OFF) |
| ARP (D) | A | RED (OFF) / GREEN (UP) / AMBER (DOWN) |
| Pattern (E) | 1 / 2 / 3 | GREEN / AMBER / RED |

### Grid (8×8)
- **Every pad:** Playable note in current scale at configured row offset.
- **RED_HIGH:** Root notes (same pitch class as configured root).
- **GREEN_HIGH:** Currently pressed pad(s).
- **GREEN_MED:** Octave indicator — same pitch class as pressed pad, different octave.
- **AMBER_LOW:** All other pads (playable scale notes).
- **Press pad:** Sends MIDI Note ON (velocity 100). Chords mode sends triad.
- **Release pad:** Sends MIDI Note OFF (unless Hold ON).
- **Hold ON:** Note sustains until pad pressed again or different pad pressed.

### Settings (TUI)
- `arp.diatonic` — ARP transposition: Diatonic (in-key, default) or Chromatic (absolute)

---

## ARP Edit Mode (Long-press E from Instrument Mode)

### Entry
- E button blinks AMBER rapidly (200ms period) while in edit mode.
- Grid transitions from instrument layout to pattern editor.

### Top Row (1-8)
| Button | LED | Action |
|--------|-----|--------|
| 1 | GREEN_HIGH | Exit — return to Instrument Mode |
| 2-8 | OFF | Unused |

### Right Column (A-H) — Page 1 (default)
| Button | LED | States | Short Press | Long Press |
|--------|-----|--------|-------------|------------|
| **A** | RED_LOW / RED_HIGH | Factory: Normal pattern | Select pattern | — (protected) |
| **B** | RED_LOW / RED_HIGH | Factory: Chordal pattern | Select pattern | — (protected) |
| **C** | RED_LOW / RED_HIGH | Factory: Octaves pattern | Select pattern | — (protected) |
| **D** | AMBER_LOW / AMBER_HIGH | User slot 4 | Select pattern | Save → blink GREEN 1s |
| **E** | RED_HIGH | Note-length sub-mode | Enter note-length mode | — |
| **F** | AMBER_LOW / AMBER_HIGH | User slot 6 | Select pattern | Save → blink GREEN 1s |
| **G** | GREEN / AMBER | Page up | Go to page 1 | — |
| **H** | GREEN / AMBER | Page down | Go to page 2 | — |

**Page 2-3:** All A-H slots (except E, G, H) are user slots (AMBER). E and G/H unchanged.

### Page Navigation LEDs
| Page | G LED | H LED |
|------|-------|-------|
| 1 | AMBER (at top) | GREEN (can go down) |
| 2 | GREEN (can go up) | GREEN (can go down) |
| 3 | GREEN (can go up) | AMBER (at bottom) |

### Grid (8×8)
- **Row 0 (bottom):** Beat chase indicator. Current step = AMBER_HIGH. Others = AMBER_LOW. 8 steps per bar, BPM-synced.
- **Rows 1-7:** Scale degrees (1 = root through 7 = 7th). AMBER_HIGH = note set at this step. OFF = skip.
- **Press unlit pad:** Set note for that step/degree.
- **Press lit pad:** Clear note (skip) for that step.
- **One pad per column max.**

---

## Note-Length Sub-Mode (Press E from ARP Edit Mode)

### Entry
- Grid scrolls "LENGTH" in RED_HIGH for 1 second.

### Top Row
| Button | LED | Action |
|--------|-----|--------|
| 1 | GREEN_HIGH | Back to ARP Edit Mode |
| 2-8 | OFF | Unused |

### Right Column (A-H)
| Button | LED | Action |
|--------|-----|--------|
| A-H | RED_HIGH | Set ALL steps to this length level (1-8) |

### Grid (8×8)
- Bar-graph display. Each column = one of 8 ARP steps. Bar height = note length (1-8).
- RED_HIGH = active bar cells. OFF = unset.
- All RED, no other colors.
- **Press pad:** Set individual step length (row 0 = level 1, row 7 = level 8).

### Note Length Levels
| Level | Duration | Feel |
|-------|----------|------|
| 1 | 1/32 note | Ultra-staccato |
| 2 | 1/16 triplet | Very short |
| 3 | 1/16 note | Standard short |
| 4 | 1/8 triplet | Medium-short |
| 5 | 1/8 note (default) | Full step |
| 6 | Dotted 1/8 | Overlaps slightly |
| 7 | 1/4 note | Long, smooth |
| 8 | Legato | No gap — tied |

---

## Clip Launcher Mode (Top-2 shortcut)

### Top Row (1-8)
| Button | LED | Action |
|--------|-----|--------|
| 1 | GREEN (away) / AMBER (home) | Switch to Performance |
| 2 | OFF | Current mode |
| 3 | OFF | Switch to Sequencer |
| 4 | OFF | Switch to Mixer |
| 5 | OFF | Switch to Instrument |
| 6-8 | OFF | Unused |

### Right Column
| Button | LED | Action |
|--------|-----|--------|
| A | GREEN / AMBER | Page indicator — current page |
| B | AMBER / OFF | Page indicator — page available |

### Grid (8×8)
- Session clip grid. 8 tracks × 7 clip slots. Top cell of each column = track header.
- Press empty slot: Launch clip (START).
- Press playing slot: Stop clip.
- AMBER = empty, GREEN = playing, RED = stopped, AMBER pulsing = queued.
- Hold Top-3 to enter edit mode (BPM pulsing, color cycling).

---

## Sequencer Mode (Top-3 shortcut)

### Top Row (1-8)
| Button | LED | Action |
|--------|-----|--------|
| 1 | GREEN / AMBER | Performance |
| 2 | OFF | Clip Launcher |
| 3 | OFF | Current mode |
| 4 | OFF | Mixer |
| 5 | OFF | Instrument |

### Right Column
| Button | LED | Action |
|--------|-----|--------|
| A | GREEN / AMBER | Page indicator |

### Grid (8×8)
- Step sequencer. 7 rows × 16 visible steps (2 pages of 8). Top row (7) = transport controls.
- Press pad: Toggle step on/off.
- AMBER = active step, OFF = inactive.
- Top row: Play/Stop, velocity, page navigation.

---

## Mixer Mode (Top-4 shortcut)

### Top Row (1-8)
| Button | LED | Action |
|--------|-----|--------|
| 1 | GREEN / AMBER | Performance |
| 2 | OFF | Clip Launcher |
| 3 | OFF | Sequencer |
| 4 | OFF | Current mode |
| 5 | OFF | Instrument |

### Grid (8×8)
- 8 tracks × 6-row vertical faders (rows 1-6). Each column = one track. Row height = fader position.
- Row 7: Mute toggles (AMBER_LOW = unmuted, RED_HIGH = muted).
- Row 0: Reverb send (OFF = 0%, AMBER_MED = 50%, GREEN_HIGH = 100%). 3-way toggle per track.
- OSC: `/track/{n}/fx/rev/send` (float 0.0-1.0).

---

## Menu Mode

### Grid
- 2×2 colored blocks representing mode shortcuts (PERF, CLIP, SEQ, MIX).
- Press block: Switch to that mode.
- Top-row buttons also act as mode shortcuts (1=Performance, 2=Clip, 3=Seq, 4=Mix, 5=Instrument).

---

## Screensaver Overlay

### Right Column (A-H)
| Button | LED | Action |
|--------|-----|--------|
| A | AMBER (current) / LOW (available) | Heart screensaver |
| B | AMBER (current) / LOW (available) | Waves screensaver |
| C | AMBER (current) / LOW (available) | Glimmer screensaver |
| D-H | OFF | Reserved for future modes |

- Current mode = AMBER at 80% brightness.
- Other available = AMBER at 20% brightness.
- Unused = OFF.

### Dismiss
- Any grid pad press: Dismiss screensaver (first press consumed).
- Any top row button: Dismiss screensaver (first press consumed).
- Second press: Passes to active mode.

---

## Universal Controls (All Modes)

### Top Row (Always Available as Mode Shortcuts)
| Button | Mode |
|--------|------|
| 1 | Performance (Home) |
| 2 | Clip Launcher |
| 3 | Sequencer |
| 4 | Mixer |
| 5 | Instrument |
| 6-8 | Unused |

### Combos (Global)
| Combo | Action |
|-------|--------|
| Top-1 + Top-2 | Trigger screensaver |
| Top-1 + Top-3 | Trigger fireworks |

### BPM Clock LED (Top-1, all modes)
- Solid AMBER (at home) / GREEN (away) until external sync received.
- Blinks at BPM once sync is active.
- Downbeat (beat 1) uses configured downbeat color.
- Configurable: tempo_led / 4 corners / disable.
