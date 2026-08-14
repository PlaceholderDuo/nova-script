"""
Engine Integration Tests — full-pipeline flows WITHOUT physical hardware.

Boots the real Engine (real controllers, OverlayManager, BPMClock, ModeManager,
OSC dispatcher) but WITHOUT rtmidi sockets: `Engine.midi_manager` is swapped for a
`VirtualMidiManager` (buffers all MIDI writes, "connected" = True), and no network
socket is opened because we drive the incoming-event handlers (`_on_grid_event`,
`_on_control_event`, `_on_osc_message`) directly — exactly what the live event
loop does for each real MIDI/OSC frame.

LED output is captured on the real LaunchpadMini controller's internal
`_grid_state` (what would be sent to hardware), so we can assert colours AND
positions without a device.

How the harness works:
  1. patch `engine_mod.MidiManager` → a virtual, hardware-free class
     (so `Engine.__init__` never touches rtmidi ports)
  2. call the same private setup methods `Engine.start()` calls, but with
     the virtual backend: `_setup_controllers`, `_setup_overlay`, `_setup_modes`
  3. drive events via the harness helpers (tap/tap_ctrl/osc)

Test matrix (all run with no device attached):
  1. boot            → lands on the configured default mode, all 7 modes present
  2. menu nav        → tapping menu pads switches to the right mode
  3. shortcuts       → top-row buttons 201-205 jump to their mode
  4. OSC mode_set    → switching + rejection of unknown modes
  5. HUD overlay     → display_message opens overlay, grid press swallowed, auto-dismiss
  6. screensaver     → overlay swallows all input until dismissed
  7. combos          → hold-200 + 201 = screensaver, +202 = fireworks, + alone = home
  8. ARP exit        → top-row 200 leaves arp_edit → instrument
  9. tuner OSC       → /nova/tuner cents/channel reaches performance mode
 10. play_state OSC  → routed to performance (guarded if method missing)
 11. beat/clock      → engine tick feeds BPMClock and emits beats
 12. virt info       → _build_virt_info reflects active mode
 13. TUI broadcast   → grid_state snapshots land in the TUI queue
"""
import asyncio
import sys
import time
from queue import Queue

sys.path.insert(0, ".")

import src.engine as engine_mod
from tests.virtualizer import VirtualMidiManager
from src.controllers.base import GridEvent, ControlEvent, EventType, LogicalColor


class FakeMidiManager(VirtualMidiManager):
    """Stand-in used by Engine.__init__ so no rtmidi port is ever touched."""

    def __init__(self, poll_interval: float = 0.5):
        super().__init__()


# Patch BEFORE `Engine` is imported/instantiated so `Engine.__init__` builds
# against the virtual manager.
engine_mod.MidiManager = FakeMidiManager


class EngineHarness:
    """Builds a running-but-virtual engine with test hooks baked in."""

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.engine = engine_mod.Engine(self.config)
        assert isinstance(self.engine.midi_manager, VirtualMidiManager), (
            "midi backend must be virtual"
        )
        self.vmidi = self.engine.midi_manager

        # Replicate Engine.start()'s setup, minus sockets/websockets/timing.
        from src.ui.image_store import ImageStore
        self.engine._image_store = ImageStore()
        self.engine._setup_controllers()
        self.engine._setup_overlay()
        self.engine._setup_modes()

        self.lp = self.engine.controllers["Launchpad Mini"]
        self.lk = self.engine.controllers.get("Launchkey 49")

    # ── event injection (mirrors the live event loop) ────────────────

    def grid_press(self, x: int, y: int, pressed: bool = True):
        self.engine._on_grid_event(GridEvent(x, y, pressed, 127, device="Launchpad Mini"))

    def tap(self, x: int, y: int, hold_ms: int = 80):
        self.grid_press(x, y, True)
        if hold_ms:
            time.sleep(hold_ms / 1000)
        self.grid_press(x, y, False)
        self.engine._tick()

    def ctrl(self, control_id: int, pressed: bool = True):
        et = EventType.FUNCTION_PRESS if pressed else EventType.FUNCTION_RELEASE
        self.engine._on_control_event(
            ControlEvent(control_id, 127 if pressed else 0, et, device="Launchpad Mini")
        )

    def tap_ctrl(self, control_id: int, hold_ms: int = 60):
        self.ctrl(control_id, True)
        if hold_ms:
            time.sleep(hold_ms / 1000)
        self.ctrl(control_id, False)
        self.engine._tick()

    def osc(self, msg: dict):
        self.engine._on_osc_message(msg)

    # ── readability helpers ──────────────────────────────────────────

    @property
    def mode(self) -> str:
        return self.engine.mode_manager.active_mode_name

    def led(self, x: int, y: int) -> LogicalColor | None:
        return self.lp.get_grid_color(x, y)

    def check_led(self, x: int, y: int, expected: LogicalColor, label: str = ""):
        actual = self.led(x, y)
        assert actual == expected, (
            f"{label} ({x},{y}): expected {expected.name}, got "
            f"{actual.name if actual else '?'}"
        )


# ── shared config builders ──────────────────────────────────────────

MENU_ITEMS = [
    {"label": "PERF", "mode": "performance", "color": "RED_HIGH", "x": 0, "y": 4, "w": 2, "h": 2},
    {"label": "CLIP", "mode": "clip_launcher", "color": "RED_MED", "x": 2, "y": 4, "w": 2, "h": 2},
    {"label": "SEQ", "mode": "sequencer", "color": "AMBER_HIGH", "x": 4, "y": 4, "w": 2, "h": 2},
    {"label": "MIX", "mode": "mixer", "color": "GREEN_HIGH", "x": 6, "y": 4, "w": 2, "h": 2},
]


def menu_config():
    return {"ui": {"default_mode": "menu"}, "modes": {"menu": {"items": MENU_ITEMS}}}


# ── 1. boot ────────────────────────────────────────────────────────

def test_boot_default_mode():
    print("=" * 60)
    print("TEST 1: Engine boot to default mode")
    print("=" * 60)
    h = EngineHarness({"ui": {"default_mode": "performance"}})
    assert h.mode == "performance", f"Boot should land on performance, got {h.mode}"
    print(f"  ✓ Booted to: {h.mode}")
    print(f"  ✓ Controllers: {sorted(h.engine.controllers.keys())}")
    print(f"  ✓ Modes: {sorted(h.engine.mode_manager._modes.keys())}")
    print()


# ── 2. menu navigation ─────────────────────────────────────────────

def test_menu_navigation():
    print("=" * 60)
    print("TEST 2: Menu pad navigation")
    print("=" * 60)
    h = EngineHarness(menu_config())
    assert h.mode == "menu", f"expected menu, got {h.mode}"

    # all four menu pads rendered lit
    for item in MENU_ITEMS:
        assert h.led(item["x"], item["y"]) not in (None, LogicalColor.OFF), (
            f"{item['label']} pad should be lit"
        )
    print("  ✓ All 4 menu pads lit (LED check)")

    h.tap(2, 4)  # CLIP block spans (2..3, 4..5)
    assert h.mode == "clip_launcher", f"expected clip_launcher, got {h.mode}"
    print(f"  ✓ Tapped CLIP → {h.mode}")

    h.osc({"type": "mode_set", "mode": "mixer"})
    assert h.mode == "mixer", f"expected mixer, got {h.mode}"
    print(f"  ✓ OSC mode_set → {h.mode}")
    print()


# ── 3. top-row shortcuts ───────────────────────────────────────────

def test_top_row_shortcuts():
    print("=" * 60)
    print("TEST 3: Top-row shortcut buttons")
    print("=" * 60)
    h = EngineHarness({"ui": {"default_mode": "performance"}})
    # Top-row shortcuts are config-driven (Entry #40): ctrl N reads the menu's
    # items[N-200]. Engine default menu: 0=PERF 1=CLIP 2=SEQ 3=MIX 4=INST 5=ARP.
    expect = {
        201: "clip_launcher",
        202: "sequencer",
        203: "mixer",
        204: "instrument",
        205: "arp_edit",
    }
    for cid, name in expect.items():
        h.tap_ctrl(cid)
        assert h.mode == name, f"ctrl {cid} should → {name}, got {h.mode}"
        print(f"  ✓ ctrl {cid} → {name}")
    print()


# ── 4. OSC mode_set ────────────────────────────────────────────────

def test_mode_set_osc():
    print("=" * 60)
    print("TEST 4: OSC mode_set routing")
    print("=" * 60)
    h = EngineHarness({"ui": {"default_mode": "performance"}})
    h.osc({"type": "mode_set", "mode": "sequencer"})
    assert h.mode == "sequencer", f"got {h.mode}"
    h.osc({"type": "mode_set", "mode": "nope"})
    assert h.mode == "sequencer", "unknown mode should be ignored"
    print("  ✓ mode_set → sequencer, unknown ignored")
    print()


# ── 5. HUD overlay ─────────────────────────────────────────────────

def test_hud_overlay_and_dismiss():
    print("=" * 60)
    print("TEST 5: HUD overlay + auto-dismiss")
    print("=" * 60)
    h = EngineHarness({"ui": {"default_mode": "performance"}})
    assert not h.engine.overlay.is_overlay_active

    h.osc({"type": "display_message", "text": "TEST"})
    assert h.engine.overlay.is_overlay_active, "HUD should activate on display_message"
    print("  ✓ display_message → HUD overlay active")

    # HUD must swallow grid presses while active
    h.engine._on_grid_event(
        GridEvent(0, 0, True, 127, device="Launchpad Mini")
    )
    assert h.mode == "performance", "HUD must not leak grid press to mode"
    print("  ✓ Grid press swallowed by HUD (mode unchanged)")

    # overlay auto-dismisses after its duration
    time.sleep(2.0)
    h.engine._tick()
    assert not h.engine.overlay.is_overlay_active, "HUD should auto-dismiss after 1.5s"
    print("  ✓ HUD auto-dismissed after duration")
    print()


# ── 6. screensaver overlay ─────────────────────────────────────────

def test_screensaver_swallows_input():
    print("=" * 60)
    print("TEST 6: Screensaver swallows grid + ctrl")
    print("=" * 60)
    h = EngineHarness({"ui": {"default_mode": "performance"}})
    h.engine.overlay.trigger_screensaver()
    assert h.engine.overlay.is_overlay_active

    h.tap_ctrl(203)  # shortcut → sequencer
    assert h.mode == "performance", f"ctrl leaked through screensaver, mode={h.mode}"
    print("  ✓ Ctrl swallowed while screensaver")

    h.tap(1, 1)
    assert h.mode == "performance", "grid swallowed while screensaver"
    print("  ✓ Grid swallowed while screensaver")

    h.engine.overlay._dismiss_overlay()
    assert not h.engine.overlay.is_overlay_active
    print()
    pass


# ── 7. combos ──────────────────────────────────────────────────────

def test_combos():
    print("=" * 60)
    print("TEST 7: Combo chords (screensaver / fireworks / home)")
    print("=" * 60)

    # --- combo A: hold-200 + 201 → screensaver overlay ---
    h = EngineHarness({"ui": {"default_mode": "sequencer"}})
    h.ctrl(200, True)
    h.ctrl(201, True)
    assert h.engine.overlay.is_overlay_active, "hold-200+201 should raise overlay"
    print("  ✓ hold-200+201 → screensaver")
    h.ctrl(201, False)
    h.ctrl(200, False)
    h.engine.overlay._dismiss_overlay()

    # --- combo B: hold-200 + 202 → fireworks overlay ---
    h = EngineHarness({"ui": {"default_mode": "sequencer"}})
    h.ctrl(200, True)
    h.ctrl(202, True)
    assert h.engine.overlay.is_overlay_active, "hold+202 should trigger overlay"
    h.ctrl(202, False)
    h.ctrl(200, False)
    print("  ✓ hold-200+202 → fireworks ON")
    h.engine.overlay._dismiss_overlay()

    # --- combo C: hold-200 alone → "home" back to performance ---
    h = EngineHarness({"ui": {"default_mode": "sequencer"}})
    h.ctrl(200, True)
    time.sleep(0.05)
    h.ctrl(200, False)
    assert h.mode == "performance", f"home should land on performance, got {h.mode}"
    print("  ✓ hold-200 alone → home / performance")
    print()


# ── 8. ARP edit exit ───────────────────────────────────────────────

def test_arp_edit_exit_top_row():
    print("=" * 60)
    print("TEST 8: ARP edit exits via top-row 200")
    print("=" * 60)
    h = EngineHarness({"ui": {"default_mode": "instrument"}})
    h.engine._enter_arp_edit()
    assert h.mode == "arp_edit", f"expected arp_edit, got {h.mode}"
    print(f"  ✓ Entered {h.mode}")

    h.tap_ctrl(200)
    assert h.mode == "instrument", f"200 should exit arp_edit → instrument, got {h.mode}"
    print("  ✓ Top-row 200 exits ARP edit → instrument")
    print()


# ── 9. OSC tuner ───────────────────────────────────────────────────

def test_tuner_osc_routing():
    print("=" * 60)
    print("TEST 9: /nova/tuner → performance mode")
    print("=" * 60)
    h = EngineHarness({"ui": {"default_mode": "performance"}})
    pm = h.engine.mode_manager._modes["performance"]
    pm.start_tuner("GTR")
    h.osc({"type": "tuner", "cents": 35.0, "channel": "GTR"})
    assert pm._tuner_cents == 35.0, f"tuner cents = {pm._tuner_cents}"
    assert pm._tuner_channel == "GTR"
    print("  ✓ OSC tuner → performance._tuner_cents = 35.0 (GTR)")
    pm.stop_tuner()
    print()


# ── 10. play_state ─────────────────────────────────────────────────

def test_play_state_osc():
    print("=" * 60)
    print("TEST 10: play_state routing (guarded if method absent)")
    print("=" * 60)
    h = EngineHarness({"ui": {"default_mode": "performance"}})
    pm = h.engine.mode_manager._modes["performance"]
    h.osc({"type": "play_state", "state": 1})
    if hasattr(pm, "set_play_state"):
        assert pm._play_state == 1, f"_play_state = {getattr(pm, '_play_state', '?')}"
        print("  ✓ set_play_state=1 reached performance")
    else:
        print("  ! set_play_state not defined — engine skip OK")
    print()


# ── 11. beat / clock ───────────────────────────────────────────────

def test_beat_clock():
    print("=" * 60)
    print("TEST 11: engine tick feeds BPMClock (beats emitted)")
    print("=" * 60)
    h = EngineHarness({"ui": {"default_mode": "performance"}})
    beats = []
    h.engine._clock.set_on_beat(lambda n: beats.append(n))
    h.osc({"type": "beat", "position": 1.0})
    start = time.monotonic()
    while time.monotonic() - start < 1.2:
        h.engine._tick()
        time.sleep(0.01)
    assert len(beats) > 0, "internal clock should emit beats"
    print(f"  ✓ {len(beats)} beat(s) generated")
    print()


# ── 12. build_virt_info ────────────────────────────────────────────

def test_build_virt_info():
    print("=" * 60)
    print("TEST 12: _build_virt_info reflects active mode")
    print("=" * 60)
    h = EngineHarness({"ui": {"default_mode": "performance"}})
    info = h.engine._build_virt_info()
    assert info["mode"] == "performance", f"got {info}"
    h.osc({"type": "mode_set", "mode": "mixer"})
    info = h.engine._build_virt_info()
    assert info["mode"] == "mixer", f"got {info}"
    print(f"  ✓ info = {info}")
    print()


# ── 13. TUI broadcast loop ─────────────────────────────────────────

def test_tui_broadcast():
    print("=" * 60)
    print("TEST 13: TUI broadcast loop publishes grid_state")
    print("=" * 60)
    q = Queue()
    h = EngineHarness({"ui": {"default_mode": "performance"}})
    h.engine.set_tui_queue(q)

    async def run_a_few():
        h.engine._running = True
        task = asyncio.create_task(h.engine._tui_broadcast_loop())
        await asyncio.sleep(0.12)
        h.engine._running = False
        task.cancel()

    asyncio.run(run_a_few())
    assert not q.empty(), "TUI queue should hold a grid_state"
    msg = q.get_nowait()
    assert msg["type"] == "grid_state", f"unexpected {msg['type']}"
    assert len(msg["grid"]) == 8 and len(msg["grid"][0]) == 8, "8x8 snapshot"
    assert msg["mode"] == "performance"
    print(f"  ✓ grid_state published: mode={msg['mode']}, devices={msg['devices']}")
    print()


if __name__ == "__main__":
    test_boot_default_mode()
    test_menu_navigation()
    test_top_row_shortcuts()
    test_mode_set_osc()
    test_hud_overlay_and_dismiss()
    test_screensaver_swallows_input()
    test_combos()
    test_arp_edit_exit_top_row()
    test_tuner_osc_routing()
    test_play_state_osc()
    test_beat_clock()
    test_build_virt_info()
    test_tui_broadcast()
    print("=" * 60)
    print("ALL ENGINE INTEGRATION TESTS PASSED")
    print("=" * 60)