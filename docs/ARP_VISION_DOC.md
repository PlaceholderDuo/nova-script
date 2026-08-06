# ARP Pattern Editor — Vision & Specification

## Concept

Edit ARP patterns entirely on the Launchpad grid — no computer required. Long-press the ARP Pattern button (E) in Instrument Mode to enter the editor. The 8×8 grid transforms into a sequencer-style pattern view where each column represents one step of the 8-step pattern, and each row represents a scale degree. The bottom row shows a beat-position chase LED synced to the BPM clock.

## Goals

1. **Zero-computer workflow.** Create, view, edit, and save ARP patterns directly on the Launchpad. No YAML, no JSON, no text editor.
2. **Visual transparency.** The pattern is always fully visible on the grid. You can see the entire 8-step sequence at once.
3. **Musical constraint.** Notes are constrained to the active scale. You can't play wrong notes — only arrange them.
4. **Live preview.** The pattern plays as you edit, with a BPM-synced beat indicator showing current position.
5. **Persistence.** Changes save back to the JSON pattern files automatically.

---

## Entry & Exit

### Entering Edit Mode

1. **Long-press** the ARP Pattern button (E, right column index 4) for ~500ms
2. The E button begins rapid blinking (AMBER, 50% duty cycle at ~200ms period)
3. The grid switches to pattern edit mode
4. The ARP continues playing during edit — non-blocking

### Exiting Edit Mode

1. **Press E again** (short press) — returns to normal Instrument Mode
2. The edited pattern is saved to the active pattern file
3. The E button returns to its normal state LED

---

## Grid Layout

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
 0   │→   │ ·  │ ·  │ ·  │ ·  │ ·  │ ·  │ ·  │  ← Beat indicator
     └────┴────┴────┴────┴────┴────┴────┴────┘
       step step step step step step step step
        0     1     2     3     4     5     6     7
```

- **Row 0 (bottom):** Beat position indicator. One LED chases across 8 columns in sync with BPM. Current position = AMBER_HIGH. Other positions = AMBER_LOW (40%). Each step = 1/8 of a bar (1/32 note at 4/4).
- **Rows 1-7:** One row per scale degree. Row 1 = root, row 7 = 7th scale degree.
- **Active note:** Set = AMBER_HIGH (or the note color). Unset = OFF.
- **Unavailable scale degrees:** If the scale has fewer than 7 notes (e.g., blues = 6), unused rows are OFF.

---

## Note Value per Cell

Each cell at column `x`, row `y` (where y ≥ 1) represents:

```
scale_degree = y - 1    (0 = root, 6 = 7th)
interval = scale[scale_degree]  (semitones from root)
```

For Major scale [0, 2, 4, 5, 7, 9, 11], root=C:
| Row | Degree | Interval | Example (C root) |
|-----|--------|----------|------------------|
| 7   | 7th    | 11       | B                |
| 6   | 6th    | 9        | A                |
| 5   | 5th    | 7        | G                |
| 4   | 4th    | 5        | F                |
| 3   | 3rd    | 4        | E                |
| 2   | 2nd    | 2        | D                |
| 1   | Root   | 0        | C                |

**Chromatic mode behavior:** When the instrument's scale is Chromatic, the ARP locks to the **Major scale** for display and editing purposes. All 7 rows are available. The user sets intervals relative to the Major scale degrees, which are then mapped to the actual chromatic notes during playback.

**Blues scale (6 notes):** Row 7 (7th degree) is OFF and unavailable. Only rows 1-6 accept input.

---

## Interaction

### Setting a Note (press unlit pad)

1. Press pad at (column, row) where row ≥ 1 and the pad is OFF
2. Pad lights up **AMBER_HIGH**
3. Any previously lit pad in the same column turns OFF
4. The pattern updates: `intervals[column] = scale[row-1]`
5. The ARP immediately plays the updated pattern on the next cycle

### Clearing a Note (press lit pad)

1. Press pad at (column, row) where row ≥ 1 and the pad is AMBER_HIGH
2. Pad turns OFF
3. The pattern updates: `intervals[column] = -1` (representing a skip/rest in the pattern)
4. The ARP skips this column on the next cycle

### Beat Indicator Behavior

- Chases from column 0 → column 7, then wraps to column 0
- Timing: each step = BPM period / 8 (e.g., 120 BPM = 62.5ms per step)
- Current step column lights AMBER_HIGH
- All other columns light AMBER_LOW (dim orange)
- The chase runs continuously while in edit mode

### Saving

- Pattern is saved **automatically** on exit to the active pattern file
- File location: `config/arp_patterns/{name}.json`
- Format: same JSON structure with `intervals` array
- Skip/rest entries are excluded from the saved pattern (array length may be < 8)

---

## Color Scheme

| State | Color | Meaning |
|-------|-------|---------|
| Beat indicator (current) | AMBER_HIGH | Currently playing step |
| Beat indicator (other) | AMBER_LOW | Future/past steps |
| Active note | AMBER_HIGH | Note set at this step |
| Unset position | OFF | No note at this step |
| Unavailable degree | OFF | Scale has fewer than 7 notes |
| E button (blinking) | AMBER | 200ms period, 50% duty — edit mode active |

---

## Assumptions & Risks

### Assumption 1: Long-press on E is detectable and doesn't conflict with normal press
**Risk:** The E button's normal behavior is to cycle through ARP patterns (1→2→3). A long press must be distinguished from a short press.
**Mitigation:** Use the existing long-press infrastructure in Mode base (500ms threshold). On release, check `resolve_press()` — if "long", enter edit mode. If "short", cycle pattern normally.

### Assumption 2: The ARP can continue playing while the grid is in edit mode
**Risk:** The ARP uses `_active_notes` and `_advance_arp()` which read from the pattern. If we're editing the pattern while ARP is running, we need to handle concurrent modification safely.
**Mitigation:** The pattern intervals are small integers (an array of ≤8 values). Use a copy-on-write pattern: the editor modifies a local `_edit_intervals` list, and `_advance_arp()` reads from the same list. The list is written atomically (single index assignment). Python's GIL ensures no race condition in the asyncio event loop (single-threaded).

### Assumption 3: The beat indicator chase can be rendered at the right speed
**Risk:** The chase must be BPM-synced and visually smooth. At 120 BPM, each step is 62.5ms — frame updates must be fast enough to avoid stutter.
**Mitigation:** The engine's tick loop already runs at up to 100Hz (10ms timeout). A 62.5ms step duration has ~6 ticks per step, which is smooth enough for a visual chase. We track elapsed time and compute step position from BPM.

### Assumption 4: All 7 scale rows fit within the 8×8 grid
**Risk:** Rows 1-7 use 7 of 8 available rows, leaving only row 0 for the beat indicator. This works for 8×8.
**Verification:** Grid is 8 high. Row 0 = beat, rows 1-7 = scale degrees. Fits exactly. ✓

### Assumption 5: Patterns with < 8 entries (skips) save and load correctly
**Risk:** The JSON format has a fixed-length `intervals` array. Skips in the pattern create shorter arrays.
**Mitigation:** The `intervals` array is variable-length (0-8 entries). When loading, pad missing entries with skips. When saving, trim trailing skips. The ARP playback engine already handles variable-length patterns via `len(intervals)`.

### Assumption 6: Chromatic scale locking to Major for ARP editing is intuitive
**Risk:** Users in Chromatic mode might expect all 12 notes to be available.
**Mitigation:** Display a brief hint ("M" in GREEN) when entering edit mode in Chromatic scale, indicating the ARP is locked to Major scale for editing. This matches real hardware behavior on Akai Force and similar devices that constrain ARP to a scale even in chromatic note mode.

---

## Implementation Plan

### Phase 1: Core Editor UI (no playback during edit)
1. Add `_arp_edit_mode` flag to InstrumentMode
2. Detect long-press on E button → enter edit mode
3. Render the edit grid (beat indicator + scale rows)
4. Handle pad presses (set/clear notes in pattern)
5. Exit on E press → save pattern, return to instrument mode

### Phase 2: Live Playback During Edit
1. While in edit mode, continue advancing the ARP
2. Beat indicator chases in sync with the ARP's own step counter
3. Pattern changes take effect immediately on next ARP cycle

### Phase 3: Visual Polish
1. E button rapid blink (200ms period)
2. Dim beat indicators for non-current steps
3. Color-coded scale rows (optional: root row slightly different color)
4. Hint display on entry if in Chromatic mode

---

## File Changes (anticipated)
- `src/ui/modes/instrument.py` — Add edit mode state, render logic, interactions
- `config/arp_patterns/*.json` — Updated by editor on save

---

## Questions to Resolve

1. **Should the pattern editor work in scales with < 7 notes?** Current plan: yes, unused rows are OFF and unresponsive.
2. **Should the saved pattern retain skip positions?** Current plan: yes, skips are excluded from the JSON intervals array.
3. **Should pressing a pad produce sound (MIDI note) or just set the pattern?** Current plan: just set the pattern. The ARP playback handles sound. This avoids audio clutter during editing.
4. **What happens if user exits edit mode with an empty pattern (all skips)?** Restore the previous pattern from memory (don't save empty).
