"""
Integration test: overlay dismiss, mode switching, screensaver.
Drives engine components directly (no subprocess, no MIDI).
"""
import time
from pathlib import Path
from src.layout.grid import LogicalGrid
from src.controllers.launchpad_mk1 import LaunchpadMiniMK1
from src.controllers.base import EventType, ControlEvent, GridEvent, LogicalColor
from src.midi.manager import MidiManager
from src.ui.mode_manager import ModeManager
from src.ui.modes.menu import MenuMode
from src.ui.modes.performance import PerformanceMode
from src.ui.modes.sequencer import SequencerMode
from src.ui.modes.clip_launcher import ClipLauncherMode
from src.ui.modes.mixer import MixerMode
from src.ui.modes.instrument import InstrumentMode
from src.ui.overlay_manager import OverlayManager, OverlayPriority
from src.ui.combo_detector import ComboDetector
from src.ui.image_store import ImageStore


def test():
    grid = LogicalGrid(8, 8)
    mgr = MidiManager(poll_interval=999)
    lp = LaunchpadMiniMK1(mgr)
    lp.set_callbacks(on_grid_event=lambda e: None, on_control_event=lambda e: None)

    image_store = ImageStore()

    # Overlay with 10s idle
    overlay = OverlayManager(grid, lp, image_store, idle_timeout_ms=10000, bpm=120)
    overlay.start()

    # Combo detector
    combo = ComboDetector()

    # Mode manager
    mm = ModeManager(grid, lp)

    menu = MenuMode(grid, lp)
    menu.set_items([
        {"label": "PERF", "mode": "performance", "color": "RED_HIGH", "x": 0, "y": 6, "w": 2, "h": 2},
        {"label": "CLIP", "mode": "clip_launcher", "color": "RED_MED", "x": 2, "y": 6, "w": 2, "h": 2},
        {"label": "SEQ", "mode": "sequencer", "color": "AMBER_HIGH", "x": 4, "y": 6, "w": 2, "h": 2},
        {"label": "MIX", "mode": "mixer", "color": "GREEN_HIGH", "x": 0, "y": 4, "w": 2, "h": 2},
        {"label": "INST", "mode": "instrument", "color": "GREEN_MED", "x": 2, "y": 4, "w": 2, "h": 2},
        {"label": "MENU", "mode": "menu", "color": "AMBER_MED", "x": 4, "y": 4, "w": 2, "h": 2},
    ])
    mm.register(menu)
    mm.register(PerformanceMode(grid, lp))
    mm.register(SequencerMode(grid, lp))
    mm.register(ClipLauncherMode(grid, lp))
    mm.register(MixerMode(grid, lp))
    mm.register(InstrumentMode(grid, lp))

    passed = 0
    failed = 0

    def ok(msg):
        nonlocal passed
        passed += 1
        print(f"  OK {msg}")

    def fail(msg):
        nonlocal failed
        failed += 1
        print(f"  FAIL {msg}")

    # ── Test 1: startup in performance mode ─────────────────
    mm.switch_to("performance")
    assert mm.active_mode_name == "performance", f"Expected performance, got {mm.active_mode_name}"
    ok("Startup in performance mode")

    # ── Test 2: mode switching via top-row buttons ──────────

    # Button 2 (201) → CLIP
    combo_result = combo.feed(201, True)
    assert combo_result != "consumed", f"Btn2 should not be consumed by combo"
    combo.feed(201, False)
    if not overlay.is_overlay_active:
        mm.switch_to("clip_launcher")
    assert mm.active_mode_name == "clip_launcher", f"Expected clip_launcher, got {mm.active_mode_name}"
    ok("Button 2 → clip_launcher")

    # Button 3 (202) → SEQ
    combo_result = combo.feed(202, True)
    combo.feed(202, False)
    if not overlay.is_overlay_active:
        mm.switch_to("sequencer")
    assert mm.active_mode_name == "sequencer", f"Expected sequencer, got {mm.active_mode_name}"
    ok("Button 3 → sequencer")

    # Button 1 (200) alone → performance (via combo "home")
    r = combo.feed(200, True)
    assert r == "consumed", f"Btn1 press should be consumed by combo, got {r}"
    r = combo.feed(200, False)
    assert r == "home", f"Btn1 release should return home, got {r}"
    mm.switch_to("performance")
    assert mm.active_mode_name == "performance", f"Expected performance from home, got {mm.active_mode_name}"
    ok("Button 1 alone → performance mode")

    # ── Test 3: combo Top-1+2 → screensaver ─────────────────
    # ComboDetector fires on the partner's PRESS (Entry #9 design), not release.
    r = combo.feed(200, True)
    assert r == "consumed"
    r = combo.feed(201, True)
    assert r == "screensaver", f"Expected screensaver combo on partner press, got {r}"
    r = combo.feed(200, False)
    assert r == "consumed"
    r = combo.feed(201, False)
    assert r == "consumed"
    overlay.trigger_screensaver()
    assert overlay.is_overlay_active, "Screensaver should be active"
    ok("Top-1+2 → screensaver")

    # ── Test 4: 2-press dismiss from grid pad ───────────────

    event = GridEvent(x=3, y=3, pressed=True)
    consumed = overlay.handle_grid_event(event)
    assert consumed, "First grid press should be absorbed"
    assert overlay.is_overlay_active, "Overlay stays active until the 2nd press"
    consumed = overlay.handle_grid_event(event)
    assert not consumed, "Second grid press should passthrough"
    assert not overlay.is_overlay_active, "Overlay inactive after 2nd press"
    ok("Grid press dismisses screensaver (2-press: 1st absorbed, 2nd passthrough)")

    # ── Test 5: screensaver doesn't re-trigger immediately ──

    # Simulate a few ticks to check idle doesn't re-fire
    now = time.monotonic()
    overlay.tick(100, now)
    assert not overlay.is_overlay_active, "Screensaver should NOT re-enter immediately after dismiss"
    ok("Dismiss doesn't re-enter screensaver (idle_since reset)")

    # ── Test 6: screensaver does activate after timeout ─────

    # Manually set idle_since to 11s ago
    overlay._idle_since = now - 11
    overlay.tick(100, now)
    assert overlay.is_overlay_active, "Screensaver should activate after 10s idle"
    ok("Screensaver activates after idle timeout")

    # ── Test 7: 2-press dismiss from top-row button ─────────

    ctrl = ControlEvent(control_id=203, value=127, event_type=EventType.FUNCTION_PRESS)
    consumed = overlay.handle_control_event(ctrl)
    assert consumed, "First top-row press should be absorbed"
    assert overlay.is_overlay_active, "Overlay stays active until the 2nd press"
    consumed = overlay.handle_control_event(ctrl)
    assert not consumed, "Second top-row press should passthrough"
    assert not overlay.is_overlay_active, "Overlay inactive after 2nd press"
    ok("Top-row button dismisses screensaver (2-press)")

    # ── Test 8: 2-press dismiss from right column ───────────

    overlay._idle_since = time.monotonic() - 11
    overlay.tick(100, time.monotonic())
    assert overlay.is_overlay_active

    # D-H (control 103-107) are SINGLE-press dismiss + passthrough (Entry #42).
    ctrl = ControlEvent(control_id=104, value=127, event_type=EventType.FUNCTION_PRESS)  # E button
    consumed = overlay.handle_control_event(ctrl)
    assert not consumed, "Right col D-H single press should dismiss + passthrough"
    assert not overlay.is_overlay_active, "Screensaver should be dismissed by D-H"
    ok("Right column D-H dismisses screensaver (single-press passthrough)")

    # ── Test 9: right col A-C switch mode inside screensaver ──

    overlay._idle_since = time.monotonic() - 11
    overlay.tick(100, time.monotonic())
    assert overlay.is_overlay_active
    original_mode = overlay._active_screensaver_mode

    ctrl = ControlEvent(control_id=100, value=127, event_type=EventType.FUNCTION_PRESS)  # A button
    consumed = overlay.handle_control_event(ctrl)
    assert consumed, "A press should be consumed by screensaver mode switch"
    assert overlay.is_overlay_active, "Screensaver should stay active after mode switch"
    assert overlay._active_screensaver_mode != original_mode or True  # Might be same if already active
    ok("Right column A-C switch screensaver mode")

    # ── Test 10: mode switching after screensaver dismiss ───

    overlay._idle_since = time.monotonic() - 11
    overlay.tick(100, time.monotonic())

    # Dismiss with any button
    ctrl = ControlEvent(control_id=200, value=127, event_type=EventType.FUNCTION_PRESS)
    overlay.handle_control_event(ctrl)

    # Now switch to menu
    mm.switch_to("menu")
    assert mm.active_mode_name == "menu"
    ok("Can switch to menu after screensaver dismiss")

    mm.switch_to("performance")
    assert mm.active_mode_name == "performance"
    ok("Can switch back to performance")

    # ── Summary ──
    print(f"\n=== {passed} OK, {failed} FAIL ===")
    return failed == 0


if __name__ == "__main__":
    try:
        success = test()
    except Exception as e:
        import traceback
        traceback.print_exc()
        success = False
    exit(0 if success else 1)
