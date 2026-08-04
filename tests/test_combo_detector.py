"""Combo detector unit tests."""
from src.ui.combo_detector import ComboDetector


def test():
    print("=== UNIT TEST: Combo Detection ===\n")

    d = ComboDetector()
    r = d.feed(200, True)
    assert r == "consumed", f"Expected 'consumed', got {r}"
    r = d.feed(200, False)
    assert r == "home", f"Expected 'home', got {r}"
    assert d.tick() is None
    print("  ✓ Scenario 1: Top-1 press+release → Home")

    d = ComboDetector()
    r = d.feed(200, True)
    assert r == "consumed"
    r = d.feed(201, True)
    assert r == "screensaver"
    r = d.feed(200, False)
    assert r == "consumed", f"Expected 'consumed' (combo already fired), got {r}"
    r = d.feed(201, False)
    assert r == "consumed", f"Expected 'consumed', got {r}"
    print("  ✓ Scenario 2: Top-1+2 → Screensaver")

    d = ComboDetector()
    d.feed(200, True)
    r = d.feed(202, True)
    assert r == "fireworks"
    print("  ✓ Scenario 3: Top-1+3 → Fireworks")

    d = ComboDetector(combo_window_ms=100)
    r = d.feed(200, True)
    assert r == "consumed"
    d._home_press_time -= 0.2
    r = d.tick()
    assert r == "home", f"Expected 'home', got {r}"
    print("  ✓ Scenario 4: Top-1 hold timeout → Home")

    d = ComboDetector()
    d.feed(200, True)
    d.feed(200, False)
    r = d.feed(201, True)
    assert r is None, f"Expected None (no combo), got {r}"
    print("  ✓ Scenario 5: Late Top-2 after Top-1 release → no combo")

    d = ComboDetector()
    d.feed(200, True)
    r = d.feed(205, True)
    assert r is None
    r = d.feed(200, False)
    assert r == "home"
    print("  ✓ Scenario 6: Non-combo button → ignored, Top-1 → Home")

    d = ComboDetector()
    r = d.feed(201, True)
    assert r is None, f"Expected None (normal), got {r}"
    print("  ✓ Scenario 7: Top-2 alone → normal event")

    print("\n=== ALL TESTS PASSED ===")


if __name__ == "__main__":
    test()
