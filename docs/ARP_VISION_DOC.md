# ARP Pattern Editor — Vision & Specification v2

## Concept

Full on-Launchpad ARP pattern creation, editing, and library management. Enter via long-press of the ARP Pattern button (E) in Instrument Mode. The 8×8 grid becomes a dual-function editor: pattern note editing AND per-step note-length control. Patterns save to a 3-page library of 24 slots via long-press on A-H buttons. Pages navigated with right-column buttons G (up) and H (down).

---

## Architecture Overview

```
Instrument Mode
    │
    ├── Normal play (grid instrument)
    │       │
    │       └── Long-press E → enters ARP Edit Mode
    │
    └── ARP Edit Mode
            │
            ├── Grid: pattern editor (notes + beat chase)
            ├── A-H buttons: long-press saves pattern to slot
            ├── Top-1 button (GREEN): exit back to instrument mode
            ├── E button (RED): note-length sub-mode
            ├── G button: page up (wraps 1→2→3→1)
            ├── H button: page down (wraps 3→2→1→3)
            │
            └── Note-Length Sub-Mode
                    ├── Grid: per-step note-length bars (RED/OFF)
                    ├── A-H buttons: set ALL steps to that length
                    ├── Top-1 button (GREEN): back to ARP edit mode
                    └── Press grid pad: set individual step length
```

---

## ARP Pattern Library

### 3 Pages × 8 Slots = 24 Patterns

| Page | Slots | Right-LED G (7) | Right-LED H (8) | Navigation |
|------|-------|-----------------|-----------------|------------|
| **1** (default) | A-H = patterns 1-8 | AMBER | GREEN | Press H → page 2 |
| **2** | A-H = patterns 9-16 | GREEN | GREEN | Press G → page 1, H → page 3 |
| **3** | A-H = patterns 17-24 | GREEN | AMBER | Press G → page 2 |

G button = page up, H button = page down. LEDs reflect available navigation directions:
- AMBER = "can't go further this way" (at boundary)
- GREEN = "can go this way" (more pages exist)

### Slot LED Mapping (A-H buttons in ARP Edit Mode)

| Button | Recommended Use |
|--------|----------------|
| A | Normal (default sequential — always present) |
| B | Chordal (root-7th-3rd-5th — always present) |
| C | Octaves (always present) |
| D-H | User patterns (5 slots per page × 3 pages = 15 custom slots) |

The 3 factory patterns (normal, chordal, octaves) occupy slots A, B, C on page 1. They CAN be overwritten via long-press save. Factory defaults are restored on `_init_defaults()` if the JSON file is deleted.

### Slot LEDs (Normal State)

| Slot Type | LED | Meaning |
|-----------|-----|---------|
| **Factory slot** (A/B/C) | RED_LOW | Protected — read-only |
| User slot (occupied) | AMBER_LOW (20%) | Has a saved pattern |
| User slot (empty) | OFF | No pattern saved |
| Currently selected | RED_HIGH (factory) / AMBER_HIGH (user) | Active pattern |
| During save (user only) | GREEN blinking (1s) | Saving to slot |

Factory slots A/B/C are read-only. Long-pressing them has no effect — no blink, no save. Only user slots D-H accept saves.

> **Implemented (BUILD_LOG #30):** long-press save is live. Slot dispatch now resolves on release — short (<500ms) selects, long (≥500ms) saves with a ~250ms GREEN/OFF blink for 1s. Factory slots still block the save.

### Saving a Pattern

1. Long-press any A-H button (500ms) while in ARP Edit Mode
2. Button blinks GREEN rapidly for 1 second
3. Pattern is saved to that slot as a JSON file
4. Blink stops → button shows AMBER_HIGH (now selected)

**File naming convention:**
```
config/arp_patterns/
├── normal.json       (factory, slot 1)
├── chordal.json      (factory, slot 2)
├── octaves.json      (factory, slot 3)
├── user_04.json      (slot 4, page 1)
├── user_05.json      (slot 5, page 1)
├── ...
├── user_24.json      (slot 24, page 3)
```

15 user slots + 3 factory slots = 18 possible files. Slots 1-8 (page 1), 9-16 (page 2), 17-24 (page 3). Empty slots have no file. Factory slots always have files.

### JSON Format (unchanged)

```json
{
    "name": "my_pattern",
    "description": "User-created pattern",
    "intervals": [0, 2, 4, 5, 7, 4, 2, 0],
    "lengths": [5, 5, 3, 5, 5, 5, 5, 5]
}
```

- `intervals`: 0-8 values. Each value is a semitone offset from the current ARP step's note. -1 = skip.
- `lengths`: 0-8 values (one per interval entry). Each value is 1-8 corresponding to the note-length level. If absent or shorter than `intervals`, defaults to 5 (standard 1/8 note).

### State Persistence

- **ARP on/off state**: Toggling ARP OFF remembers which pattern was active. Toggling ARP ON resumes with the same pattern. This survives mode switches (leaving instrument mode and returning).
- **Last active pattern**: Stored in instrument mode's `_last_arp_pattern_name`. Default: "normal".
- **Last page**: Stored in `_arp_page`. Reopens to last-used page. Default: page 1.

---

## ARP Edit Mode — Grid Layout

```
  col: 0    1    2    3    4    5    6    7
row  ┌────┬────┬────┬────┬────┬────┬────┬────┐
 7   │ 7th│ 7th│ 7th│ 7th│ 7th│ 7th│ 7th│ 7th│  ← 7th scale degree
 6   │ 6th│ 6th│ 6th│ 6th│ 6th│ 6th│ 6th│ 6th│  ← 6th scale degree
 5   │ 5th│ 5th│ 5th│ 5th│ 5th│ 5th│ 5th│ 5th│  ← 5th scale degree
 4   │ 4th│ 4th│ 4th│ 4th│ 4th│ 4th│ 4th│ 4th│  ← 4th scale degree
 3   │ 3rd│ 3rd│ 3rd│ 3rd│ 3rd│ 3rd│ 3rd│ 3rd│  ← 3rd scale degree
 2   │ 2nd│ 2nd│ 2nd│ 2nd│ 2nd│ 2nd│ 2nd│ 2nd│  ← 2nd scale degree
 1   │ R  │ R  │ R  │ R  │ R  │ R  │ R  │ R  │  ← Root / 1st degree
 0   │→   │ ·  │ ·  │ ·  │ ·  │ ·  │ ·  │ ·  │  ← Beat position indicator
     └────┴────┴────┴────┴────┴────┴────┴────┘
       S0    S1    S2    S3    S4    S5    S6    S7   (steps)
```

- **Row 0**: Beat chase. Current step = AMBER_HIGH. Others = AMBER_LOW.
- **Rows 1-7**: Scale degrees. AMBER_HIGH = note set. OFF = skip.
- **Note**: One lit pad per column.
- **Unused scale degrees** (blues = 6 notes): top rows OFF. Chromatic → locks to Major for editing.

### Beat Chase Timing

Chase speed = BPM. Each step duration = 1/2 beat (8 steps per bar at 4/4).

At 120 BPM:
- Beat period = 500ms
- Step period = 250ms (1/8 note)
- Full bar = 8 steps = 4 beats = 2 seconds

The chase LED advances from column 0→1→2...→7→0 continuously while in edit mode. Uses elapsed time since entering edit mode (not absolute BPM sync) to avoid phase issues.

---

## Note-Length Sub-Mode

Entered by pressing E (RED LED) while in ARP Edit Mode.

### Grid Layout

```
  col: 0    1    2    3    4    5    6    7
row  ┌────┬────┬────┬────┬────┬────┬────┬────┐
 7   │  ■ │    │    │  ■ │    │    │    │  ■ │  ← Level 8: Legato
 6   │  ■ │  ■ │    │  ■ │    │    │  ■ │  ■ │  ← Level 7: 1/4 note
 5   │  ■ │  ■ │    │  ■ │  ■ │    │  ■ │  ■ │  ← Level 6: Dotted 1/8
 4   │  ■ │  ■ │  ■ │  ■ │  ■ │  ■ │  ■ │  ■ │  ← Level 5: 1/8 note (default)
 3   │  ■ │  ■ │  ■ │  ■ │  ■ │  ■ │  ■ │  ■ │  ← Level 4: 1/8 triplet
 2   │  ■ │  ■ │  ■ │  ■ │  ■ │  ■ │  ■ │  ■ │  ← Level 3: 1/16 note
 1   │  ■ │  ■ │  ■ │  ■ │  ■ │  ■ │  ■ │  ■ │  ← Level 2: 1/16 triplet
 0   │  ■ │  ■ │  ■ │  ■ │  ■ │  ■ │  ■ │  ■ │  ← Level 1: 1/32 note
     └────┴────┴────┴────┴────┴────┴────┴────┘
       S0    S1    S2    S3    S4    S5    S6    S7
```

- **Lit pads**: RED_HIGH — shows the note-length "bar" for each step
- **Unlit pads**: OFF
- **Taller bars** = longer notes
- **All 8 columns represent the 8 steps** — same as pattern editor layout

### Note Length Values

| Level | Musical Duration | Relative to Step | Performance Feel |
|-------|-----------------|-----------------|------------------|
| 1 | 1/32 note | 25% of step | Ultra-staccato — click |
| 2 | 1/16 triplet | 33% of step | Very short — tight |
| 3 | 1/16 note | 50% of step | Standard short |
| 4 | 1/8 triplet | 67% of step | Medium-short |
| 5 | 1/8 note | 100% of step | **Full step (default)** |
| 6 | Dotted 1/8 | 150% of step | Overlaps slightly |
| 7 | 1/4 note | 200% of step | Long — smooth |
| 8 | Legato | No gap | Seamless — tied |

Step duration at default ARP rate (1/8 note at current BPM). At 120 BPM: step = 250ms.

Lengths 6-8 span multiple steps, creating a legato effect where notes overlap. The MIDI note stays on across step boundaries. **Implemented (BUILD_LOG #28):** playback is fully length-aware. Each step's note-off is scheduled at `now + multiplier × step_duration`. Levels 6-7 overlap into following steps; level 8 (legato) holds indefinitely until replaced by a different pitch or released on exit. A tick-driven chase loop (`_advance_chase`) schedules note-ons/offs based on elapsed time since entry (no drift) and `_fire_due_offs` retires finished notes.

### Setting Note Lengths

**Per-step (individual):**
- Press a pad at (x, y) → sets step x to length y+1 (1=bottom, 8=top)
- The column redraws to show the new bar height

**All steps (global):**
- Press right-column A-H button → sets ALL 8 steps to that button's level (0=A→1, 7=H→8)
- Visual: all 8 columns snap to the same height

### Colors (Note-Length Mode ONLY)

| Element | Color |
|---------|-------|
| Lit pad (bar) | RED_HIGH |
| Unlit pad | OFF |
| E button | RED_HIGH |
| Top-1 button | GREEN_HIGH (go back) |
| All other top row | OFF |
| Right column A-H | RED_HIGH (global set buttons) |

### Entry Animation

When entering note-length mode, the grid displays scrolling text **"LENGTH"** in **RED_HIGH** for 1 second before showing the bar-graph. This provides visual confirmation of what mode you're in. The scrolling text uses the standard 5×5 font, scrolling from right to left across the grid at ~150ms per pixel. After 1s, the text fades out and the bar-graph appears.

**Implemented (BUILD_LOG #28):** the entry scroll accepts the `LENGTH` string, renders at `RED_HIGH` only, scrolls right-to-left at ~150ms/px, and completes after 1s when the bar-graph appears. A grid/control interaction during the animation immediately swaps to the bar-graph.

### Navigation

- **Top-1 button** (GREEN): Exit note-length mode → return to ARP edit mode
- **Grid pad press**: Set individual note length
- **Right column A-H press**: Set global note length for all steps

---

## Edit Mode — Control Button Map

### Top Row (Buttons 1-8)

| Button | LED | Action |
|--------|-----|--------|
| **1** | GREEN_HIGH | Exit ARP edit → return to Instrument Mode |
| 2-8 | OFF | Unused in edit mode |

### Right Column (A-H)

| Button | LED (edit mode) | Action (short press) | Action (long press) |
|--------|-----------------|---------------------|---------------------|
| **A** | RED_LOW/HIGH | Select factory pattern A | — (protected) |
| **B** | RED_LOW/HIGH | Select factory pattern B | — (protected) |
| **C** | RED_LOW/HIGH | Select factory pattern C | — (protected) |
| **D** | AMBER_LOW/HIGH | Select pattern in slot D | Save current to slot D |
| **E** | RED_HIGH | Enter note-length mode | — |
| **F** | AMBER_LOW/HIGH | Select pattern in slot F | Save current to slot F |
| **G** | GREEN/AMBER | Page up | — |
| **H** | GREEN/AMBER | Page down | — |

---

## Complete Interaction Flow

```
Instrument Mode (normal grid instrument)
    │
    ├── Short press E: cycle ARP pattern (normal → chordal → octaves → normal)
    │
    └── Long press E (500ms): enter ARP Edit Mode
            │
            ├── Grid: pattern editor visible
            ├── Beat chase running
            ├── A-H: select/save patterns, page nav
            ├── Top-1: exit to instrument mode
            │
            ├── Short press A-H: select different pattern
            │       └── Grid updates with new pattern's notes
            │
            ├── Long press A-H: save pattern to slot
            │       └── Button blinks GREEN for 1s → saved
            │
            ├── Press pad on grid: set/clear note for that step
            │       └── ARP preview plays updated pattern
            │
            ├── Press G/H: change page
            │       └── A-H LEDs update to show new page's patterns
            │
            └── Press E (RED): enter Note-Length Mode
                    │
                    ├── Grid: bar-graph showing per-step lengths
                    ├── Top-1: back to ARP Edit Mode
                    ├── A-H: set ALL steps to this length
                    └── Press pad: set individual step length
```

---

## File Structure

```
config/arp_patterns/
├── normal.json          Factory: sequential (slot 1)
├── chordal.json         Factory: chord-tone (slot 2)
├── octaves.json         Factory: octave jumps (slot 3)
├── user_04.json         User pattern (slot 4)
├── user_05.json         User pattern (slot 5)
├── ...
└── user_24.json         User pattern (slot 24)

src/ui/modes/instrument.py    — ARP edit mode + note-length mode
```

---

## Assumptions & Risks

### A1: Long-press on E doesn't conflict with short press (pattern cycling)
**Risk:** Medium. The same button triggers two behaviors based on hold duration.
**Test:** Virtualizer — send short press (< 500ms), verify pattern cycles. Send long press (> 500ms), verify edit mode entered.
**Mitigation:** Mode base long-press infrastructure already exists (500ms threshold, `track_press`/`resolve_press`).

### A2: Saving to slot via long-press on A-H doesn't conflict with slot selection (short press on A-H)
**Risk:** Medium. Same dual-behavior pattern as E button.
**Test:** Virtualizer — short press A → selects pattern. Long press A → saves pattern.
**Mitigation:** Same long-press infrastructure. Save triggers only on "long" resolution.

### A3: 24 pattern files can be managed without naming collisions
**Risk:** Low. Fixed naming convention (`user_04.json` through `user_24.json`) prevents collisions.
**Test:** Create all 24 patterns programmatically. Verify each file is unique.
**Mitigation:** Slot-based naming, not user-named. Factory slots (1-3) are protected.

### A4: Note-lengths 6-8 (spanning multiple steps) don't cause MIDI note pileups
**Risk:** Medium. A note-off for step 3 might fire while step 4's note-on (from length 7) is still active.
**Test:** Virtualizer — set all steps to length 7, watch MIDI log for duplicate note-ons or missing note-offs.
**Mitigation:** Track active MIDI notes per step. Before sending note-on for step N, send note-off for step N's previous note. Lengths that span steps keep the note-on active until the length expires.

### A5: Beat chase stays synced with no drift over extended editing sessions
**Risk:** Low. Uses elapsed time modulo step duration. No cumulative error.
**Test:** Virtualizer — stay in edit mode for 5 minutes at 120 BPM. Verify chase position matches expected position within 1 step.
**Mitigation:** Position computed as `int((now - entry_time) / step_duration) % 8`. No drift possible.

### A6: All grid interactions are discoverable without labels
**Risk:** Medium. The MK1 has no screen — users must learn the button mappings.
**Test:** Virtualizer — verify visual hints (blinking LEDs, color changes) provide enough feedback.
**Mitigation:** Clear color language: GREEN = "go/enter/select", RED = "danger/note-length sub-mode", AMBER = "navigation/page", blinking = "saving." Top-1 always lit GREEN as the "exit" affordance.

---

## Test Plan (Virtualizer-Based)

All tests run against virtualizer + nova-script. No hardware needed.

### Test Suite 1: Edit Mode Entry/Exit
- [ ] Long-press E → enters edit mode (E blinks AMBER)
- [ ] Grid shows pattern editor layout (beat chase + scale rows)
- [ ] Short press Top-1 → exits to instrument mode
- [ ] Short press E (in edit mode) → does nothing (prevent accidental exit)

### Test Suite 2: Pattern Editing
- [ ] Press unlit pad → pad lights AMBER_HIGH, pattern updates
- [ ] Press lit pad → pad clears (OFF), becomes skip
- [ ] Only one pad per column can be lit
- [ ] Beat chase runs continuously, synchronized
- [ ] Pattern changes audible via virtual MIDI output

### Test Suite 3: Pattern Save/Load
- [ ] Long-press A → A blinks GREEN 1s → saves to `user_04.json`
- [ ] Short-press B → selects pattern from slot B, grid updates
- [ ] Empty slot (no file) → shows empty grid on select
- [ ] Factory slots A/B/C always have patterns
- [ ] Custom slot D → save pattern → exit → re-enter → press D → pattern loads

### Test Suite 4: Page Navigation
- [ ] Page 1: G=AMBER, H=GREEN
- [ ] Press H → page 2: G=GREEN, H=GREEN
- [ ] Press H → page 3: G=GREEN, H=AMBER
- [ ] Press G → back to page 2
- [ ] Page wraps correctly (page 3 + H → page 1)
- [ ] Exit + re-enter → remembers last page

### Test Suite 5: Note-Length Mode
- [ ] Press E (in edit mode) → enters note-length mode
- [ ] Grid shows bar-graph (RED bars at correct heights)
- [ ] All columns show current pattern's note lengths
- [ ] Press pad (x, y) → step x shows bar of height y+1
- [ ] Press A-H → all steps set to that level
- [ ] Top-1 → returns to edit mode
- [ ] All RED/OFF (no other colors in note-length mode)

### Test Suite 6: State Persistence
- [ ] Select pattern in slot D → exit instrument → re-enter → ARP still on pattern D
- [ ] Toggle ARP OFF → cycle instrument mode off → toggle ARP ON → same pattern playing
- [ ] Page 2 selected → exit → re-enter → page 2 still open

---

## Virtualizer Debug Panel (Enhanced)

To enable autonomous debugging without hardware:

### Additions to virtualizer HTML:
1. **Debug panel toggle** — keyboard shortcut `D` or button
2. **Grid text dump** — ASCII representation with LogicalColor names:
   ```
   [ROW 7]  OFF       AMBER_HIGH  OFF  ...
   [ROW 6]  RED_HIGH   OFF         OFF  ...
   ...
   ```
3. **MIDI message log** — last 200 messages with timestamps, decoded:
   ```
   18:03:10.123  Note ON  ch1  note=0   vel=0x33  → AMBER_HIGH  grid(0,7)
   18:03:10.124  Note ON  ch1  note=16  vel=0x01  → RED_LOW     grid(0,6)
   18:03:10.125  CC       ch1  cc=104  val=0x33  → AMBER_HIGH  top_row[0]
   ```
4. **Timing display** — BPM, beat count, ms since mode entry, message rate
5. **Color matrix** — 8×8 grid showing LogicalColor name in each cell
6. **Frame capture** — press key to freeze and download current state as JSON
7. **Message rate graph** — simple bar showing msgs/sec over last 5 seconds
