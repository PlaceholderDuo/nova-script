# Reference Projects & Research

Comparative analysis of existing projects doing similar work. What to learn, steal, and avoid.

---

## 1. Launchpad Python Libraries

### FMMT666/launchpad.py ★382
**https://github.com/FMMT666/launchpad.py** — The definitive Python Launchpad library. Python 2/3, PyGame MIDI.

- Most comprehensive device support: LP Mk1, Mk2, Pro, Pro Mk3, Mini Mk3, LPX, Launch Control/XL, LaunchKey Mini, Dicer, Midi Fighter
- No formal base class hierarchy — per-device monolith classes
- Poll-based only, no event system. Buffer can overflow from pot/slider events
- Mk1 compatibility hacks bloat RGB device classes
- `Close()` is broken on PyGame — crashes with "Bad Pointer" on exit
- Character rendering has bugs (!, 0, N broken)
- **Take:** Rapid bulk LED update pattern, color palette approach, font system concept, multi-device detection
- **Avoid:** PyGame dependency (broken on Apple Silicon), poll-only input, MK1 cruft, broken Close()

### dhilowitz/launchpad_rtmidi.py ★10
**https://github.com/dhilowitz/launchpad_rtmidi.py** — Fork of above using python-rtmidi instead of PyGame. Python 2 only. Mk1, Mk2, Pro, Control XL, LaunchKey Mini.

- **Take:** The pattern of wrapping python-rtmidi — confirmed as the right choice
- **Avoid:** Python 2 lock-in, stale fork (no Mk3/X/ProMk3 support)

### beryxz/launchpad-mini (June 2026)
**https://github.com/beryxz/launchpad-mini** — Modern, clean Python 3.12 package. MK1 only. python-rtmidi + uv.

- Implements **full classic Launchpad MIDI protocol** including features most omit: velocity copy/clear flags, double buffering, hardware flashing, duty cycle control, grid mapping mode selection
- **Canvas/Pixel API** with shape drawing (circle, rect, line, point) + Renderer
- `poll()` returns structured event with `.pressed`, `.x`, `.y`
- Text scroller built in
- **Take:** Canvas/Pixel API is the right grid abstraction. UV packaging. Context manager pattern.
- **Avoid:** MK1 only, poll-based, single-device, brand new

### rotanpuolikas/launchpad-mini-gif (March 2026)
**https://github.com/rotanpuolikas/launchpad-mini-gif** — Renders GIFs/PNGs on Launchpad Mini MK1.

- Pillow decode → resize 8×8 → quantize to 4-level amber
- **Take:** Image-to-grid mapping approach for future graphics features

---

## 2. Launchpad Step Sequencers

### edwardgallyot/LaunchpadSequencer.py ★4 (2021)
**https://github.com/edwardgallyot/LaunchpadSequencer.py** — Single-file step sequencer. python-rtmidi.

- 8×8 grid as pattern editor (rows=tracks, cols=steps). Right column = transport.
- Uses `time.sleep()` — crude timing
- **Take:** Direct grid-to-notes mapping pattern
- **Avoid:** `time.sleep()`, no clock sync, no persistence

### danpprince/lpstep ★1 (2015-2016, 55 commits)
**https://github.com/danpprince/lpstep** — MVC-pattern step sequencer. PyGame MIDI.

- Clean separation: sequencermodel.py, lpview.py, lpstep.py (controller), midiinputcontroller.py
- External sequencing, note state tracking, MIDI input for external keyboards
- Emphasizes flexibility + improvisation
- **Take:** MVC architecture pattern, note state tracking, model/view separation
- **Avoid:** PyGame MIDI, abandoned

---

## 3. Ableton Live Remote Scripts

### hdavid/Launchpad95 ★400 (88 forks) — CRITICAL REFERENCE
**https://github.com/hdavid/Launchpad95** — Modified Ableton Live control surface scripts. Python, runs inside Ableton's interpreter.

**Modes:** Session (clip launch), Instrument (Push-style note grid + scale), Step Sequencer, Device Controller, Mixer.

**Architecture:** Component-based (Ableton `_Framework` API). Separate components: StepSequencer, InstrumentController, NoteEditor, DeviceController, SpecialSession, LoopSelector, Scale, NoteRepeat. Skin files for MK1/MK2 color mapping.

**What to steal:**
- Mode-switching architecture (top buttons switch modes)
- Scale quantization for note grid
- Step sequencer UI: left column = step pages, colored indicators for velocity
- Device parameter mapping with 8-knob style mapping
- Overall UX design — this is the gold standard

**Limitations:** Tied to Ableton's Remote Script API (not standalone). MK1/MK2 only.

---

## 4. OSC/MIDI Bridges

### velolala/touchosc2midi ★128 (25 forks)
**https://github.com/velolala/touchosc2midi** — TouchOSC Bridge clone. Python, mido + python-rtmidi + pyliblo + zeroconf.

- Bidirectional: OSC→MIDI and MIDI→OSC translation
- Virtual + hardware MIDI ports
- Zeroconf auto-discovery
- **Take:** Bidirectional translation pattern, mido as MIDI abstraction layer

### codex-live-bridge ★25 (Feb 2026)
**https://github.com/sunflower-of-parchman/codex-live-bridge** — OSC/UDP bridge for Ableton. Python CLI + Max for Live.

- Command+ACK on separate UDP ports (clean separation)
- Token-based write security, Request ID correlation
- LiveAPI path notation, observer system
- **Take:** Separate command/feedback channels, request ID correlation pattern

### attwad/python-osc ★580 — THE OSC LIBRARY
**https://github.com/attwad/python-osc** — Pure Python, zero deps. OSC 1.0/1.1.

- UDP + TCP, blocking/threading/forking/asyncio variants
- Bundle support, full type support (int, float, string, blob, MIDI, timestamps)
- **Take:** This IS the OSC library we should use (and already do). Dispatcher pattern, asyncio support.

---

## 5. Hardware Bridge Projects

### APC-Eos-Bridge (April 2026)
**https://github.com/sandalphonqlab/APC-Eos-Bridge** — Akai APC Mini MK2 → ETC Eos lighting via OSC + MIDI.

- MIDI input → Python → OSC commands to Eos
- RGB LED feedback via MIDI out. Auto-reconnect. Web config editor.
- **Take:** Auto-reconnect pattern, MIDI→OSC with LED feedback, headless deployment

### sandraschi/reaper-mcp (2025-2026, 39 commits)
**https://github.com/sandraschi/reaper-mcp** — MCP server for AI-controlled Reaper. Python 3.12+, python-osc.

- Reaper OSC setup: Reaper listens on 8000, remote on 8001. "Send all feedback" enabled.
- Portmanteau tools: transport, tracks, project, system, reascript, orchestrator
- **Take:** Reaper OSC address space usage, setup details

---

## 6. Hardware Reference

| Model | VID:PID | Grid | Colors | Notes |
|-------|---------|------|--------|-------|
| LP MK1/Mini MK1 | 1235:0036 | 8×8 + 8 top + 8 right | 2-bit red+green = ~9 colors | USB MIDI class-compliant |
| LP MK2 | — | 8×8 + 8 top + 8 right | 6-bit RGB + 128-palette | Higher power draw |
| LP Pro | — | 8×8 + 8 top + 8 right + 8 left | 6-bit RGB + 128-palette | Pressure-sensitive |
| LP X | — | 8×8 + more | 6-bit RGB | Pressure events |
| LP Mini MK3 | — | 8×8 + top | 6-bit RGB | — |
| LP Pro MK3 | — | 8×8 + top + right + left | 6-bit RGB | Must disable Transmit Clock |
| Launch Control XL | — | 3×8 LED + 24 pots + 8 faders | Red/green | 8 user + 8 factory templates |
| Launchkey 49 MK2 | — | 16 pads (2×8) + 8 knobs + 8 faders | RGB palette via velocity | InControl port required |

---

## 7. Key Takeaways

### Confirmed correct decisions:
- ✅ python-rtmidi (not PyGame) — confirmed by dhilowitz fork
- ✅ Textual for TUI — no better alternative found
- ✅ python-osc — the standard, zero deps
- ✅ YAML config — simple, readable
- ✅ Our layered architecture (controllers → modes → protocol bridge)
- ✅ LogicalColor abstraction — maps to both MK1 2-bit and MK3 palette
- ✅ Long-press detection in base Mode class
- ✅ Canvas/Pixel API concept (our grid abstraction is this)

### Gaps we're filling (unique value):
1. **No LED grid UI widget framework exists.** Our Mode system + grid abstraction is the closest thing.
2. **No standalone session view / clip launcher.** Our Performance mode fills this gap.
3. **No multi-device Novation abstraction framework.** Our NovationController base + DeviceCapabilities does this.
4. **No Launchpad→Reaper OSC bridge.** Our OscBridge is exactly this.
5. **No Python live-performance MIDI router.** Opportunity for future.

### Ideas for future:
- **Canvas API:** Port beryxz's Canvas shape drawing (circles, lines, rects) to our LogicalGrid
- **Image rendering:** GIF/PNG → 8×8 grid mapping for visual effects
- **MVC pattern:** Apply lpstep's model/view separation to our modes
- **Command/ACK channels:** Use separate OSC ports for commands vs feedback (codex-live-bridge pattern)
- **MIDI learn:** KnobLooper's pattern for mapping hardware controls to parameters
- **Web config editor:** APC-Eos-Bridge's approach for remote configuration
- **Dual-buffer LED rendering:** beryxz's discovery that MK1 supports double buffering for flicker-free updates
- **Hardware flashing/duty cycle:** MK1 supports these natively — we should expose them

### Avoid (confirmed):
- ❌ PyGame MIDI — dead on Apple Silicon
- ❌ Poll-only input — we have event system ✓
- ❌ Hardcoded per-device without abstraction — we have NovationController base ✓
- ❌ `time.sleep()` for timing — we use asyncio + delta time ✓
- ❌ MK1 compatibility mode hacks — we use LogicalColor mapping ✓
