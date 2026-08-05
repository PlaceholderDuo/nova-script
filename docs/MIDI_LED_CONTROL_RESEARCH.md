# MIDI LED Control Research — Launchpad Mini MK1 & Novation Ecosystem

## 1. How the Hardware Actually Works

### Physical Architecture

The Launchpad Mini MK1 uses a **multiplexed LED matrix** controlled by an embedded microcontroller (likely a PIC or ARM Cortex-M). The 64 grid pads + 8 top row + 8 right column = 80 LEDs total. LEDs are driven via a **scanning matrix** — rows are activated one at a time, columns supply current. This is how the MK1 achieves 80 individually-addressable bicolor LEDs with a low pin-count MCU.

Key implications of the scanning matrix:
- LEDs are NOT continuously lit. They're pulsed at a high refresh rate (>1kHz).
- Perceived brightness is controlled by **PWM duty cycle**, not voltage.
- The 3 brightness levels (LOW/MED/HIGH) are implemented in the MCU firmware.
- **There is NO double-buffering.** State is applied immediately as MIDI messages arrive.

### MIDI Protocol Fundamentals

The MK1 presents as a standard USB MIDI device (class-compliant, no drivers needed). It operates on **MIDI channel 1** exclusively.

**Grid pads — Note On (0x90):**
- Each pad is a MIDI note in the range 0-127
- Note number encoding: `note = (7 - row) * 16 + col` where `(0,0)` is bottom-left, `(7,0)` is top-left
- Velocity byte controls LED state: bits 4-5 = green level (0-3), bits 0-1 = red level (0-3)
- `note = 0` → top-left pad, `note = 127` → bottom-right pad
- RIGHT COLUMN buttons are also Note On messages on notes 8, 24, 40, 56, 72, 88, 104, 120

**Top row — CC (0xB0):**
- Controllers 0x68-0x6F → top row buttons 1-8
- Value byte uses same green/red encoding as Note velocity
- CC 0x00 on channel 1: special reset/buffer kick command

**Color encoding (velocity/value byte):**
```
velocity = (green_level << 4) | red_level

green_level: 0=off, 1=low, 2=medium, 3=high
red_level:   0=off, 1=low, 2=medium, 3=high

AMBER = both green AND red active simultaneously (two physical LEDs)
```

| Value | Hex  | Green | Red | Color       | Brightness |
|-------|------|-------|-----|-------------|------------|
| 0     | 0x00 | 0     | 0   | OFF         | —          |
| 1     | 0x01 | 0     | 1   | RED_LOW     | LOW        |
| 2     | 0x02 | 0     | 2   | RED_MED     | MED        |
| 3     | 0x03 | 0     | 3   | RED_HIGH    | HIGH       |
| 16    | 0x10 | 1     | 0   | GREEN_LOW   | LOW        |
| 32    | 0x20 | 2     | 0   | GREEN_MED   | MED        |
| 48    | 0x30 | 3     | 0   | GREEN_HIGH  | HIGH       |
| 17    | 0x11 | 1     | 1   | AMBER_LOW   | LOW        |
| 34    | 0x22 | 2     | 2   | AMBER_MED   | MED        |
| 51    | 0x33 | 3     | 3   | AMBER_HIGH  | HIGH       |

**Critical detail:** The green and red LEDs are physically separate dies in the same package. AMBER is produced by illuminating both simultaneously. Due to manufacturing variance, LED aging, and diffuser yellowing, the exact perceived amber color varies between units. The green LED runs through a ~525nm die; the red through ~625nm.

### LED Control Behavior — No Caching, No Double-Buffer

**The MK1 has NO internal LED state cache.** The microcontroller does not maintain a copy of the current LED state. Each MIDI message overrides the LED state for that specific pad immediately. This means:

1. **State is held in hardware output registers** — Once set, a pad stays lit at its assigned brightness until a new message changes it.
2. **No frames, no vsync** — There is no concept of a "frame" or "swap buffer." Each message is applied as it arrives.
3. **No bulk clear** — There is no "clear all" MIDI message. Each pad must be individually set to OFF (velocity 0).
4. **Reading back state is impossible** — The MCU does not expose LED state for querying. Host must track state in software.

**Implication for nova-script:** The `LogicalGrid` and `grid_state` in `NovationController` are **essential** — they are the ONLY source of truth for what's displayed. The hardware cannot be queried. Our software grid IS the state.

### Maximum Update Rate

USB MIDI on the MK1 is **USB 1.1 Full Speed (12 Mbps)**. The MIDI class driver processes messages at the USB frame rate (1ms intervals on USB 1.1).

- Theoretical max: ~1000 MIDI messages/second (one per USB frame)
- Practical max: ~800-900 messages/second (sustained)
- Single pad update: 3 bytes → ~0.25µs to transmit
- Full grid clear (64 pads): 64 × 3 = 192 bytes → ~2ms at full bandwidth

**The MK1 processes LED messages asynchronously from the USB stack.** The MCU's main loop services USB interrupts, then updates the LED matrix in the next scan cycle. This means LED updates are NOT guaranteed to be atomic or synchronized. Rapid updates may cause brief visual artifacts (e.g., one row updating before another in the same scan cycle).

**In practice:** Sending 64 LED messages in rapid succession (as nova-script does on every `clear()` + render) takes approximately 2-5ms. The user typically cannot perceive this flicker. However, at high update rates (every tick/every frame), the visual result may appear "busy" or "shimmering."

### The "Automap Kick" — What It Actually Does

```python
for i in range(8):
    send([0xB0, 0x68 + i, 0x33])  # Set top-row LED to AMBER briefly
    send([0xB0, 0x68 + i, 0x00])  # Turn it off
send([0xB0, 0x00, 0x00])           # Reset/buffer kick
```

This sequence serves two purposes:

1. **Flush stale button input** — The MK1 buffers button state events. Sending LED messages to the top row forces the MCU to flush any pending button-press data in its USB buffer. The 0x33→0x00 pairs are discarded by the LED controller but trigger the MCU's input processing. This prevents "phantom" button presses from being sent after the host connects.

2. **Reset session mode** — `[0xB0, 0x00, 0x00]` forces the MK1 into "Session Mode" (LEDs controlled exclusively by the host). This is the only mode where all 64 grid pads + top row + right column are independently addressable by the host.

**Without the automap kick:** The MK1 may send buffered button-press data from before the host connected, or may remain in a layout mode where some LEDs are internally controlled. The kick is required for clean initialization.

### Session Mode vs. Layout Modes

The MK1 has 3 internal layout modes selected via `[0xB0, 0x00, value]`:

| Value | Mode | LED Control |
|-------|------|-------------|
| 0x00 | Session | Host controls all LEDs |
| 0x01 | User 1 | Layout mode 1 — some LEDs auto-controlled |
| 0x02 | User 2 | Layout mode 2 — different auto-layout |

**nova-script must always be in Session Mode (0x00).** The reset command in `_reset_to_session()` ensures this.

---

## 2. How MIDI LED Control Works Across Novation Devices

### Launchpad MK1 (original) vs Mini MK1

The original Launchpad MK1 uses the **exact same protocol** as the Mini MK1. Same note mapping, same color encoding, same CC ranges. The only differences:
- Original MK1 is larger (108mm square pads vs Mini's ~80mm)
- Original MK1 has more side buttons (Scene buttons on the right, dedicated transport row)
- The note numbers for side buttons differ slightly
- Otherwise, firmware-identical for grid + top row control

### Launchpad MK2

The MK2 transitioned to **full RGB LEDs** with a 128-color palette. Key differences:
- Note/CC mapping remains the same (backward compatible)
- LED control uses a **palette-based system**: first you set palette entries (color lookup table), then refer to palette indices when setting pads
- Supports SysEx for bulk palette updates (more efficient than per-pad messages)
- OFF is palette index 0

### Launchpad MK3 / Mini MK3 / Pro MK3

Dramatically different protocol:
- Introduces **double-buffering** for LED state — two display buffers, swapped via a "display" command
- SysEx-based bulk LED update (all 64 pads in one message)
- Programmer mode vs Live mode (different MIDI port interfaces)
- RGB palette per pad (not shared palette)
- Velocity-sensitive pads (poly aftertouch)
- DAW integration mode

### Launchkey 49 MK2

Uses yet another protocol:
- LED control on **MIDI channel 16** (0x9F)
- 128-entry palette, updated via CC messages
- Different note map for the 8×2 pad grid
- Extended mode for InControl DAW integration
- Transport controls send CC messages (not Note)

### General MIDI LED Control Principles

Across ALL Novation controllers, these principles hold:

1. **MIDI messages ARE the LED commands** — There is no separate "LED protocol." Note On velocity and CC value are the LED states.
2. **State is fire-and-forget** — The host sends an LED value; the controller applies it. There is no acknowledgment, no handshake, no query.
3. **Timing is not real-time** — LED updates are not isochronous. USB jitter, MCU scan cycles, and message queuing mean there is **no guaranteed latency** for LED changes. This makes beat-synced visual effects inherently approximate.
4. **No atomicity guarantees** — When updating multiple LEDs, there is no "present" or "swap" command on MK1/MK2. Visual tearing (partial updates) is possible during rapid multi-pad changes.

---

## 3. Game-Changing Insights for Nova-Script

### Insight #1: clear() + render() = Wasted Bandwidth

Every time we call `clear()` then `render()` then `commit()`, we send 64 LED messages — even if only 5 cells changed. The MK1 doesn't care (it applies them instantly), but this is **wasteful MIDI bandwidth** and causes unnecessary USB traffic.

**What we should do:**
- Track a "previous frame" buffer in the controller (`_previous_grid_state`)
- On commit, only send messages for cells that **actually changed** between frames
- This is already partially implemented via `dirty_cells()`, but `clear()` marks ALL cells dirty
- **Fix: Don't use `clear()` before render. Instead, render the new state and compare diffs at commit time.**

**Impact:** 64 messages → ~5-10 messages per typical mode tick. 6-12x reduction in MIDI traffic.

### Insight #2: The "No Double-Buffer" Problem

Because the hardware has no double-buffer and applies updates immediately, a mode that calls `clear()` first will briefly flash all pads OFF before rendering the new state. This is potentially visible as a flicker.

**Current nova-script behavior:** `clear()` → all 64 OFF messages → render → 64 new messages. The hardware transitions through OFF briefly.

**Fix: Render-first, clear-after.** Or better: compute the new state, diff against previous, send only changes. The user should never see an OFF flash between renders.

**This applies to ALL modes** — performance, instrument, clip launcher, sequencer, mixer. Every mode calls `clear()` first, causing a single-frame black flash.

### Insight #3: The Launchpad Does NOT Keep Up With Every Tick

In the engine's current event loop:
```python
event_data = await asyncio.wait_for(queue.get(), timeout=0.1)
# ...
self._tick()
```

The `_tick()` method runs at up to 10Hz (every 100ms) when idle, plus on every MIDI event. But mode.render() is called inside tick, potentially at every cycle. This sends 64 MIDI messages every 100ms even when nothing changes — 10 fps of full-grid redraws.

**Impact:** 640 LED messages/second at idle. While the MK1 can handle this, it's wasteful and may cause subtle shimmering.

**Fix: Only render on state changes.** Already partially implemented in instrument mode. Should be applied to ALL modes.

### Insight #4: The "send_message" Silently Drops Problem

Our `send_message()` silently returns when the device is not connected (we fixed this in an earlier commit). But there's a deeper issue: **messages sent before connection are lost forever.** There is no queue, no retry, no "apply latest state on reconnect."

When nova-script starts without a Launchpad connected (or before the virtualizer creates ports):
1. Modes render and call send_message → silently dropped
2. Launchpad connects later → `on_connect()` is called → `clear_grid()` runs
3. But the mode's logical grid state was "rendered" into the void — those LED commands were never sent
4. The mode is sitting in a state where it THINKS the hardware shows something, but it doesn't

**Fix: On connect, call `mode.enter()` to force a full re-render.** We already do this partially via `_on_device_connect` calling `mode.enter()`. But we should verify this covers all cases.

### Insight #5: Right Column is Note On, Not CC

A common misconception: the right column buttons are often assumed to be CC messages (like the top row). They are NOT — they're Note On messages on specific notes (8, 24, 40, 56, 72, 88, 104, 120). This matters because:

- You can illuminate right column buttons with `[0x90, note, velocity]` — same as grid pads
- The `parse_midi()` in our MK1 controller correctly handles this
- But if you send CC 0x68+n to the right column, nothing happens
- Our virtualizer must match this exactly for valid simulation

### Insight #6: The Startup Screen Behavior

The Launchpad Mini MK1, when first powered on or reset via host connection, briefly shows a "Novation" logo pattern (all pads lit in sequence). This is firmware behavior and cannot be suppressed.

After the logo, the MK1 enters its last-used layout mode. If the host hasn't sent `[0xB0, 0x00, 0x00]` yet, the pads will show whatever internal state they had. This is why our startup wave sometimes shows a "red block" before the wave animation begins — the MK1 is in an indeterminate state until the reset command is sent.

---

## 4. Practical Recommendations for Nova-Script

### Immediate Fixes

1. **Don't call `clear()` before render in modes.** Compute the new state, diff against previous, send only changes. This eliminates the single-frame black flash and reduces MIDI traffic 6-12x.

2. **Add a `force_render()` method to controllers** that renders all cells regardless of dirty state. Use this on mode entry and device connect only.

3. **Throttle re-renders in all modes** — only redraw on actual state changes. The instrument mode already does this correctly. Apply the pattern everywhere.

### Medium-Term Improvements

4. **Implement a "render queue"** — batch LED updates and send them as a group after a small delay (1-2ms). This ensures visual consistency by grouping changes that belong to the same logical frame.

5. **Add "on connect" state restoration** — when a device reconnects, replay the last known full state (or call `mode.enter()` to force re-render).

### Future Considerations

6. **For MK3 support (future):** Use double-buffering. Write to the inactive buffer, then swap. No flicker, atomic updates, cleaner visuals.

7. **Color space awareness** — The MK1's bicolor LEDs have a fundamentally different color space than RGB displays. Our virtualizer approximates with sRGB, but the perceptual difference is significant. A hardware-calibrated LUT would help.

8. **USB bandwidth monitoring** — Track how many MIDI messages/second we're sending. Alert if we exceed ~800 msg/s (the practical limit for the MK1's USB 1.1 bus).

---

## 5. References

- Novation Launchpad Mini Programmer's Reference Manual (PDF, Focusrite/Novation)
- FMMT666/launchpad.py — Most comprehensive open-source Launchpad library
- MIDI 1.0 Specification (MMA)
- USB MIDI 1.0 Class Specification
- CoreMIDI documentation (Apple) — for macOS virtual port behavior

---

## 6. Summary of Key Findings

| Finding | Severity | Fix |
|---------|----------|-----|
| `clear()` + render = 64 useless messages per frame | High | Diff-based rendering |
| No double-buffer = brief OFF flash between renders | High | Render-first, then diff |
| Screensaver lacked clear() → ghost composites | Fixed | Added `grid.clear()` |
| Startup wave runs before mode setup (was "red block") | Fixed | Wave runs then mode renders |
| Colors approximated — need hardware calibration | Medium | LUT-based color mapping |
| Launchkey connection crashes on `_reported_secondary` | Fixed | Added to dataclass |
| Modes re-render on every tick even when idle | Medium | State-change-only renders |
| "Cannot send" debug spam before port connects | Fixed | Silent drop |
| Virtualizer needs color alignment with hardware | Medium | Updated RGB values |
