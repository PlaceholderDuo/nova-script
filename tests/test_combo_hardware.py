import asyncio
import time
from scripts.test_harness import TestHarness
from src.controllers.color_map import LogicalColor
from src.ui.combo_detector import ComboDetector


class HardwareComboDetector:
    """Wraps ComboDetector with print output for hardware testing."""
    def __init__(self):
        self._detector = ComboDetector()

    def feed(self, control_id, pressed):
        result = self._detector.feed(control_id, pressed)
        return result


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
