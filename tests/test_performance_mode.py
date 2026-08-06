"""
Unit test for Performance Mode — volume bars, FX presets, disable toggles.
"""
import sys
sys.path.insert(0, ".")

from src.ui.modes.performance import PerformanceMode, CHANNELS, FX_COUNT, NUM_PADS, MAX_VOL, MIN_VOL
from src.controllers.base import GridEvent, LogicalColor


class MockGrid:
    def __init__(self):
        self._cells = {}
        self._dirty = set()

    def set_cell(self, x: int, y: int, color: LogicalColor):
        self._cells[(x, y)] = color
        self._dirty.add((x, y))

    def get_cell(self, x: int, y: int) -> LogicalColor:
        return self._cells.get((x, y), LogicalColor.OFF)

    def get(self, x: int, y: int) -> LogicalColor:
        return self._cells.get((x, y), LogicalColor.OFF)

    def clear(self):
        self._cells.clear()
        self._dirty.clear()

    def dirty_cells(self):
        d = list(self._dirty)
        self._dirty.clear()
        return d

    def commit(self):
        pass

    def dump_vol(self, ch: str):
        vc = CHANNELS[ch]["vol_col"]
        return [(y, self.get(vc, y).name) for y in range(NUM_PADS)]

    def dump_fx(self, ch: str, fx_idx: int):
        s = CHANNELS[ch]["fx_start"]
        pm = PerformanceMode.__new__(PerformanceMode)
        pr = pm._fx_preset_row(fx_idx)
        dr = pm._fx_disable_row(fx_idx)
        return {
            "presets": [(s + p, self.get(s + p, pr).name) for p in range(3)],
            "disable": [(s + p, self.get(s + p, dr).name) for p in range(3)],
        }


class MockController:
    def set_grid_color(self, x, y, color):
        pass


def g_press(x, y):
    return GridEvent(x, y, True)


def test_volume_press():
    print("=== Volume Press Tests ===")
    grid = MockGrid()
    pm = PerformanceMode(grid, MockController(), osc_bridge=None)
    pm.enter()
    pm._render()

    assert pm._volumes["GTR"] == 24
    assert pm._volumes["VOX"] == 24

    pad, sub = pm._volume_to_pad(24)
    assert pad == 3 and sub is False, f"24 should map to pad 3 (green), got {pad}/{sub}"

    pm._handle_volume_press("GTR", 7)
    pm._render()
    assert pm._volumes["GTR"] == 32, f"Pad 7 press should set GTR to 32, got {pm._volumes['GTR']}"
    print(f"  Pad 7 press → GTR volume = {pm._volumes['GTR']} ✓")

    pm._handle_volume_press("GTR", 7)
    pm._render()
    assert pm._volumes["GTR"] == 31, f"Second pad 7 press should set GTR to 31, got {pm._volumes['GTR']}"
    assert pm._vol_sub["GTR"] is True, f"Should be sub-level"
    print(f"  Pad 7 second press → GTR volume = {pm._volumes['GTR']} (sub) ✓")

    pm._handle_volume_press("GTR", 7)
    pm._render()
    assert pm._volumes["GTR"] == 32, f"Third pad 7 press should cycle back to 32"
    print(f"  Pad 7 third press → GTR volume = {pm._volumes['GTR']} ✓")

    pm._handle_volume_press("GTR", 2)
    pm._render()
    assert pm._volumes["GTR"] == 22, f"Pad 2 press should set to 22, got {pm._volumes['GTR']}"
    print(f"  Pad 2 press → GTR volume = {pm._volumes['GTR']} ✓")

    pm._handle_volume_press("GTR", 2)
    pm._render()
    assert pm._volumes["GTR"] == 21, f"Pad 2 second press should set to 21, got {pm._volumes['GTR']}"
    print(f"  Pad 2 second press → GTR volume = {pm._volumes['GTR']} ✓")

    print("  Volume bar rendering (GTR):")
    for y, col in reversed(grid.dump_vol("GTR")):
        print(f"    y={y}: {col}")

    cur_pad, cur_sub = pm._volume_to_pad(pm._volumes["GTR"])
    assert grid.get(0, cur_pad) == LogicalColor.AMBER_HIGH, "Current pad should be AMBER (sub)"

    for y in range(cur_pad + 1, NUM_PADS):
        assert grid.get(0, y) == LogicalColor.RED_HIGH, f"Pad y={y} above current should be RED"

    for y in range(cur_pad):
        assert grid.get(0, y) == LogicalColor.OFF, f"Pad y={y} below current should be OFF"


def test_volume_mute():
    print("\n=== Volume Mute Tests ===")
    grid = MockGrid()
    pm = PerformanceMode(grid, MockController(), osc_bridge=None)
    pm.enter()
    pm._render()

    pm._volumes["GTR"] = 18
    pm._vol_sub["GTR"] = False
    pm._handle_volume_press("GTR", 0)
    pm._render()
    assert pm._muted_ch["GTR"] is True, f"Pad 0 double-press at 18 should mute"
    assert pm._volumes["GTR"] == 0
    print(f"  Pad 0 at level 18 → double-press → muted ✓")

    for y in range(NUM_PADS):
        assert grid.get(0, y) == LogicalColor.RED_HIGH, f"Full column should be RED when muted, y={y} is {grid.get(0, y)}"
    print(f"  Full column RED when muted ✓")

    pm._handle_volume_press("GTR", 5)
    pm._render()
    assert pm._muted_ch["GTR"] is False, f"Any pad press should unmute"
    assert pm._volumes["GTR"] == 28
    print(f"  Pad 5 press from mute → unmutes, volume={pm._volumes['GTR']} ✓")


def test_fx_preset():
    print("\n=== FX Preset Tests ===")
    grid = MockGrid()
    pm = PerformanceMode(grid, MockController(), osc_bridge=None)
    pm.enter()
    pm._render()

    pm._handle_fx_press("GTR", 1, pm._fx_preset_row(0))
    pm._render()
    assert pm._fx_enabled["GTR"][0] is True, "Pressing preset should enable disabled FX"
    assert pm._fx_presets["GTR"][0] == 1, f"Pad 1 press should select preset 1, got {pm._fx_presets['GTR'][0]}"
    assert pm._fx_bank["GTR"][0] is False
    print(f"  FX0 pad 1 → enabled, preset={pm._fx_presets['GTR'][0]}, bank=1 ✓")

    state = grid.dump_fx("GTR", 0)
    assert state["presets"][0][1] == "AMBER_HIGH", f"Pad 1 should be AMBER (selected), got {state['presets'][0]}"
    assert state["presets"][1][1] == "GREEN_HIGH", f"Pad 2 should be GREEN, got {state['presets'][1]}"
    print(f"  Colors: {state['presets']} ✓")

    pm._handle_fx_press("GTR", 3, pm._fx_preset_row(0))
    pm._render()
    assert pm._fx_presets["GTR"][0] == 3, f"Pad 3 press should switch to preset 3, got {pm._fx_presets['GTR'][0]}"
    assert pm._fx_bank["GTR"][0] is False
    state = grid.dump_fx("GTR", 0)
    assert state["presets"][2][1] == "AMBER_HIGH", "Pad 3 should now be AMBER"
    print(f"  FX0 pad 3 → preset=3 ✓")

    pm._handle_fx_press("GTR", 3, pm._fx_preset_row(0))
    pm._render()
    assert pm._fx_presets["GTR"][0] == 6, f"Pad 3 second press → bank 2, preset 6, got {pm._fx_presets['GTR'][0]}"
    assert pm._fx_bank["GTR"][0] is True
    state = grid.dump_fx("GTR", 0)
    assert state["presets"][2][1] == "RED_HIGH", "Pad 3 should be RED (bank 2)"
    print(f"  FX0 pad 3 second press → bank 2, preset=6, color=RED ✓")

    pm._handle_fx_press("GTR", 3, pm._fx_preset_row(0))
    pm._render()
    assert pm._fx_presets["GTR"][0] == 3, f"Pad 3 third press → bank 1, preset 3"
    assert pm._fx_bank["GTR"][0] is False
    state = grid.dump_fx("GTR", 0)
    assert state["presets"][2][1] == "AMBER_HIGH", "Pad 3 back to AMBER"
    print(f"  FX0 pad 3 third press → bank 1, preset=3 ✓")


def test_fx_disable():
    print("\n=== FX Disable Tests ===")
    grid = MockGrid()
    pm = PerformanceMode(grid, MockController(), osc_bridge=None)
    pm.enter()
    pm._render()

    pm._handle_fx_press("GTR", 1, pm._fx_preset_row(0))
    pm._render()
    assert pm._fx_enabled["GTR"][0] is True

    pm._handle_fx_press("GTR", 1, pm._fx_disable_row(0))
    pm._render()
    assert pm._fx_enabled["GTR"][0] is False, "Disable press should disable FX"
    state = grid.dump_fx("GTR", 0)
    assert state["disable"][0][1] == "RED_MED", "Disable row should be RED_MED when disabled"
    print(f"  FX0 disable → disabled ✓")

    for p in range(3):
        assert grid.get(CHANNELS["GTR"]["fx_start"] + p, pm._fx_preset_row(0)) == LogicalColor.OFF, \
            f"Preset pad {p} should be OFF when disabled"

    pm._handle_fx_press("GTR", 2, pm._fx_preset_row(0))
    pm._render()
    assert pm._fx_enabled["GTR"][0] is True, "Preset press should re-enable disabled FX"
    assert pm._fx_presets["GTR"][0] == 2
    print(f"  FX0 preset re-enable from disabled → enabled, preset=2 ✓")


def test_volume_mapping():
    print("\n=== Volume Mapping Tests ===")
    grid = MockGrid()
    pm = PerformanceMode(grid, MockController(), osc_bridge=None)

    tests = [
        (7, False, 32, "Pad 7 first → 32"),
        (7, True, 31, "Pad 7 second → 31"),
        (6, False, 30, "Pad 6 first → 30"),
        (6, True, 29, "Pad 6 second → 29"),
        (4, False, 26, "Pad 4 first → 26"),
        (4, True, 25, "Pad 4 second → 25"),
        (1, False, 20, "Pad 1 first → 20"),
        (1, True, 19, "Pad 1 second → 19"),
        (0, False, 18, "Pad 0 first → 18"),
        (0, True, 0, "Pad 0 second → 0 (mute)"),
    ]

    for pad, sub, expected, desc in tests:
        result = pm._pad_to_volume(pad, sub)
        assert result == expected, f"{desc}: expected {expected}, got {result}"
        print(f"  {desc} ✓")

    for vol, (exp_pad, exp_sub) in {
        32: (7, False),
        31: (7, True),
        30: (6, False),
        29: (6, True),
        26: (4, False),
        25: (4, True),
        20: (1, False),
        19: (1, True),
        18: (0, False),
        17: (0, False),
        0: (0, True),
    }.items():
        pad, sub = pm._volume_to_pad(vol)
        assert pad == exp_pad and sub == exp_sub, f"Vol {vol}: expected ({exp_pad},{exp_sub}), got ({pad},{sub})"


def test_fx_row_layout():
    print("\n=== FX Row Layout Tests ===")
    pm = PerformanceMode.__new__(PerformanceMode)

    assert pm._fx_preset_row(0) == 7, f"Delay preset row should be 7 (top), got {pm._fx_preset_row(0)}"
    assert pm._fx_disable_row(0) == 6, f"Delay disable row should be 6, got {pm._fx_disable_row(0)}"
    assert pm._fx_preset_row(1) == 5, f"Harmony preset row should be 5, got {pm._fx_preset_row(1)}"
    assert pm._fx_disable_row(1) == 4
    assert pm._fx_preset_row(2) == 3
    assert pm._fx_disable_row(2) == 2
    assert pm._fx_preset_row(3) == 1, f"Tremolo preset row should be 1, got {pm._fx_preset_row(3)}"
    assert pm._fx_disable_row(3) == 0, f"Tremolo disable row should be 0 (bottom), got {pm._fx_disable_row(3)}"
    print(f"  Delay: rows 7/6 ✓")
    print(f"  Harmony: rows 5/4 ✓")
    print(f"  Amp&Drv: rows 3/2 ✓")
    print(f"  Tremolo: rows 1/0 ✓")


def test_independent_channels():
    print("\n=== Independent Channel Tests ===")
    grid = MockGrid()
    pm = PerformanceMode(grid, MockController(), osc_bridge=None)
    pm.enter()
    pm._render()

    pm._handle_volume_press("GTR", 7)
    pm._handle_volume_press("VOX", 2)
    pm._render()
    assert pm._volumes["GTR"] == 32, f"GTR should be 32, got {pm._volumes['GTR']}"
    assert pm._volumes["VOX"] == 22, f"VOX should be 22, got {pm._volumes['VOX']}"
    print(f"  GTR=32, VOX=22 ✓")

    pm._handle_fx_press("GTR", 1, pm._fx_preset_row(0))
    pm._render()
    assert pm._fx_enabled["GTR"][0] is True
    assert pm._fx_enabled["VOX"][0] is False, "VOX Delay should still be disabled"
    print(f"  GTR Delay enabled, VOX Delay still disabled ✓")


if __name__ == "__main__":
    test_volume_mapping()
    test_fx_row_layout()
    test_volume_press()
    test_volume_mute()
    test_fx_preset()
    test_fx_disable()
    test_independent_channels()
    print("\n✅ ALL TESTS PASSED")
