# Nova-Script Requirements

## Functional Requirements

### FR1 — Device Discovery & Connection
- FR1.1: Auto-detect connected Novation devices by MIDI port name
- FR1.2: Support hot-plug / hot-unplug of devices at runtime
- FR1.3: Distinguish between input and output ports per device
- FR1.4: Handle devices that present multiple MIDI port pairs (DAW port vs. standard port)

### FR2 — LED Control
- FR2.1: Set individual pad LED color on any supported device
- FR2.2: Set entire grid to a single color (clear/reset)
- FR2.3: Flash/pulse LEDs (where hardware supports it)
- FR2.4: Logical color model that maps to best available hardware color
- FR2.5: Batch LED updates for flicker-free grid refresh

### FR3 — Input Handling
- FR3.1: Detect button press and release events
- FR3.2: Normalize grid coordinates across devices (0,0 = bottom-left)
- FR3.3: Detect velocity/aftertouch on pads (Launchkey)
- FR3.4: Detect knob, fader, and transport button events (Launchkey)
- FR3.5: Distinguish short press vs. long press (hold threshold)
- FR3.6: Track idle time since last physical input

### FR4 — Mode System
- FR4.1: Support multiple mutually exclusive modes
- FR4.2: Mode switching via dedicated hardware buttons
- FR4.3: Mode switching via OSC command
- FR4.4: Each mode owns the grid — controls all LED output
- FR4.5: Mode lifecycle: enter → handle events → tick (optional) → exit

### FR5 — Step Sequencer Mode
- FR5.1: N rows × M columns grid representation
- FR5.2: Each step toggles between on (selected note/velocity) and off
- FR5.3: Scrolling/region support for sequences longer than grid width
- FR5.4: Pattern chaining (sequence patterns A → B → C)
- FR5.5: Adjustable step resolution (1/4, 1/8, 1/16, 1/32, triplets)
- FR5.6: Output sequenced notes as MIDI to configured output port

### FR6 — Mixer Mode
- FR6.1: Display track volumes as vertical LED columns
- FR6.2: Adjust track volume by pressing pad position in column
- FR6.3: Track mute/solo indicators
- FR6.4: Send level indicators
- FR6.5: Pan position indicators
- FR6.6: Send volume changes as OSC to Reaper
- FR6.7: Scrollable track banks (more tracks than grid columns)

### FR7 — Effects Mode
- FR7.1: Navigate FX chain per track
- FR7.2: Display and adjust FX parameters
- FR7.3: Bypass/engage individual effects
- FR7.4: Send parameter changes as OSC to Reaper

### FR8 — Performance Mode
- FR8.1: Grid-based clip/scene launching (Ableton-style session view)
- FR8.2: Clip slot states: empty, loaded, playing, recording
- FR8.3: Scene launch (entire row at once)
- FR8.4: Clip stop buttons

### FR9 — Menu Mode
- FR9.1: Display available modes as labeled grid buttons
- FR9.2: Navigate sub-menus
- FR9.3: Visual feedback showing current selection

### FR10 — Message Display Mode
- FR10.1: Receive OSC message with text to display
- FR10.2: Render text as scrolling LED animation on the grid
- FR10.3: Auto-activate when device is idle (configurable timeout, default 2s)
- FR10.4: Immediately dismiss on any button press
- FR10.5: Queue multiple messages, display sequentially
- FR10.6: Support for configurable scroll speed

### FR11 — OSC Communication
- FR11.1: OSC server listening on configurable port (default: 9000)
- FR11.2: OSC client sending to Reaper on configurable port (default: 8000)
- FR11.3: Well-defined OSC address namespace for all parameters
- FR11.4: Bidirectional: send commands, receive feedback

### FR12 — MIDI Output
- FR12.1: Route MIDI notes, CC, PC to configurable output ports
- FR12.2: MIDI clock output (when acting as clock master)
- FR12.3: Configurable routing table

### FR13 — Configuration
- FR13.1: YAML-based configuration file
- FR13.2: Device-specific settings (colors, sensitivity)
- FR13.3: Mode mappings (which button triggers which mode)
- FR13.4: MIDI routing table
- FR13.5: OSC port settings
- FR13.6: Multiple configuration profiles

### FR14 — TUI Companion
- FR14.1: Live grid mirror showing Launchpad LED state with colors
- FR14.2: Active mode indicator
- FR14.3: Scrollable event/activity log
- FR14.4: Configuration editing
- FR14.5: Device connection status

### FR15 — Launchkey 49 MK2 Support
- FR15.1: Map 16 velocity-sensitive pads with LED feedback
- FR15.2: Map 8 knobs contextually to active mode
- FR15.3: Map 8 faders contextually to active mode
- FR15.4: Map transport buttons (play, stop, record, loop)
- FR15.5: Pads can mirror Launchpad grid quadrant or serve independent function

## Non-Functional Requirements

### NFR1 — Performance
- NFR1.1: LED grid updates within 10ms of state change
- NFR1.2: MIDI input latency < 5ms
- NFR1.3: OSC round-trip < 20ms

### NFR2 — Reliability
- NFR2.1: Graceful handling of device disconnect/reconnect
- NFR2.2: No crashes on malformed OSC/MIDI input
- NFR2.3: Recoverable state after errors

### NFR3 — Extensibility
- NFR3.1: Adding a new device model requires only a new controller subclass
- NFR3.2: Adding a new mode requires only a new Mode subclass
- NFR3.3: OSC namespace documented and versioned

### NFR4 — Usability
- NFR4.1: Visual UI for configuration (no editing YAML by hand required)
- NFR4.2: Clear LED feedback for all interactions
- NFR4.3: Help/info mode showing control layout
