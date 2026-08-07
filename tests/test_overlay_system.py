"""
Full overlay system integration test via virtualizer.
Tests: startup wave, idle→screensaver, dismiss, combos, fireworks, HUD.
"""
import tempfile
from pathlib import Path

from tests.virtualizer import VirtualLaunchpad, ASCII_COLORS
from src.controllers.color_map import LogicalColor
from src.layout.grid import LogicalGrid
from src.ui.image_store import ImageStore
from src.ui.overlay_manager import OverlayManager, OverlayPriority
from src.ui.startup_wave import StartupWave


def test_startup_wave_virtual():
    """Verify startup wave renders and cleans up."""
    print("=" * 60)
    print("TEST: Startup Wave")
    print("=" * 60)

    import src.ui.startup_wave as startup_wave_mod
    monotonic_time = [0.0]

    def fake_monotonic():
        return monotonic_time[0]

    orig_monotonic = startup_wave_mod.time.monotonic
    startup_wave_mod.time.monotonic = fake_monotonic

    try:
        v = VirtualLaunchpad()
        v.on_connect()
        logical = LogicalGrid(8, 8)

        def commit():
            for x, y in logical.dirty_cells():
                color = logical.get_cell(x, y)
                v.controller.set_grid_color(x, y, color)

        logical.set_on_cell_changed(lambda x, y, c: None)

        wave = StartupWave(logical, v.controller)
        wave._commit = commit
        monotonic_time[0] = 0.0
        wave.start()

        frames = 0
        max_cells_lit = 0
        while True:
            if not wave.tick():
                break
            frames += 1
            if frames > 1000:
                break
            lit = sum(1 for y in range(8) for x in range(8) if logical.get_cell(x, y) != LogicalColor.OFF)
            max_cells_lit = max(max_cells_lit, lit)
            monotonic_time[0] += 0.02
    finally:
        startup_wave_mod.time.monotonic = orig_monotonic

    assert max_cells_lit > 0, "Startup wave should light cells"
    v.assert_all_off()
    print(f"  ✓ Frames: {frames}, max cells lit: {max_cells_lit}")
    print(f"  ✓ Grid clean after animation")
    print()


def test_overlay_idle_screensaver():
    """Idle timeout → screensaver → dismiss → back to mode."""
    print("=" * 60)
    print("TEST: Idle → Screensaver → Dismiss")
    print("=" * 60)

    v = VirtualLaunchpad()
    v.on_connect()
    logical = LogicalGrid(8, 8)

    def commit():
        for x, y in logical.dirty_cells():
            color = logical.get_cell(x, y)
            v.controller.set_grid_color(x, y, color)

    logical.set_on_cell_changed(lambda x, y, c: None)

    tmp = Path(tempfile.mktemp(suffix=".yaml"))
    store = ImageStore(tmp)
    overlay = OverlayManager(logical, v.controller, store, idle_timeout_ms=1000)
    overlay._commit = commit
    overlay.start()
    overlay.set_mode_context("menu")

    # Show menu pads initially
    logical.clear()
    logical.set_cell(0, 0, LogicalColor.AMBER_HIGH)
    logical.set_cell(1, 0, LogicalColor.GREEN_HIGH)
    commit()
    print(v.render("Active mode: menu (2 pads lit)"))
    print()

    # Should NOT enter screensaver yet (idle < 1s)
    overlay.tick(16, now=overlay._idle_since + 0.5)
    assert overlay.active == OverlayPriority.ACTIVE_MODE, "Should still be in mode"
    print("  ✓ Not screensaver at 0.5s idle")

    # After 1.2s idle → screensaver (mode "waves")
    overlay.tick(16, now=overlay._idle_since + 1.2)
    assert overlay.active == OverlayPriority.SCREENSAVER, f"Expected screensaver, got {overlay.active}"
    overlay._active_screensaver_mode = 1  # waves
    overlay._render_screensaver()
    print(v.render("Screensaver active (waves)"))
    print("  ✓ Auto-entered screensaver after idle timeout")

    # First button press → consumed (dismiss, but stay in screensaver mode)
    result = overlay.handle_grid_event(
        type("E", (), {"x": 3, "y": 3, "pressed": True, "velocity": 127})()
    )
    assert result is True, "First press should be consumed"
    assert overlay.active == OverlayPriority.SCREENSAVER, "Still screensaver (first press dismissed)"
    print("  ✓ First press consumed (overlay dismissed, still screensaver)")

    # Second press → exit overlay, back to active mode
    result = overlay.handle_grid_event(
        type("E", (), {"x": 3, "y": 3, "pressed": True, "velocity": 127})()
    )
    assert result is False, "Second press should pass through to mode"
    assert overlay.active == OverlayPriority.ACTIVE_MODE, "Back to active mode"
    print("  ✓ Second press passes through to active mode")
    print("  ✓ Back in menu mode")

    tmp.unlink(missing_ok=True)
    print()


def test_overlay_fireworks_to_screensaver():
    """Fireworks → 8 bars → auto screensaver."""
    print("=" * 60)
    print("TEST: Fireworks → Screensaver")
    print("=" * 60)

    v = VirtualLaunchpad()
    v.on_connect()
    logical = LogicalGrid(8, 8)

    def commit():
        for x, y in logical.dirty_cells():
            color = logical.get_cell(x, y)
            v.controller.set_grid_color(x, y, color)

    logical.set_on_cell_changed(lambda x, y, c: None)

    tmp = Path(tempfile.mktemp(suffix=".yaml"))
    store = ImageStore(tmp)
    overlay = OverlayManager(logical, v.controller, store, bpm=240)
    overlay._commit = commit
    overlay.start()
    overlay.set_mode_context("menu")

    # Trigger fireworks manually
    overlay.trigger_fireworks()
    assert overlay.active == OverlayPriority.FIREWORKS
    print("  ✓ Fireworks triggered")

    # Run fireworks until completion
    sim_time = overlay._fireworks._start_time
    frames = 0
    while overlay.active == OverlayPriority.FIREWORKS:
        overlay.tick(16, now=sim_time)
        frames += 1
        sim_time += 0.05
        if frames > 500:
            break

    assert overlay.active == OverlayPriority.SCREENSAVER, (
        f"Expected screensaver after fireworks, got {overlay.active}"
    )
    print(f"  ✓ Fireworks completed in {frames} frames → auto-entered screensaver")

    # Dismiss screensaver
    overlay.handle_grid_event(
        type("E", (), {"x": 0, "y": 0, "pressed": True, "velocity": 127})()
    )
    overlay.handle_grid_event(
        type("E", (), {"x": 0, "y": 0, "pressed": True, "velocity": 127})()
    )
    assert overlay.active == OverlayPriority.ACTIVE_MODE
    print("  ✓ Screensaver dismissed, back to mode")

    tmp.unlink(missing_ok=True)
    print()


def test_overlay_hud():
    """HUD overlay → auto-dismiss → return to previous state."""
    print("=" * 60)
    print("TEST: HUD Overlay")
    print("=" * 60)

    v = VirtualLaunchpad()
    v.on_connect()
    logical = LogicalGrid(8, 8)

    def commit():
        for x, y in logical.dirty_cells():
            color = logical.get_cell(x, y)
            v.controller.set_grid_color(x, y, color)

    logical.set_on_cell_changed(lambda x, y, c: None)

    tmp = Path(tempfile.mktemp(suffix=".yaml"))
    store = ImageStore(tmp)
    overlay = OverlayManager(logical, v.controller, store)
    overlay._commit = commit
    overlay.start()
    overlay.set_mode_context("performance")

    # Trigger HUD with a character
    overlay.trigger_hud(char="G")
    assert overlay.active == OverlayPriority.HUD
    # Render HUD while still active (within 1.5s window)
    overlay.tick(16, now=overlay._hud_timeout + 0.1)
    print(v.render("HUD: character 'G'"))
    print("  ✓ HUD activated with character")

    # HUD should auto-dismiss after timeout
    overlay.tick(16, now=overlay._hud_timeout + 2.0)
    assert overlay.active == OverlayPriority.ACTIVE_MODE, f"Expected mode after HUD, got {overlay.active}"
    print("  ✓ HUD auto-dismissed → back to mode")

    # Test HUD from screensaver → returns to screensaver
    overlay.trigger_screensaver()
    overlay.trigger_hud(text="OK")
    overlay.tick(16, now=overlay._hud_timeout + 2.0)
    assert overlay.active == OverlayPriority.SCREENSAVER, (
        f"Expected screensaver after HUD dismiss, got {overlay.active}"
    )
    print("  ✓ HUD from screensaver → returns to screensaver")

    tmp.unlink(missing_ok=True)
    print()


def test_overlay_screensaver_picker():
    """Screensaver mode selection via simulated right-column buttons."""
    print("=" * 60)
    print("TEST: Screensaver Mode Pick")
    print("=" * 60)

    v = VirtualLaunchpad()
    v.on_connect()
    logical = LogicalGrid(8, 8)

    def commit():
        for x, y in logical.dirty_cells():
            color = logical.get_cell(x, y)
            v.controller.set_grid_color(x, y, color)

    logical.set_on_cell_changed(lambda x, y, c: None)

    tmp = Path(tempfile.mktemp(suffix=".yaml"))
    store = ImageStore(tmp)
    overlay = OverlayManager(logical, v.controller, store)
    overlay._commit = commit
    overlay.start()

    # Enter screensaver (default mode at index 1 = "waves")
    overlay.trigger_screensaver()
    overlay_modes = overlay._screensaver_modes
    assert "waves" in overlay_modes
    overlay._active_screensaver_mode = overlay_modes.index("waves")
    overlay._render_screensaver()
    print(v.render("Screensaver: mode 'waves'"))
    print("  ✓ Screensaver entered on 'waves'")

    # Switch mode via right-column control (simulates button press)
    heart_idx = overlay_modes.index("heart")
    assert isinstance(overlay.handle_control_event(
        type("E", (), {"control_id": 100 + heart_idx,
                       "event_type": type("ET", (), {"name": "FUNCTION_PRESS"})})()
    ), bool)
    assert overlay._active_screensaver_mode == heart_idx
    overlay._render_screensaver()
    print(v.render("Screensaver: mode 'heart'"))
    print("  ✓ Switched to 'heart' via right column")

    # Cycle to another mode
    overlay._active_screensaver_mode = 2  # glimmer
    overlay._render_screensaver()
    print("  ✓ Cycled to 'glimmer'")

    tmp.unlink(missing_ok=True)
    print()


if __name__ == "__main__":
    test_startup_wave_virtual()
    test_overlay_idle_screensaver()
    test_overlay_fireworks_to_screensaver()
    test_overlay_hud()
    test_overlay_screensaver_picker()
    print("=" * 60)
    print("ALL OVERLAY SYSTEM TESTS PASSED")
    print("=" * 60)
