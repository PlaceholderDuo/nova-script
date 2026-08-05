# Implementation Plan — Post-Research Rendering & Optimization

Based on findings in `docs/MIDI_LED_CONTROL_RESEARCH.md`

---

## Phase 1: Diff-Based Rendering (eliminate clear()-first pattern)

**The Problem:** Every mode calls `self.clear()` → render cells → `self.commit()`. This sends 64 OFF + 64 ON = 128 messages per frame. The OFF messages create a single-frame black flash visible on hardware.

**Target files:**
- `src/ui/mode.py` — Mode base class `commit()` and new `clear()` behavior
- `src/controllers/base.py` — `set_grid_color()` diff check
- `src/ui/modes/performance.py` — remove `self.clear()`
- `src/ui/modes/clip_launcher.py` — remove `self.clear()`
- `src/ui/modes/sequencer.py` — remove `self.clear()`
- `src/ui/modes/mixer.py` — remove `self.clear()`
- `src/ui/modes/instrument.py` — remove `self.clear()`
- `src/ui/modes/menu.py` — remove `self.clear()`
- `src/ui/overlay_manager.py` — `_render_screensaver_image` etc.

**Implementation:**

### 1.1 — Controller-Side Diff in `set_grid_color()`

```python
# src/controllers/base.py — set_grid_color
def set_grid_color(self, x: int, y: int, color: LogicalColor):
    if not (0 <= x < grid_w and 0 <= y < grid_h):
        return
    if self._grid_state[y][x] == color:
        return  # ← NEW: skip if unchanged
    self._grid_state[y][x] = color
    self.send_led(x, y, color)
```

**Impact:** Even without mode changes, this halves MIDI traffic for renders where cells don't change. A re-render of the same state sends 0 messages instead of 64.

### 1.2 — LogicalGrid: Iterate Cells Without Clear

```python
# src/layout/grid.py — new methods
def iter_cells(self):
    """Yield (x, y, color) for all cells, defaulting to OFF."""
    for y in range(self.height):
        for x in range(self.width):
            yield x, y, self._cells.get((x, y), LogicalColor.OFF)

def apply_grid(self, other: 'LogicalGrid'):
    """Mark cells dirty where self differs from other."""
    self._dirty.clear()
    for x, y, color in other.iter_cells():
        if self.get_cell(x, y) != color:
            self.set_cell(x, y, color)
```

### 1.3 — Mode Base: New Render Pattern

```python
# src/ui/mode.py
def render_to(self, target_grid):
    """Override in subclasses. Fill target_grid with new state."""
    pass

def commit_diff(self):
    """Send only changed cells to hardware."""
    for x, y in self.grid.dirty_cells():
        color = self.grid.get_cell(x, y)
        self.controller.set_grid_color(x, y, color)
    # dirty_cells() consumes the set

def clear(self):
    """Explicit clear for transitions. Use sparingly."""
    self.grid.clear()
```

### 1.4 — Each Mode: Replace `_render()` with `render_to()`

Instead of:
```python
def _render(self):
    self.clear()
    # ... draw cells ...
    self.commit()
```

Do:
```python
def _render(self):
    # ... draw cells ...
    self.commit_diff()
```

The mode draws directly onto `self.grid`. Cells that are OFF just don't get `set_cell()` called. The LogicalGrid defaults to OFF for unset cells. `commit_diff()` sends only cells that changed from last frame.

### 1.5 — Mode Transition: `clear()` Only on Enter/Exit

`enter()` calls `self.clear()` followed by first render. This is correct — we need a full paint on mode switch. `exit()` calls `self.clear()` to blank everything before next mode renders.

---

## Phase 2: Tick Throttle (stop rendering on every engine tick)

**The Problem:** The engine's `_tick()` runs at up to 10Hz idle. Most modes call `_render()` inside `tick()`, causing thousands of LED messages per second for no reason.

**Target files:**
- `src/ui/mode.py` — `_needs_render` flag
- All mode `tick()` methods — guard with flag

### 2.1 — Add `_needs_render` to Mode Base

```python
class Mode(ABC):
    def __init__(self, ...):
        ...
        self._needs_render: bool = True  # render on first tick
    
    def mark_dirty(self):
        self._needs_render = True
    
    def tick(self, delta_ms: float):
        if self._needs_render:
            self._needs_render = False
            self._render()
```

### 2.2 — Each Mode: Call `mark_dirty()` on State Changes

Any method that changes visible state calls `self.mark_dirty()`. For example:

```python
# performance.py
def _toggle_mute(self, track_idx):
    ...
    self.mark_dirty()

# instrument.py
def _cycle_scale(self):
    ...
    self.mark_dirty()

def handle_grid_event(self, event):
    ...
    self.mark_dirty()
```

### 2.3 — ARP/Animation Exceptions

Modes with time-based animations (ARP, BPM pulses, tuner strobe) call `self.mark_dirty()` each time step. This is correct — they genuinely change state at BPM rate.

---

## Phase 3: Connection State Restoration

**The Problem:** When nova-script starts before the Launchpad connects, render commands are silently dropped. On connect, the hardware shows whatever `on_connect()` renders (typically clear_grid + top row + right column), but the mode's logical state may not be re-synced.

**Target files:**
- `src/engine.py` — `_on_device_connect`
- `src/controllers/base.py` — `refresh_grid()` enhancement

### 3.1 — Verify `_on_device_connect` → `mode.enter()`

Already calls `mode.enter()` which triggers a full render. This is correct. Verify with virtualizer test.

### 3.2 — Add `refresh_grid()` to Controller Base

```python
def refresh_grid(self):
    """Force all 64 cells to re-send to hardware. Use after reconnect."""
    for y in range(self.capabilities.grid_height):
        for x in range(self.capabilities.grid_width):
            self.send_led(x, y, self._grid_state[y][x])
```

### 3.3 — On-Connect Sequence

```python
def _on_device_connect(self, device_name):
    ...
    controller.on_connect()      # reset, kick, clear
    controller.refresh_grid()    # re-sync hardware from software state
    if mode:
        mode.mark_dirty()        # force re-render
```

---

## Phase 4: Overlay Manager Optimization

**The Problem:** The overlay manager's `_tick_screensaver` and other tick methods run every engine cycle, checking time intervals. This is fine for timing checks but `_render_screensaver_image` already calls `grid.clear()` + render + commit — 128 messages per cycle switch.

**Target file:** `src/ui/overlay_manager.py`

### 4.1 — Use `grid.clear()` Only on Overlay Entry/Exit

When transitioning ACTIVE_MODE → SCREENSAVER:
- `_enter_overlay()` does NOT call clear — the mode's exit already did
- `trigger_screensaver()` renders the first image

When cycling images within screensaver:
- `_tick_screensaver` called `_render_screensaver_image()` which now has `grid.clear()` (added in last fix)
- This is correct — we want the old image fully cleared before new one renders

When exiting overlay:
- `_dismiss_overlay()` → enter ACTIVE_MODE → mode re-renders

### 4.2 — Check: Is clear() needed per cycle?

Yes — the screensaver images have different lit cells. Without clear, OFF cells from the new image won't overwrite ON cells from the old image. The screensaver cycle IS a full-replace operation, so clear() is appropriate here.

However, the MIDI messages from `clear()` (64 OFF + 64 ON = 128) happen every 4 seconds. That's only ~32 msg/s average, which is fine.

---

## Phase 5: Startup Wave Refinement

**The Problem:** The startup wave currently sends 64 LED messages per frame via `_commit()` which loops over all cells. With the diff-based `set_grid_color`, this will naturally be optimized — the wave already calls `grid.clear()` at the start of each frame and only sets specific cells, so only those cells will differ from the controller's state.

**Target file:** `src/ui/startup_wave.py`

### 5.1 — Already Efficient

The startup wave already uses `dirty_cells()` in `_commit()`. No changes needed here. The transparent diff optimization in `set_grid_color` will further reduce messages for frames where a cell gets the same color as the previous frame.

---

## Implementation Order

| # | Task | Files | Risk | Effort |
|---|------|-------|------|--------|
| 1 | `set_grid_color` diff check | `base.py` | Low | 2 lines |
| 2 | `_needs_render` flag + Mode base tick guard | `mode.py` | Low | 5 lines |
| 3 | Remove `clear()` from Performance mode | `performance.py` | Medium | Replace clear+commit pattern |
| 4 | Remove `clear()` from Instrument mode | `instrument.py` | Low | Already mostly diff-based |
| 5 | Remove `clear()` from Clip Launcher | `clip_launcher.py` | Medium | BPM pulsing may need care |
| 6 | Remove `clear()` from Sequencer | `sequencer.py` | Medium | Step grid pattern |
| 7 | Remove `clear()` from Mixer | `mixer.py` | Low | Fader bars pattern |
| 8 | Remove `clear()` from Menu | `menu.py` | Low | Static blocks |
| 9 | Add `mark_dirty()` to all state-change methods | All modes | Medium | Each control handler |
| 10 | Verify on-connect re-render via virtualizer | `engine.py` | Low | Integration test |
| 11 | Add `refresh_grid()` to controller | `base.py` | Low | New method |

---

## Verification Plan

For each phase, test with the virtualizer:

1. **Start virtualizer + nova-script** → verify mode renders correctly
2. **Switch between modes** → verify no black flash (check virtualizer state during transition)
3. **Idle for 10 seconds** → verify MIDI message count drops to near-zero (no re-renders)
4. **Interact with controls** → verify LED updates happen immediately
5. **Start nova-script before virtualizer** → verify on-connect re-render fills grid correctly
6. **Screensaver cycle** → verify clean transition between images

---

## Expected Metrics After Phase 1-3

| Metric | Before | After | Reduction |
|--------|--------|-------|-----------|
| Messages per mode switch | 128 (64 OFF + 64 ON) | ~64 (diff only) | ~50% |
| Messages per idle tick | 0-64 (mode dependent) | 0 | ~100% |
| Messages per screensaver cycle | 128 | 128 (full replace) | same |
| Startup wave frames | 20 × 64 = 1280 | 20 × ~10 = ~200 | ~84% |
| Visual flicker between renders | Yes (perceivable) | No | Eliminated |

---

## Risks

**Risk 1: Retained OFF cells.** If a mode renders fewer cells than the previous frame (e.g., transitioning from 8 tracks to 4), the OFF cells for tracks 5-8 won't be sent because the mode never calls `set_cell(OFF)` for them. 

**Mitigation:** Modes must explicitly set OFF for cells that should no longer be lit. The LogicalGrid defaults to OFF for unset cells, and `iter_cells()` returns OFF for them. If the mode draws a sparser grid, the diff will detect cells that went from ON→OFF and send the OFF message.

**Risk 2: Instrument mode root note movement.** When changing octave offset, the root notes change position. Since we don't clear, the old root positions would retain RED_HIGH. 

**Mitigation:** The instrument mode re-renders ALL 64 cells on every `_render()`. With the diff, only changed cells send MIDI. Root positions that moved will get the diff (old→OFF, new→RED) correctly.

**Risk 3: BPM clock LED unlit.** The top row LED blinking uses `send_top_row_led` directly (not through LogicalGrid/commit). 

**Mitigation:** Already using direct send — no change needed. The diff optimization only affects grid pad rendering.
