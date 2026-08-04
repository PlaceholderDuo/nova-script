"""Test multi-button combo detection logic."""
import time


class ComboDetector:
    """Detects multi-button combos on the control row."""

    def __init__(self, combo_window_ms: int = 250):
        self._combo_window_ms = combo_window_ms
        self._held: dict[int, float] = {}
        self._pending_home = False
        self._home_press_time = 0.0
        self._combo_fired = False
        self._combo_partner: int | None = None

    def feed(self, control_id: int, pressed: bool) -> str | None:
        """Returns: None (normal), 'home', 'screensaver', 'fireworks', or 'consumed'."""
        if pressed:
            self._held[control_id] = time.monotonic()

            if control_id == 200:
                self._pending_home = True
                self._home_press_time = time.monotonic()
                return "consumed"

            if self._held.get(200) is not None:
                if control_id == 201:
                    self._pending_home = False
                    self._combo_fired = True
                    self._combo_partner = 201
                    return "screensaver"
                elif control_id == 202:
                    self._pending_home = False
                    self._combo_fired = True
                    self._combo_partner = 202
                    return "fireworks"

            return None
        else:
            self._held.pop(control_id, None)

            if control_id == 200:
                self._pending_home = False
                if self._combo_fired:
                    return "consumed"
                return "home"

            if self._combo_fired and control_id == self._combo_partner:
                if len(self._held) == 0:
                    self._combo_fired = False
                    self._combo_partner = None
                return "consumed"

            return None

    def tick(self) -> str | None:
        """Call periodically. Returns 'home' if combo window expired."""
        if self._pending_home:
            elapsed = (time.monotonic() - self._home_press_time) * 1000
            if elapsed >= self._combo_window_ms:
                self._pending_home = False
                return "home"
        return None


def test():
    print("=== UNIT TEST: Combo Detection ===\n")

    # Scenario 1: Top-1 alone → Home on release
    d = ComboDetector()
    r = d.feed(200, True)
    assert r == "consumed", f"Expected 'consumed', got {r}"
    r = d.feed(200, False)
    assert r == "home", f"Expected 'home', got {r}"
    assert d.tick() is None
    print("  ✓ Scenario 1: Top-1 press+release → Home")

    # Scenario 2: Top-1+2 → Screensaver (combo fires immediately)
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

    # Scenario 3: Top-1+3 → Fireworks
    d = ComboDetector()
    d.feed(200, True)
    r = d.feed(202, True)
    assert r == "fireworks"
    print("  ✓ Scenario 3: Top-1+3 → Fireworks")

    # Scenario 4: Top-1 held too long (tick timeout) → Home
    d = ComboDetector(combo_window_ms=100)
    r = d.feed(200, True)
    assert r == "consumed"
    # Simulate time passing
    d._home_press_time -= 0.2
    r = d.tick()
    assert r == "home", f"Expected 'home', got {r}"
    print("  ✓ Scenario 4: Top-1 hold timeout → Home")

    # Scenario 5: Top-1 pressed, then Top-2 pressed AFTER Top-1 released → No combo
    d = ComboDetector()
    d.feed(200, True)
    d.feed(200, False)  # Top-1 released before combo
    r = d.feed(201, True)  # Top-2 now pressed alone
    assert r is None, f"Expected None (no combo), got {r}"
    print("  ✓ Scenario 5: Late Top-2 (Top-1 already released) → no combo")

    # Scenario 6: Non-combo button while Top-1 held → consumed, no combo
    d = ComboDetector()
    d.feed(200, True)
    r = d.feed(205, True)  # Top-6, not a combo button
    assert r is None
    r = d.feed(200, False)
    assert r == "home"  # Top-1 release is still Home!
    print("  ✓ Scenario 6: Non-combo button during Top-1 hold → ignored, Top-1 → Home")

    # Scenario 7: Top-2 alone (no Top-1 held) → normal
    d = ComboDetector()
    r = d.feed(201, True)
    assert r is None, f"Expected None (normal), got {r}"
    print("  ✓ Scenario 7: Top-2 alone → normal event")

    print("\n=== ALL TESTS PASSED ===")


if __name__ == "__main__":
    test()
