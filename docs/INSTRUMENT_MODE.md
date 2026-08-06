# Instrument Mode — Vision & Specification

## Concept

Instrument Mode transforms the Launchpad Mini MK1 into a grid-based instrument controller, modeled after Ableton Live's Push grid instrument and the Akai Force's MIDI instrument track. The full 8×8 grid becomes a scale-mapped playing surface where every pad is a musical note — no dead zones, no menu blocks.

## Design Goals

1. **Every pad is playable.** All 64 pads map to notes in the selected scale.
2. **Minimal cognitive load.** Root notes glow red. Pressed notes glow green. Everything else is a soft amber — an always-visible, never-distracting canvas.
3. **Push-style architecture.** Right column controls mode parameters. Top row doubles as overlay for A-button offset selection. No mode-switching mid-performance — stay in the flow.
4. **Extensible ARP.** ARP patterns live as JSON files. Replace them with custom patterns by dropping a same-named file into the folder.
5. **Virtualizer-compatible.** Full visual feedback in the browser-based virtualizer for development without hardware.

---

## Grid Layout

```
  x: 0    1    2    3    4    5    6    7
y:┌────┬────┬────┬────┬────┬────┬────┬────┐
7 │  C │  D │  E │  F │  G │  A │  B │  C │  ← +7·offset
6 │  C │  D │  E │  F │  G │  A │  B │  C │  ← +6·offset
5 │  C │  D │  E │  F │  G │  A │  B │  C │  ← +5·offset
4 │  C │  D │  E │  F │  G │  A │  B │  C │  ← +4·offset
3 │  C │  D │  E │  F │  G │  A │  B │  C │  ← +3·offset
2 │  C │  D │  E │  F │  G │  A │  B │  C │  ← +2·offset
1 │  C │  D │  E │  F │  G │  A │  B │  C │  ← +1·offset
0 │  C │  D │  E │  F │  G │  A │  B │  C │  ← root row
  └────┴────┴────┴────┴────┴────┴────┴────┘
   R    □    □    □    □    □    □    R

R = RED_HIGH  (root note — same pitch class as configured root)
□ = AMBER_LOW (background — all pads show scale notes)
```

**Note calculation:**
```
scale_index = x % len(scale)
octave_shift = (x // len(scale)) * 12
row_offset = y * note_offset
note = root_note + scale[scale_index] + octave_shift + row_offset
```

### Row Offset (Note Offset)

Each row above the bottom is offset by a configurable number of semitones. This is the "In Key" interval spacing — identical to Ableton Push's row offset.

| Setting | Offset | Effect |
|---------|--------|--------|
| Octaves | 12 semitones | Same notes, higher octaves. Safe, predictable. |
| 2 | 2 semitones | Whole-step rows. Diagonal runs ascend chromatically. |
| 3 | 3 semitones | Minor-third rows. |
| 4 | 4 semitones | Major-third rows. Rich harmonic spread. |
| 5 | 5 semitones | Fourth rows. Circle-of-fourths layout. Experimental. |

**To change offset:** Hold the A (right column) button. It flashes. Top row pads 1-5 light up orange. Tap the desired offset pad (it turns green). Release A to confirm.

---

## Color System

| State | Color | Brightness | Meaning |
|-------|-------|------------|---------|
| Root note | RED_HIGH | 100% | Pad plays a note whose pitch class matches the root |
| Pressed pad | GREEN_HIGH | 100% | Currently held down |
| Octave of pressed | GREEN_MED | ~70% | Same pitch class, different octave — visual anchor |
| Background | AMBER_LOW | ~40% | Playable pad in scale — soft, always visible |

**Why these colors:** The MK1 Launchpad has only red, green, and amber (red+green simultaneously). RED for roots (sharp, structural), GREEN for interaction (safe, go), AMBER for canvas (warm, neutral). All at LOW brightness except for interaction states — gentle on the eyes during long sessions.

---

## Right Column Controls (A–E)

Pressing a right-column button cycles through its options. Current state is shown by the button's LED color.

### A — Notes / Chords
| State | LED | Behavior |
|-------|-----|----------|
| **Notes** (default) | GREEN_HIGH | Single note per pad |
| **Chords** | AMBER_HIGH | Chord based on scale degree (major: root+3rd+5th, blues: root+3rd+5th+7th, chromatic: root+3rd+5th) |

Toggling disables the A-button hold overlay for offset selection.

### B — Scale
| State | LED | Scale | Notes |
|-------|-----|-------|-------|
| **Major** (default) | GREEN_HIGH | [0,2,4,5,7,9,11] | Standard 7-note scale |
| **Blues** | AMBER_HIGH | [0,3,5,6,7,10] | 6-note blues scale |
| **Chromatic** | RED_HIGH | [0-11] | All 12 notes |

Changing scale releases all held notes and re-renders the grid.

### C — Hold
| State | LED | Behavior |
|-------|-----|----------|
| **OFF** (default) | RED_HIGH | Note stops on pad release |
| **ON** | GREEN_HIGH | Note sustains until pad is pressed again or different pad pressed |

Hold co-exists with ARP — the arpeggiator keeps running on held notes until dismissed.

### D — ARP (Arpeggiator)
| State | LED | Behavior |
|-------|-----|----------|
| **OFF** (default) | RED_HIGH | No arpeggiation |
| **Up** | GREEN_HIGH | Arpeggiates held note(s) ascending |
| **Down** | AMBER_HIGH | Arpeggiates held note(s) descending |

ARP step timing: 1/16 note at current BPM (configurable). ARP fires note-off for previous step, note-on for current step, cycling through active notes.

### E — ARP Pattern
| State | LED | Pattern File | Behavior |
|-------|-----|-------------|----------|
| **Normal** (default) | GREEN_HIGH | `normal.json` | Sequential note offsets [0,1,2,3,4,5,6,7] |
| **Chordal** | AMBER_HIGH | `chordal.json` | Root, 7th, 3rd, 5th, root... — chord tone arpeggiation |
| **Octaves** | RED_HIGH | `octaves.json` | 3-octave span jumps [0,7,14,7,0,...] |

Patterns live in `config/arp_patterns/`. To customize: replace the JSON file with same-named file containing `{"name": "...", "intervals": [...]}`. Intervals are semitone offsets from the note at the current ARP step position.

### Controls A–E not mapped

Buttons F, G, H (indices 5–7) are reserved for future use. Currently OFF.

### Visual Hints (Non-Blocking Overlays)

When any right-column control button is pressed, a brief 5×5 letter overlay appears on the grid for 300ms. The letter and color indicate the **new state** the control is switching to. Hints are completely non-blocking — pad presses, ARP, and all other interactions continue normally while the hint is visible.

| Control | What You See | Colors |
|---------|-------------|--------|
| **B (Scale)** | `S` / `B` / `C` | RED (all scale hints) |
| **C (Hold)** | `H` | GREEN=ON, RED=OFF |
| **D (ARP)** | `A` | RED=OFF, GREEN=Up, AMBER=Down |
| **E (ARP Pat)** | `1` / `2` / `3` | GREEN=Normal, AMBER=Chordal, RED=Octaves |

**Why 300ms:** Long enough to read, short enough to not interfere with playing. The grid returns to its normal instrument display automatically — no press required to dismiss.

**Design rationale:** The hint letters spell out the mode (S=Scale, B=Blues, C=Chromatic) in RED for consistency across all scale changes. When the user double-presses rapidly to skip to a mode 2-states away, the first hint is immediately replaced by the second — no overlap or animation queue.



---

## Interaction Flow

### Playing a Note
1. Tap any pad → GREEN_HIGH, note sent via MIDI (channel configurable)
2. Release pad → returns to background AMBER_LOW, note-off sent
3. Same pitch class in other octaves → GREEN_MED while held (octave indicator)

### With Hold ON
1. Press pad → GREEN_HIGH, note sustains
2. Release pad → stays GREEN_HIGH, note continues
3. Press same pad again → returns to background, note-off sent
4. Press different pad → old pad returns to background, old note stops, new note starts

### With ARP ON
1. Press pad(s) → green, notes captured by arpeggiator
2. ARP cycles through held notes at 1/16-note timing
3. Pattern determines the interval sequence
4. Direction (up/down) determines order
5. Release with Hold ON → ARP continues on held notes

### Changing Offset
1. Hold A button → A flashes, top-row pads 1-5 appear as overlay (ORANGE except current = GREEN)
2. Tap desired offset pad → A stops flashing, new offset applied
3. Grid re-renders immediately with new row spacing

---

## MIDI Output

Instrument mode sends MIDI notes to a configurable output. Default: MIDI channel 1, note velocity 100. Each pad press sends `NOTE ON` with the calculated note number and velocity. Release sends `NOTE OFF`.

Future: configurable MIDI channel and velocity curve.

---

## File Structure

```
src/ui/modes/instrument.py     — Mode class (423 lines)
config/arp_patterns/
  normal.json                   — Sequential pattern
  chordal.json                  — Chord-tone pattern (root-7th-3rd-5th)
  octaves.json                  — Octave-jump pattern
```

### ARP Pattern JSON Format
```json
{
    "name": "pattern_name",
    "description": "What this pattern does",
    "intervals": [0, 1, 2, 3, 4, 5, 6, 7]
}
```

`intervals` is an array of semitone offsets applied to each ARP step. The pattern cycles: step N uses `intervals[N % len(intervals)]` added to the current held note. The held note index advances after each complete pass through the intervals.

---

## Scales Reference

| Scale | Intervals | Notes (C root) | Grid feel |
|-------|-----------|----------------|-----------|
| Major | 0,2,4,5,7,9,11 | C D E F G A B | Full, bright |
| Blues | 0,3,5,6,7,10 | C Eb F F# G Bb | Soulful, 6-note |
| Chromatic | 0-11 | All 12 notes | Experimental, no wrong notes |

## Known Limitations (current)

- Root note is fixed at MIDI note 48 (C3). No transposition yet.
- MIDI output channel is not configurable.
- Chords mode uses fixed triad patterns per scale.
- No velocity sensitivity (MK1 limitation — all notes at velocity 100).
- ARP timing is fixed at 1/16 per BPM beat.
- Offset overlay uses top-row pads 1-5 which are also mode shortcut buttons — overlay takes priority.

## Future Ideas

- **Tap tempo** — hold F to tap BPM
- **Transpose** — hold G + press pad to set new root
- **Custom scales** — user-defined scale JSON files
- **Velocity curve** — simulate velocity via pad position or pressure duration
- **Sustain pedal** — external MIDI CC sustain
- **Multi-track** — send different rows to different MIDI channels
- **Record/loop** — capture and loop a sequence directly from the grid
