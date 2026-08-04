#!/usr/bin/env python
"""
Nova-Script interactive test harness.
Connect to Launchpad and run test patterns step by step.

Usage: python scripts/test_harness.py
"""
import asyncio
import logging
import readline
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)

from src.controllers.launchpad_mk1 import LaunchpadMiniMK1
from src.controllers.color_map import LogicalColor
from src.midi.manager import MidiManager


class TestHarness:
    def __init__(self):
        self.midi = MidiManager(poll_interval=0.5)
        self.lp = LaunchpadMiniMK1(self.midi)

    async def connect(self):
        self.midi.register_device("Launchpad Mini", self.lp.handle_raw_midi)
        await self.midi.start()
        await asyncio.sleep(0.5)
        if self.midi.devices["Launchpad Mini"].connected:
            self.lp.on_connect()
            print("✓ Launchpad connected")
            self._bg_task = asyncio.create_task(self._dispatch_loop())
            return True
        else:
            print("✗ Launchpad NOT found")
            return False

    async def _dispatch_loop(self):
        queue = self.midi.event_queue
        while True:
            try:
                event_data = await asyncio.wait_for(queue.get(), timeout=0.05)
                device_name, message, timestamp = event_data[0], event_data[1], event_data[2]
                if device_name in self.midi.devices and self.midi.devices[device_name].connected:
                    self.lp.handle_raw_midi(message)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def disconnect(self):
        if hasattr(self, '_bg_task'):
            self._bg_task.cancel()
            try:
                await self._bg_task
            except:
                pass
        self.lp.clear_grid()
        self.lp.reset()
        await self.midi.stop()
        print("Disconnected")

    def set_led(self, x, y, color_name):
        """Set a grid pad LED. x=0-7 (0=left), y=0-7 (0=bottom)."""
        try:
            color = LogicalColor[color_name.upper()]
        except KeyError:
            print(f"Unknown color: {color_name}. Use: OFF, RED_LOW/MED/HIGH, GREEN_LOW/MED/HIGH, AMBER_LOW/MED/HIGH")
            return False
        self.lp.set_grid_color(x, y, color)
        print(f"LED ({x},{y}) → {color.name}")
        return True

    def set_top_led(self, index, color_name):
        """Set a top row circular button LED. index 0-7 (0=leftmost)."""
        try:
            color = LogicalColor[color_name.upper()]
        except KeyError:
            print(f"Unknown color: {color_name}")
            return False
        self.lp.send_top_row_led(index, color)
        print(f"Top LED [{index}] → {color.name}")
        return True

    def set_right_led(self, index, color_name):
        """Set a right column circular button LED. index 0-7 (0=topmost)."""
        try:
            color = LogicalColor[color_name.upper()]
        except KeyError:
            print(f"Unknown color: {color_name}")
            return False
        self.lp.send_right_column_led(index, color)
        print(f"Right LED [{index}] → {color.name}")
        return True

    def clear(self):
        self.lp.clear_grid()
        print("Grid cleared")

    def fill(self, color_name):
        try:
            color = LogicalColor[color_name.upper()]
        except KeyError:
            print(f"Unknown color: {color_name}")
            return
        for y in range(8):
            for x in range(8):
                self.lp.set_grid_color(x, y, color)

    def cross(self, color_name):
        try:
            color = LogicalColor[color_name.upper()]
        except KeyError:
            print(f"Unknown color: {color_name}")
            return
        self.lp.clear_grid()
        for i in range(8):
            self.lp.set_grid_color(i, i, color)
            self.lp.set_grid_color(i, 7 - i, color)

    def border(self, color_name):
        try:
            color = LogicalColor[color_name.upper()]
        except KeyError:
            print(f"Unknown color: {color_name}")
            return
        self.lp.clear_grid()
        for x in range(8):
            self.lp.set_grid_color(x, 0, color)
            self.lp.set_grid_color(x, 7, color)
        for y in range(1, 7):
            self.lp.set_grid_color(0, y, color)
            self.lp.set_grid_color(7, y, color)

    def all_outer(self, color_name):
        """Light all outer circular buttons (top row + right column)."""
        try:
            color = LogicalColor[color_name.upper()]
        except KeyError:
            print(f"Unknown color: {color_name}")
            return
        for i in range(8):
            self.lp.send_top_row_led(i, color)
            self.lp.send_right_column_led(i, color)

    def chase_top(self, delay=0.1, loops=3):
        """Chase animation on top row buttons."""
        for _ in range(loops):
            for i in range(8):
                self.lp.send_top_row_led(i, LogicalColor.AMBER_HIGH)
                if i > 0:
                    self.lp.send_top_row_led(i - 1, LogicalColor.OFF)
                time.sleep(delay)
            self.lp.send_top_row_led(7, LogicalColor.OFF)

    def chase_right(self, delay=0.1, loops=3):
        """Chase animation on right column buttons."""
        for _ in range(loops):
            for i in range(8):
                self.lp.send_right_column_led(i, LogicalColor.AMBER_HIGH)
                if i > 0:
                    self.lp.send_right_column_led(i - 1, LogicalColor.OFF)
                time.sleep(delay)
            self.lp.send_right_column_led(7, LogicalColor.OFF)

    def chase_grid(self, delay=0.05, loops=2):
        """Chase animation around the outer grid border."""
        for _ in range(loops):
            border = []
            for x in range(8):
                border.append((x, 0))
            for y in range(1, 8):
                border.append((7, y))
            for x in range(6, -1, -1):
                border.append((x, 7))
            for y in range(6, 0, -1):
                border.append((0, y))

            trail = []
            for x, y in border:
                self.lp.set_grid_color(x, y, LogicalColor.AMBER_HIGH)
                trail.append((x, y))
                if len(trail) > 3:
                    ox, oy = trail.pop(0)
                    self.lp.set_grid_color(ox, oy, LogicalColor.OFF)
                time.sleep(delay)
            self.lp.clear_grid()

    def cycle_colors(self, x, y, delay=0.5, loops=2):
        """Cycle a pad through available colors."""
        colors = [
            LogicalColor.GREEN_HIGH,
            LogicalColor.RED_HIGH,
            LogicalColor.AMBER_HIGH,
            LogicalColor.GREEN_MED,
            LogicalColor.RED_MED,
            LogicalColor.AMBER_MED,
            LogicalColor.OFF,
        ]
        for _ in range(loops):
            for c in colors:
                self.lp.set_grid_color(x, y, c)
                time.sleep(delay)

    def smiley(self):
        """Draw a smiley face pattern."""
        self.lp.clear_grid()
        pattern = [
            (2, 6), (5, 6),                # eyes
            (1, 3), (6, 3),                # cheeks
            (2, 2), (3, 2), (4, 2), (5, 2),  # mouth
        ]
        for x, y in pattern:
            self.lp.set_grid_color(x, y, LogicalColor.AMBER_HIGH)

    def heart(self):
        """Draw a heart pattern."""
        self.lp.clear_grid()
        pattern = [
            (1, 6), (2, 6), (5, 6), (6, 6),
            (0, 5), (1, 5), (2, 5), (5, 5), (6, 5), (7, 5),
            (0, 4), (1, 4), (2, 4), (3, 4), (4, 4), (5, 4), (6, 4), (7, 4),
            (1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (6, 3),
            (2, 2), (3, 2), (4, 2), (5, 2),
            (3, 1), (4, 1),
        ]
        for x, y in pattern:
            self.lp.set_grid_color(x, y, LogicalColor.RED_HIGH)

    async def check_buttons(self, timeout=10):
        """Monitor button presses and print them."""
        printed = []
        original_grid = self.lp._on_grid_event
        original_ctrl = self.lp._on_control_event

        def grid_cb(event):
            msg = f"GRID: ({event.x},{event.y}) pressed={event.pressed} vel={event.velocity}"
            printed.append(msg)
            print(f"  >>> {msg}")

        def ctrl_cb(event):
            msg = f"CTRL: id={event.control_id} type={event.event_type.name} val={event.value}"
            printed.append(msg)
            print(f"  >>> {msg}")

        self.lp._on_grid_event = grid_cb
        self.lp._on_control_event = ctrl_cb

        print(f"Monitoring button presses for {timeout}s... Press Launchpad buttons!")
        try:
            await asyncio.sleep(timeout)
        except KeyboardInterrupt:
            pass
        finally:
            self.lp._on_grid_event = original_grid
            self.lp._on_control_event = original_ctrl
        print(f"Button monitor stopped ({len(printed)} events)")


async def interactive():
    h = TestHarness()
    if not await h.connect():
        return

    print("\n" + "=" * 60)
    print("  Nova-Script Test Harness")
    print("  Launchpad Mini MK1 connected")
    print("=" * 60)
    print()
    print("  Available commands (type as Python):")
    print("    h.set_led(x, y, 'color')       — Light a grid pad")
    print("    h.set_top_led(idx, 'color')     — Light top circular button")
    print("    h.set_right_led(idx, 'color')   — Light right circular button")
    print("    h.clear()                       — Clear all LEDs")
    print("    h.fill('color')                 — Fill entire grid")
    print("    h.cross('color')                — Draw X pattern")
    print("    h.border('color')               — Draw border")
    print("    h.all_outer('color')            — Light all outer buttons")
    print("    h.smiley()                      — Draw smiley")
    print("    h.heart()                       — Draw heart")
    print("    h.chase_top(0.1, 3)            — Chase on top row")
    print("    h.chase_right(0.1, 3)          — Chase on right column")
    print("    h.chase_grid(0.05, 2)          — Chase on grid border")
    print("    h.cycle_colors(0, 0, 0.5, 2)   — Cycle colors on a pad")
    print("    await h.check_buttons(10)       — Monitor button presses")
    print()
    print("  Colors: OFF, RED_LOW/MED/HIGH, GREEN_LOW/MED/HIGH,")
    print("          AMBER_LOW/MED/HIGH")
    print()
    print("  Type Python commands. 'await' for async. Ctrl+D to exit.")
    print()

    try:
        while True:
            try:
                cmd = input(">>> ")
                if not cmd.strip():
                    continue
                if cmd.strip().startswith("await "):
                    coro = eval(cmd[6:].strip(), {"h": h, "result": None})
                    result = await coro
                else:
                    exec(cmd, {"h": h, "result": None, "time": time, "LogicalColor": LogicalColor})
                print()
            except EOFError:
                break
            except Exception as e:
                print(f"Error: {e}\n")
    finally:
        await h.disconnect()


if __name__ == "__main__":
    asyncio.run(interactive())
