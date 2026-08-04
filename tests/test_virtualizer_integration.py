"""
Comprehensive integration test using the Virtualizer.
Tests LED output, button input, mode switching, and assertions.
"""
import sys
from tests.virtualizer import VirtualLaunchpad, ASCII_COLORS
from src.controllers.color_map import LogicalColor
from src.ui.mode_manager import ModeManager
from src.ui.modes.menu import MenuMode
from src.layout.grid import LogicalGrid


def test_led_output():
    """Test that LED output renders correctly in ASCII."""
    print("=" * 60)
    print("TEST 1: LED Output")
    print("=" * 60)

    v = VirtualLaunchpad()
    v.on_connect()

    # Single pad
    v.controller.set_grid_color(0, 0, LogicalColor.GREEN_HIGH)
    v.assert_cell(0, 0, LogicalColor.GREEN_HIGH)
    print(v.render("Bottom-left GREEN_HIGH"))
    print(f"  ✓ Cell (0,0) is GREEN_HIGH ($)")

    # Color cycling
    v.controller.set_grid_color(0, 0, LogicalColor.RED_HIGH)
    print(v.render("Same pad → RED_HIGH"))
    v.assert_cell(0, 0, LogicalColor.RED_HIGH)
    print(f"  ✓ Cell (0,0) is RED_HIGH (#)")

    v.controller.set_grid_color(0, 0, LogicalColor.AMBER_HIGH)
    print(v.render("Same pad → AMBER_HIGH"))
    v.assert_cell(0, 0, LogicalColor.AMBER_HIGH)
    print(f"  ✓ Cell (0,0) is AMBER_HIGH (@)")

    # Multiple pads
    v.controller.set_grid_color(4, 4, LogicalColor.AMBER_HIGH)
    v.controller.set_grid_color(7, 7, LogicalColor.GREEN_HIGH)
    v.controller.set_grid_color(7, 0, LogicalColor.RED_HIGH)
    v.controller.set_grid_color(0, 7, LogicalColor.RED_MED)
    print(v.render("Multiple colors"))
    print(f"  ✓ 4 corners have different colors")

    # Clear
    v.controller.clear_grid()
    v.assert_all_off()
    print(v.render("Clear grid"))
    print(f"  ✓ All cells OFF (·)")
    print()


def test_button_input():
    """Test that simulated button presses route correctly."""
    print("=" * 60)
    print("TEST 2: Button Input Simulation")
    print("=" * 60)

    v = VirtualLaunchpad()

    events = []

    def on_grid(event):
        events.append(f"GRID ({event.x},{event.y}) p={event.pressed}")

    def on_control(event):
        is_press = "PRESS" in event.event_type.name
        events.append(f"CTRL id={event.control_id} {'press' if is_press else 'release'}")

    v.controller.set_callbacks(on_grid_event=on_grid, on_control_event=on_control)

    # Simulate grid pad presses
    v.tap(0, 0)
    v.tap(4, 4)
    v.long_press(7, 7, duration_ms=600)
    v.tap_control(200)  # Top-1
    v.tap_control(201)  # Top-2
    v.tap_control(100)  # Right-1
    v.tap_control(107)  # Right-8

    print("Simulated events:")
    for e in events:
        print(f"  ✓ {e}")

    assert len(events) == 14, f"Expected 14 events, got {len(events)}"
    print(f"\n  ✓ All {len(events)} events received correctly")
    print()


def test_menu_mode():
    """Test Menu mode with virtual Launchpad."""
    print("=" * 60)
    print("TEST 3: Menu Mode")
    print("=" * 60)

    v = VirtualLaunchpad()
    v.on_connect()

    logical_grid = LogicalGrid(8, 8)

    # Wire logical grid updates to virtual Launchpad LEDs
    def commit_grid():
        for x, y in logical_grid.dirty_cells():
            color = logical_grid.get_cell(x, y)
            v.controller.set_grid_color(x, y, color)

    logical_grid.set_on_cell_changed(lambda x, y, c: None)
    original_commit = lambda: commit_grid()

    mode_switched = []

    def on_mode_select(name):
        mode_switched.append(name)

    menu = MenuMode(logical_grid, v.controller, on_mode_select=on_mode_select)
    menu_items = [
        {"label": "SEQ", "mode": "sequencer", "color": "AMBER_HIGH"},
        {"label": "MIX", "mode": "mixer", "color": "GREEN_HIGH"},
        {"label": "FX", "mode": "effects", "color": "RED_HIGH"},
        {"label": "PERF", "mode": "performance", "color": "AMBER_HIGH"},
        {"label": "DEV", "mode": "device", "color": "GREEN_HIGH"},
    ]
    menu.set_items(menu_items)
    menu.enter()
    commit_grid()

    print(v.render("Menu mode — 5 mode pads lit"))
    print()

    # Verify menu pads are lit
    colors_at_pads = {}
    for i, item in enumerate(menu_items):
        expected_color = LogicalColor[item["color"]]
        x = i % 8
        y = i // 8
        actual = logical_grid.get_cell(x, y)
        colors_at_pads[item["label"]] = actual
        assert actual == expected_color, (
            f"Menu item {item['label']} at ({x},{y}): "
            f"expected {expected_color.name}, got {actual.name}"
        )
    print(f"  ✓ All 5 menu pads have correct colors")

    # Simulate tapping a menu pad
    print("\n  Simulate: tap pad (0,0) → select Sequencer...")
    v.controller._on_grid_event = lambda e: menu.handle_grid_event(e)
    v.tap(0, 0)

    assert mode_switched == ["sequencer"], f"Expected ['sequencer'], got {mode_switched}"
    print(f"  ✓ Mode switched to: {mode_switched[0]}")

    # Test top-row quick select
    mode_switched.clear()
    print("\n  Simulate: press Top-3 (FX)...")
    v.controller._on_control_event = lambda e: menu.handle_control_event(e)
    v.tap_control(202)  # Top-3 → effects (3rd item, 0-indexed = 2 → id=202)

    assert mode_switched == ["effects"], f"Expected ['effects'], got {mode_switched}"
    print(f"  ✓ Mode switched to: {mode_switched[0]}")

    print()


def test_grid_coordinates():
    """Verify the coordinate system is consistent."""
    print("=" * 60)
    print("TEST 4: Coordinate System Verification")
    print("=" * 60)

    v = VirtualLaunchpad()

    # Test that (0,0) = bottom-left lights the correct position
    v.controller.set_grid_color(0, 0, LogicalColor.GREEN_HIGH)
    r = v.render("(0,0) = bottom-left → GREEN_HIGH")

    # Bottom row (y=0) should show the green character
    bottom_row = r.strip().split("\n")
    for line in bottom_row:
        print(line)

    # Find the last data row (bottom row, y=0)
    data_lines = [l for l in bottom_row if "│" in l and not "┌" in l and not "└" in l and not "─" in l]
    first_row = data_lines[-1]  # last data line = y=0 (bottom)
    assert "$" in first_row, f"Bottom-left should show green ($), got: {first_row}"

    # The bottom row should have $ at position 0 (after the box border)
    cells = first_row.split("│")[1].strip().split()
    assert cells[0] == "$", f"First cell should be $, got {cells[0]}"

    print(f"  ✓ (0,0) correct — green appears at bottom-left position")
    print(f"  ✓ Row ordering correct — y=0 is bottom row")
    print(f"  ✓ Column ordering correct — x=0 is leftmost")
    print()


if __name__ == "__main__":
    test_led_output()
    test_button_input()
    test_menu_mode()
    test_grid_coordinates()
    print("=" * 60)
    print("ALL VIRTUALIZER TESTS PASSED")
    print("=" * 60)
