"""
Comprehensive integration test battery.
Proves (or fails) every interaction: combo detection, overlay dismiss,
mode switching, screensaver behavior.
"""
import time
from src.layout.grid import LogicalGrid
from src.controllers.launchpad_mk1 import LaunchpadMiniMK1
from src.controllers.base import EventType, ControlEvent, GridEvent, LogicalColor
from src.midi.manager import MidiManager
from src.ui.mode_manager import ModeManager
from src.ui.modes.menu import MenuMode
from src.ui.modes.sequencer import SequencerMode
from src.ui.modes.clip_launcher import ClipLauncherMode
from src.ui.modes.mixer import MixerMode
from src.ui.modes.instrument import InstrumentMode
from src.ui.modes.performance import PerformanceMode
from src.ui.overlay_manager import OverlayManager, OverlayPriority
from src.ui.combo_detector import ComboDetector
from src.ui.image_store import ImageStore


class T:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def ok(self, msg):
        self.passed += 1

    def fail(self, msg):
        self.failed += 1
        print(f"  FAIL {msg}")

    def check(self, cond, msg):
        if cond:
            self.passed += 1
        else:
            self.failed += 1
            print(f"  FAIL {msg}")

    def skip(self, msg):
        self.skipped += 1
        print(f"  SKIP {msg} (not testable without hardware)")

    def summary(self, label):
        total = self.passed + self.failed + self.skipped
        print(f"\n--- {label}: {self.passed} PASS, {self.failed} FAIL, {self.skipped} SKIP (of {total}) ---")


def make_env():
    grid = LogicalGrid(8, 8)
    mgr = MidiManager(poll_interval=999)
    lp = LaunchpadMiniMK1(mgr)
    lp.set_callbacks(on_grid_event=lambda e: None, on_control_event=lambda e: None)
    overlay = OverlayManager(grid, lp, ImageStore(), idle_timeout_ms=10000, bpm=120)
    overlay.start()
    return grid, mgr, lp, overlay


def make_modes(grid, lp):
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
    for m in [menu, PerformanceMode(grid, lp), SequencerMode(grid, lp),
              ClipLauncherMode(grid, lp), MixerMode(grid, lp), InstrumentMode(grid, lp)]:
        mm.register(m)
    return mm, menu


def press(control_id, pressed=True):
    return ControlEvent(control_id=control_id, value=(127 if pressed else 0),
                        event_type=(EventType.FUNCTION_PRESS if pressed else EventType.FUNCTION_RELEASE))


def grid_press(x, y):
    return GridEvent(x=x, y=y, pressed=True)


# ── TEST 1: Combo detection ────────────────────────────────────

def test_combo_basics():
    t = T()
    print("\n=== Combo Detection ===")
    d = ComboDetector()

    r = d.feed(200, True)
    t.check(r == "consumed", "Top-1 press → consumed")
    r = d.feed(200, False)
    t.check(r == "home", "Top-1 release alone → home")
    t.check(d.feed(201, True) is None, "Top-2 alone → None (normal)")
    t.check(d.feed(201, False) is None, "Top-2 release → None")

    r = d.feed(200, True)
    t.check(r == "consumed", "Top-1 hold start")
    r = d.feed(201, True)
    t.check(r == "screensaver", "Top-1+2 → screensaver (fires on partner press)")
    r = d.feed(200, False)
    t.check(r == "consumed", "Top-1 release after combo → consumed")
    r = d.feed(201, False)
    t.check(r == "consumed", "Top-2 release after combo → consumed")

    r = d.feed(200, True)
    t.check(r == "consumed", "Fresh Top-1 → consumed")
    r = d.feed(202, True)
    t.check(r == "fireworks", "Top-1+3 → fireworks")

    # Non-combo button while Top-1 held: should pass through normally
    d2 = ComboDetector()
    d2.feed(200, True)
    r = d2.feed(203, True)
    t.check(r is None, "Top-4 while Top-1 held → passes through")
    r = d2.feed(200, False)
    t.check(r == "home", "Top-1 release still fires home")

    # tick timeout
    d3 = ComboDetector(combo_window_ms=50)
    d3.feed(200, True)
    time.sleep(0.06)
    r = d3.tick()
    t.check(r == "home", "Combo window expiry → home")

    t.summary("Combo detection")
    return t


# ── TEST 2: Overlay lifecycle ─────────────────────────────────

def test_overlay_lifecycle():
    t = T()
    print("\n=== Overlay Lifecycle ===")
    grid, _, lp, overlay = make_env()
    _, menu = make_modes(grid, lp)

    t.check(not overlay.is_overlay_active, "Starts in active mode")

    # Activate screensaver
    overlay.trigger_screensaver()
    t.check(overlay.is_overlay_active, "Screensaver activates")
    t.check(overlay._active == OverlayPriority.SCREENSAVER, "Priority is SCREENSAVER")

    # Dismiss via top-row (2-press: first absorb, second passthrough)
    consumed = overlay.handle_control_event(press(201))
    t.check(consumed, "Top-2 press 1 → consumed (dismiss)")
    consumed = overlay.handle_control_event(press(201))
    t.check(not consumed, "Top-2 press 2 → not consumed (passthrough)")
    t.check(not overlay.is_overlay_active, "Screensaver dismissed")

    # Re-activate
    overlay.trigger_screensaver()
    t.check(overlay.is_overlay_active, "Re-activated")

    # Dismiss via grid (2-press)
    consumed = overlay.handle_grid_event(grid_press(3, 3))
    t.check(consumed, "Grid press 1 → consumed (dismiss)")
    consumed = overlay.handle_grid_event(grid_press(3, 3))
    t.check(not consumed, "Grid press 2 → passthrough")
    t.check(not overlay.is_overlay_active, "Dismissed by grid")

    # Fireworks
    overlay.trigger_fireworks()
    t.check(overlay.is_overlay_active, "Fireworks activates")
    t.check(overlay._active == OverlayPriority.FIREWORKS, "Priority is FIREWORKS")

    consumed = overlay.handle_control_event(press(200))
    t.check(consumed, "Top-1 press 1 → dismisses fireworks (absorbed)")
    t.check(overlay.is_overlay_active, "Fireworks still active after dismiss tap")
    consumed = overlay.handle_control_event(press(200))
    t.check(not consumed, "Top-1 press 2 → passthrough")
    t.check(not overlay.is_overlay_active, "Fireworks dismissed")

    # HUD
    overlay.trigger_hud(char="G")
    t.check(overlay.is_overlay_active, "HUD activates")
    consumed = overlay.handle_grid_event(grid_press(2, 2))
    t.check(consumed, "HUD dismissed by grid (consumed, no passthrough)")
    t.check(not overlay.is_overlay_active, "HUD dismissed")

    t.summary("Overlay lifecycle")
    return t


# ── TEST 3: Right column in screensaver ────────────────────────

def test_right_column_screensaver():
    t = T()
    print("\n=== Right Column in Screensaver ===")
    grid, _, lp, overlay = make_env()
    _, menu = make_modes(grid, lp)

    overlay.trigger_screensaver()
    original = overlay._active_screensaver_mode

    # A press → switch mode
    consumed = overlay.handle_control_event(press(100))  # A
    t.check(consumed, "A press consumed by screensaver")
    t.check(overlay.is_overlay_active, "Screensaver still active after A")

    # B press → switch mode
    consumed = overlay.handle_control_event(press(101))  # B
    t.check(consumed, "B press consumed")
    t.check(overlay.is_overlay_active, "Still active after B")

    # C press → switch mode
    consumed = overlay.handle_control_event(press(102))  # C
    t.check(consumed, "C press consumed")
    t.check(overlay.is_overlay_active, "Still active after C")

    # D press → dismiss + passthrough
    consumed = overlay.handle_control_event(press(103))  # D
    t.check(not consumed, "D press → not consumed (dismiss + passthrough)")
    t.check(not overlay.is_overlay_active, "D dismisses screensaver")

    # Re-enter screensaver, test E-H all dismiss
    for idx, label in [(104, "E"), (105, "F"), (106, "G"), (107, "H")]:
        overlay.trigger_screensaver()
        consumed = overlay.handle_control_event(press(idx))
        t.check(not consumed, f"{label} press → dismiss + passthrough")
        t.check(not overlay.is_overlay_active, f"{label} dismissed")

    # Dismiss consumes (HUD override)
    overlay.trigger_hud(char="X")
    t.check(overlay.is_overlay_active, "HUD active")
    consumed = overlay.handle_control_event(press(104))
    t.check(consumed, "HUD dismissed by E press (HUD specific behavior)")

    t.summary("Right column screensaver")
    return t


# ── TEST 4: Idle timer ────────────────────────────────────────

def test_idle_timer():
    t = T()
    print("\n=== Idle Timer ===")
    grid, _, lp, overlay = make_env()

    now = time.monotonic()

    # Not idle yet
    overlay._idle_since = now - 5
    overlay.tick(100, now)
    t.check(not overlay.is_overlay_active, "5s idle → no screensaver")

    # After timeout
    overlay._idle_since = now - 11
    overlay.tick(100, now)
    t.check(overlay.is_overlay_active, "11s idle → screensaver activates")

    # Dismiss resets timer (2-press)
    overlay.handle_control_event(press(201))
    overlay.handle_control_event(press(201))
    t.check(not overlay.is_overlay_active, "Dismissed after timeout")
    # Verify idle was reset (should be near 'now')
    elapsed = (time.monotonic() - overlay._idle_since)
    t.check(elapsed < 1.0, f"Idle timestamp reset after dismiss (age={elapsed:.1f}s)")

    # Verify doesn't re-fire immediately
    overlay.tick(100, time.monotonic())
    t.check(not overlay.is_overlay_active, "Does not re-enter immediately after dismiss")

    t.summary("Idle timer")
    return t


# ── TEST 5: Mode switching ────────────────────────────────────

def test_mode_switching():
    t = T()
    print("\n=== Mode Switching ===")
    grid, _, lp, _ = make_env()
    mm, menu = make_modes(grid, lp)

    mm.switch_to("performance")
    t.check(mm.active_mode_name == "performance", "Start → performance")

    mm.switch_to("clip_launcher")
    t.check(mm.active_mode_name == "clip_launcher", "Switch → clip_launcher")

    mm.switch_to("sequencer")
    t.check(mm.active_mode_name == "sequencer", "Switch → sequencer")

    mm.switch_to("mixer")
    t.check(mm.active_mode_name == "mixer", "Switch → mixer")

    mm.switch_to("instrument")
    t.check(mm.active_mode_name == "instrument", "Switch → instrument")

    mm.switch_to("menu")
    t.check(mm.active_mode_name == "menu", "Switch → menu")

    mm.switch_to("performance")
    t.check(mm.active_mode_name == "performance", "Switch → performance again")

    # Switching to same mode is a no-op
    mm.switch_to("performance")
    t.check(mm.active_mode_name == "performance", "Switch to same mode → no-op")

    # Unknown mode doesn't change
    prev = mm.active_mode_name
    mm.switch_to("nonexistent")
    t.check(mm.active_mode_name == prev, f"Unknown mode → stays at {prev}")

    t.summary("Mode switching")
    return t


# ── TEST 6: Engine-like button flow ──────────────────────────

def test_button_flow():
    """Simulate the full engine button dispatch: combo → overlay → mode."""
    t = T()
    print("\n=== Engine Button Flow ===")
    grid, _, lp, _ = make_env()
    mm, menu = make_modes(grid, lp)
    overlay = OverlayManager(grid, lp, ImageStore(), idle_timeout_ms=10000)
    overlay.start()
    combo = ComboDetector()

    mm.switch_to("performance")

    # Engine flow simulation
    def handle_control(event):
        is_press = "PRESS" in event.event_type.name
        if overlay and is_press:
            overlay.mark_activity()
        result = combo.feed(event.control_id, is_press)
        if result == "consumed":
            return "combo_consumed"
        if result == "home":
            mm.switch_to("performance")
            return "combo_home"
        if result == "screensaver":
            overlay.trigger_screensaver()
            return "combo_screensaver"
        if result == "fireworks":
            overlay.trigger_fireworks()
            return "combo_fireworks"
        if overlay.handle_control_event(event):
            return "overlay_consumed"
        # Fall through: check menu items
        if is_press and not overlay.is_overlay_active:
            cid = event.control_id
            if 201 <= cid <= 208:
                top_idx = cid - 200
                if top_idx < len(menu._items):
                    item = menu._items[top_idx]
                    mm.switch_to(item["mode"])
                    return f"switched_to_{item['mode']}"
        return "passthrough"

    # Button 2 → CLIP
    r = handle_control(press(201))
    t.check(r == "switched_to_clip_launcher", f"Btn2 → clip_launcher ({r})")
    t.check(mm.active_mode_name == "clip_launcher", "Mode is clip_launcher")

    # Button 3 → SEQ
    r = handle_control(press(202))
    t.check(r == "switched_to_sequencer", f"Btn3 → sequencer ({r})")
    t.check(mm.active_mode_name == "sequencer", "Mode is sequencer")

    # Button 1 → performance
    r = handle_control(press(200))
    t.check(r == "combo_consumed", "Btn1 press consumed by combo")
    r = handle_control(ControlEvent(control_id=200, event_type=EventType.FUNCTION_RELEASE, value=0))
    t.check(r == "combo_home", "Btn1 release → combo home → performance")
    t.check(mm.active_mode_name == "performance", "Mode is performance")

    # Top-1+2 → screensaver
    handle_control(press(200))
    r = handle_control(press(201))
    t.check(r == "combo_screensaver", "Top-1+2 → screensaver")
    t.check(overlay.is_overlay_active, "Screensaver active")
    # Clean up combo state
    handle_control(ControlEvent(control_id=200, event_type=EventType.FUNCTION_RELEASE, value=0))
    handle_control(ControlEvent(control_id=201, event_type=EventType.FUNCTION_RELEASE, value=0))

    # Dismiss screensaver (2-press): first press dismisses, second passes through
    r = handle_control(press(202))
    t.check(r == "overlay_consumed", f"Btn3 press 1 → dismiss only ({r})")
    t.check(overlay.is_overlay_active, "Screensaver still active after dismiss tap")
    r = handle_control(press(202))
    t.check(r == "switched_to_sequencer", f"Btn3 press 2 → passthrough to sequencer ({r})")
    t.check(not overlay.is_overlay_active, "Screensaver dismissed after 2nd press")
    t.check(mm.active_mode_name == "sequencer", "Landed in sequencer")

    # Top-1+3 from non-home mode
    handle_control(press(200))
    r = handle_control(press(202))
    t.check(r == "combo_fireworks", "Top-1+3 → fireworks")
    t.check(overlay.is_overlay_active, "Fireworks active")
    # Clean up
    handle_control(ControlEvent(control_id=200, event_type=EventType.FUNCTION_RELEASE, value=0))
    handle_control(ControlEvent(control_id=202, event_type=EventType.FUNCTION_RELEASE, value=0))

    # Dismiss fireworks (2-press): first dismisses, second passes through
    r = handle_control(press(201))
    t.check(r == "overlay_consumed", f"Btn2 press 1 → dismiss fireworks ({r})")
    r = handle_control(press(201))
    t.check(r == "switched_to_clip_launcher", f"Btn2 press 2 → passthrough to clip_launcher ({r})")
    t.check(not overlay.is_overlay_active, "Fireworks dismissed")

    t.summary("Engine button flow")
    return t


# ── TEST 7: Mode rendering verification ───────────────────────

def test_mode_render():
    """Verify each mode renders unique correct cells to grid_state."""
    t = T()
    print("\n=== Mode Rendering ===")
    grid, _, lp, _ = make_env()
    mm, menu = make_modes(grid, lp)

    def lit_cells(mode_name):
        lp.reset_grid_state()
        mm.switch_to(mode_name)
        grid.clear()
        # simulate enter (which calls render + commit)
        mode = mm._modes[mode_name]
        mode.enter()
        cells = {}
        for y in range(8):
            for x in range(8):
                if lp._grid_state[y][x] != LogicalColor.OFF:
                    cells[(x, y)] = lp._grid_state[y][x]
        mode.exit()
        return cells

    # Menu
    cells = lit_cells("menu")
    t.check(len(cells) == 24, f"Menu has 24 lit cells (6 blocks × 2×2), got {len(cells)}")
    t.check(cells.get((0, 6)) == LogicalColor.RED_HIGH, f"PERF at (0,6) is RED_HIGH, got {cells.get((0,6))}")
    t.check(cells.get((2, 6)) == LogicalColor.RED_MED, f"CLIP at (2,6) is RED_MED, got {cells.get((2,6))}")
    t.check(cells.get((4, 6)) == LogicalColor.AMBER_HIGH, f"SEQ at (4,6) is AMBER_HIGH, got {cells.get((4,6))}")
    t.check(cells.get((0, 4)) == LogicalColor.GREEN_HIGH, f"MIX at (0,4) is GREEN_HIGH, got {cells.get((0,4))}")
    t.check(cells.get((2, 4)) == LogicalColor.GREEN_MED, f"INST at (2,4) is GREEN_MED, got {cells.get((2,4))}")
    t.check(cells.get((4, 4)) == LogicalColor.AMBER_MED, f"MENU at (4,4) is AMBER_MED, got {cells.get((4,4))}")

    # Clip Launcher — 4 quadrants (bottom row y0 = track-stop, so RED quadrant is y1-3)
    cells = lit_cells("clip_launcher")
    t.check(len(cells) == 44, f"Clip launcher has 44 lit cells (amber16+green16+red12), got {len(cells)}")
    t.check(cells.get((0, 7)) == LogicalColor.AMBER_HIGH, f"CLIP top-left = AMBER_HIGH, got {cells.get((0,7))}")
    t.check(cells.get((4, 7)) == LogicalColor.GREEN_HIGH, f"CLIP top-right = GREEN_HIGH, got {cells.get((4,7))}")
    t.check(cells.get((4, 3)) == LogicalColor.RED_MED, f"CLIP bottom-right = RED_MED, got {cells.get((4,3))}")
    t.check((0, 3) not in cells, "CLIP bottom-left is OFF/empty")

    # Sequencer
    cells = lit_cells("sequencer")
    t.check(len(cells) >= 2, f"Sequencer has cells (play LED + markers), got {len(cells)}")

    # Verify clip_launcher ≠ sequencer (Entry #39 bug)
    lp.reset_grid_state()
    mm.switch_to("clip_launcher")
    clip_state = [row[:] for row in lp._grid_state]
    lp.reset_grid_state()
    mm.switch_to("sequencer")
    seq_state = [row[:] for row in lp._grid_state]
    same = clip_state == seq_state
    t.check(not same, "CLIP ≠ SEQ render (distinct grids)")

    # Performance
    cells = lit_cells("performance")
    t.check(len(cells) > 0, f"Performance has cells, got {len(cells)}")

    # Mixer
    cells = lit_cells("mixer")
    t.check(len(cells) > 0, f"Mixer has cells, got {len(cells)}")

    # Instrument
    cells = lit_cells("instrument")
    t.check(len(cells) == 64, f"Instrument fills all 64 cells, got {len(cells)}")
    t.check(cells.get((0, 7)) == LogicalColor.RED_HIGH, "Root notes are RED_HIGH")
    t.check(cells.get((2, 7)) == LogicalColor.AMBER_LOW, "Background is AMBER_LOW")

    t.summary("Mode rendering")
    return t


# ── TEST 8: clear_grid prevents ghost cells ────────────────────

def test_clear_grid_ghost_prevention():
    t = T()
    print("\n=== Ghost Cell Prevention ===")
    grid, _, lp, _ = make_env()
    mm, menu = make_modes(grid, lp)

    # Set grid_state to fake garbage (startup wave leftovers)
    for y in range(8):
        for x in range(8):
            lp._grid_state[y][x] = LogicalColor.GREEN_HIGH

    # Switch to menu → clear_grid runs → menu renders
    mm.switch_to("menu")

    # Count OFF vs non-OFF cells
    off = 0
    lit = 0
    for y in range(8):
        for x in range(8):
            if lp._grid_state[y][x] == LogicalColor.OFF:
                off += 1
            elif lp._grid_state[y][x] not in (
                LogicalColor.RED_HIGH, LogicalColor.RED_MED,
                LogicalColor.AMBER_HIGH, LogicalColor.GREEN_HIGH, LogicalColor.GREEN_MED,
                LogicalColor.AMBER_MED,
            ):
                lit += 1  # Unexpected color
            else:
                lit += 1

    t.check(off == 64 - 24, f"After menu render: {off} OFF cells (expected 40)")
    t.check(lit == 24, f"After menu render: {lit} lit cells (expected 24 - the 6 mode blocks)")
    t.check(lp._grid_state[6][0] == LogicalColor.RED_HIGH, "PERF uses RED_HIGH")
    t.check(lp._grid_state[6][2] == LogicalColor.RED_MED, "CLIP uses RED_MED")

    t.summary("Ghost cell prevention")
    return t


# ── Run all tests ──────────────────────────────────────────────

def main():
    all_tests = [
        test_combo_basics,
        test_overlay_lifecycle,
        test_right_column_screensaver,
        test_idle_timer,
        test_mode_switching,
        test_button_flow,
        test_mode_render,
        test_clear_grid_ghost_prevention,
    ]

    grand_passed = 0
    grand_failed = 0
    grand_skipped = 0

    for test_fn in all_tests:
        name = test_fn.__name__
        print(f"\n━━━ {name} ━━━")
        try:
            t = test_fn()
            grand_passed += t.passed
            grand_failed += t.failed
            grand_skipped += t.skipped
        except Exception as e:
            import traceback
            traceback.print_exc()
            grand_failed += 1
            print(f"  CRASH: {e}")

    total = grand_passed + grand_failed + grand_skipped
    print(f"\n{'='*50}")
    print(f"TOTAL: {grand_passed} PASS, {grand_failed} FAIL, {grand_skipped} SKIP ({total} checks)")
    print(f"{'='*50}")

    return grand_failed == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
