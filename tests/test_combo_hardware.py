"""Hardware test: multi-button combo detection on Launchpad Mini MK1."""
import asyncio
import time
from scripts.test_harness import TestHarness
from src.controllers.color_map import LogicalColor


class HardwareComboDetector:
    def __init__(self, combo_window_ms: int = 250):
        self._combo_window_ms = combo_window_ms
        self._held: dict[int, float] = {}
        self._pending_home = False
        self._home_press_time = 0.0
        self._combo_fired = False
        self._combo_partner: int | None = None
        self._events: list[str] = []

    def feed(self, control_id: int, pressed: bool) -> str | None:
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


async def main():
    h = TestHarness()
    await h.connect()

    detector = HardwareComboDetector()
    original = h.lp._on_control_event

    # Light top-1 amber so you know which one it is
    h.lp.send_top_row_led(0, LogicalColor.AMBER_HIGH)

    def ctrl_cb(event):
        result = detector.feed(event.control_id, event.pressed)
        label = f"id={event.control_id} press={event.pressed}"
        if result:
            print(f"  >>> {label} → {result.upper()}")
        else:
            print(f"       {label}")

    h.lp._on_control_event = ctrl_cb

    print()
    print("Top-1 lit AMBER. Test these combos:")
    print("  1. Press Top-1 alone → should say HOME")
    print("  2. Hold Top-1, then press Top-2 → should say SCREENSAVER")
    print("  3. Hold Top-1, then press Top-3 → should say FIREWORKS")
    print("  4. Press Top-2 alone → should show normal press")
    print()
    print("Testing for 20 seconds...")
    print()

    await asyncio.sleep(20)

    h.lp._on_control_event = original
    h.lp.clear_grid()
    await h.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
