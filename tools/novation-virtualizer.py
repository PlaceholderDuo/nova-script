#!/usr/bin/env python3
"""
Novation Hardware Virtualizer
Simulates Novation controllers for development without hardware.
Creates virtual MIDI ports that nova-script connects to.
WebSocket server bridges visual UI <-> virtual MIDI.
"""

import asyncio
import json
import logging
import signal
import sys

import rtmidi
import websockets
from websockets.asyncio.server import serve

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("virtualizer")

# ── Color tables ────────────────────────────────────────────────────────────

MK1_VELOCITY_TO_COLOR: dict[int, str] = {
    0: "OFF",
    1: "RED_LOW", 2: "RED_MED", 3: "RED_HIGH",
    16: "GREEN_LOW", 32: "GREEN_MED", 48: "GREEN_HIGH",
    17: "AMBER_LOW", 34: "AMBER_MED", 51: "AMBER_HIGH",
    33: "ORANGE_MED", 50: "YELLOW_MED",
}

LK_PALETTE_TO_COLOR: dict[int, str] = {
    0: "OFF",
    1: "WHITE_LOW", 2: "WHITE_MED", 3: "WHITE_HIGH",
    5: "RED_LOW", 6: "RED_MED", 7: "RED_HIGH",
    9: "AMBER_LOW", 10: "AMBER_MED", 11: "AMBER_HIGH",
    13: "YELLOW_LOW", 14: "YELLOW_MED", 15: "YELLOW_HIGH",
    17: "GREEN_LOW", 18: "GREEN_MED", 19: "GREEN_HIGH",
    21: "GREEN_LOW", 22: "GREEN_MED", 23: "GREEN_HIGH",
    33: "CYAN_LOW", 34: "CYAN_MED", 35: "CYAN_HIGH",
    41: "BLUE_LOW", 42: "BLUE_MED", 43: "BLUE_HIGH",
    49: "PURPLE_LOW", 50: "PURPLE_MED", 51: "PURPLE_HIGH",
}

# LED-accurate RGB approximations for each LogicalColor
# Calibrated against MK1 Launchpad Mini hardware:
#   Red LED ~625nm through silicone diffuser → warm red-orange
#   Green LED ~525nm through diffuser → vivid lime-green
#   Amber = both LEDs on simultaneously → golden amber through diffuser
COLOR_TO_LED_RGB: dict[str, tuple[int, int, int]] = {
    "OFF": (42, 42, 44),
    "RED_LOW": (90, 10, 0), "RED_MED": (165, 22, 3), "RED_HIGH": (245, 38, 8),
    "GREEN_LOW": (0, 92, 6), "GREEN_MED": (2, 165, 14), "GREEN_HIGH": (8, 248, 25),
    "AMBER_LOW": (90, 50, 0), "AMBER_MED": (168, 98, 5), "AMBER_HIGH": (248, 158, 14),
    "ORANGE_LOW": (85, 38, 0), "ORANGE_MED": (160, 72, 3), "ORANGE_HIGH": (248, 125, 8),
    "YELLOW_LOW": (80, 70, 0), "YELLOW_MED": (150, 135, 3), "YELLOW_HIGH": (248, 228, 8),
    "WHITE_LOW": (80, 75, 70), "WHITE_MED": (150, 145, 138), "WHITE_HIGH": (248, 248, 240),
    "BLUE_LOW": (0, 5, 75), "BLUE_MED": (0, 12, 148), "BLUE_HIGH": (5, 20, 248),
    "PURPLE_LOW": (58, 0, 58), "PURPLE_MED": (125, 3, 125), "PURPLE_HIGH": (235, 5, 235),
    "CYAN_LOW": (0, 60, 60), "CYAN_MED": (3, 128, 128), "CYAN_HIGH": (5, 242, 242),
}


def color_to_rgb(name: str) -> tuple[int, int, int]:
    return COLOR_TO_LED_RGB.get(name, (58, 58, 58))


# ── Device profiles ─────────────────────────────────────────────────────────

DEVICE_PROFILES = {
    "Launchpad Mini MK1": {
        "grid_w": 8, "grid_h": 8, "has_rgb": False, "has_velocity": False,
        "function_row": True, "function_col": True,
        "num_knobs": 0, "num_faders": 0, "has_transport": False,
        "port_name": "Launchpad Mini",
        "protocol": "mk1",
        "row_cc": 0x68,
        "col_notes": [8, 24, 40, 56, 72, 88, 104, 120],
        "top_labels": ["HOME", "Perf", "Clip", "Seq", "Mixer", "Page◀", "Page▶", "Rec"],
        "right_labels": ["A", "B", "C", "D", "E", "F", "G", "H"],
        "device_brand": "Launchpad Mini",
        "model_line": "MK1",
    },
    "Launchpad MK1": {
        "grid_w": 8, "grid_h": 8, "has_rgb": False, "has_velocity": False,
        "function_row": True, "function_col": True,
        "num_knobs": 0, "num_faders": 0, "has_transport": False,
        "port_name": "Launchpad MK1",
        "protocol": "mk1",
        "row_cc": 0x68,
        "col_notes": [8, 24, 40, 56, 72, 88, 104, 120],
        "top_labels": ["⬆", "⬇", "⬅", "➡", "Session", "User 1", "User 2", "Mixer"],
        "right_labels": ["Vol", "Pan", "SndA", "SndB", "Stop", "Trk▶", "Solo", "Arm"],
        "device_brand": "Launchpad",
        "model_line": "MK1",
    },
    "Launchpad Mini MK3": {
        "grid_w": 8, "grid_h": 8, "has_rgb": True, "has_velocity": True,
        "function_row": True, "function_col": True,
        "num_knobs": 0, "num_faders": 0, "has_transport": False,
        "port_name": "Launchpad Mini MK3",
        "protocol": "mk3",
        "row_cc": 0x68,
        "col_notes": [8, 24, 40, 56, 72, 88, 104, 120],
        "top_labels": ["Note", "Chord", "Custom", "", "", "▲", "▼", "Scale"],
        "right_labels": ["", "", "", "", "", "", "", ""],
        "device_brand": "Launchpad Mini",
        "model_line": "MK3",
        "extra_buttons": ["Session", "Note", "Custom", "◀", "▲", "▼", "▶", "Capture", "Quantise"],
    },
    "Launchpad Pro MK3": {
        "grid_w": 8, "grid_h": 8, "has_rgb": True, "has_velocity": True,
        "function_row": True, "function_col": True, "function_col_left": True,
        "num_knobs": 0, "num_faders": 0, "has_transport": False,
        "port_name": "Launchpad Pro MK3",
        "protocol": "mk3",
        "row_cc": 0x68,
        "col_notes": [8, 24, 40, 56, 72, 88, 104, 120],
        "top_labels": ["Note", "Chord", "Custom", "Seq", "Track◀", "Track▶", "Record", "Play"],
        "right_labels": ["", "", "", "", "", "", "", ""],
        "left_labels": ["", "", "", "", "", "", "", ""],
        "device_brand": "Launchpad Pro",
        "model_line": "MK3",
        "extra_buttons": ["Session", "Note", "Custom", "◀", "▲", "▼", "▶", "Capture", "Quantise", "◼", "▶"],
    },
    "Launchkey 49 MK2": {
        "grid_w": 8, "grid_h": 2, "has_rgb": True, "has_velocity": True,
        "function_row": False, "function_col": False,
        "num_knobs": 8, "num_faders": 9, "has_transport": True,
        "port_name": "Launchkey 49",
        "protocol": "launchkey",
        "pad_notes": [96, 97, 98, 99, 100, 101, 102, 103,
                      112, 113, 114, 115, 116, 117, 118, 119],
        "knob_cc": [21, 22, 23, 24, 25, 26, 27, 28],
        "fader_cc": [41, 42, 43, 44, 45, 46, 47, 48],
        "master_fader_cc": 7,
        "transport_cc": [112, 113, 114, 115, 116, 117, 102, 103],
        "transport_labels": ["◀◀", "▶▶", "◼", "▶", "↺", "●", "Tr◀", "Tr▶"],
        "led_channel": 0x9F,
        "device_brand": "Launchkey 49",
        "model_line": "MK2",
    },
}

# ── VirtualDevice ───────────────────────────────────────────────────────────

class VirtualDevice:
    def __init__(self, profile_key: str):
        p = DEVICE_PROFILES[profile_key]
        self.profile_key = profile_key
        self.profile = p
        self.grid = [["OFF"] * p["grid_w"] for _ in range(p["grid_h"])]
        self.top_row = ["OFF"] * 8 if p["function_row"] else []
        self.right_col = ["OFF"] * 8 if p["function_col"] else []
        self.left_col = ["OFF"] * 8 if p.get("function_col_left") else []
        self.connected = False
        self.mode_name: str = ""
        self.page_name: str = ""
        self.subpage_name: str = ""
        self._midi_in: rtmidi.MidiIn | None = None
        self._midi_out: rtmidi.MidiOut | None = None

    @property
    def port_name(self):
        return self.profile["port_name"]

    def _cmd_from_grid_pos(self, note: int) -> tuple[int, int] | None:
        p = self.profile
        if p["protocol"] == "launchkey":
            if note in p["pad_notes"]:
                idx = p["pad_notes"].index(note)
                return (idx % p["grid_w"], p["grid_h"] - 1 - idx // p["grid_w"])
            return None
        x = note % 16
        y = p["grid_h"] - 1 - note // 16
        if 0 <= x < p["grid_w"] and 0 <= y < p["grid_h"]:
            return (x, y)
        return None

    def _grid_pos_to_cmd(self, x: int, y: int) -> int:
        p = self.profile
        if p["protocol"] == "launchkey":
            return p["pad_notes"][(p["grid_h"] - 1 - y) * p["grid_w"] + x]
        return (p["grid_h"] - 1 - y) * 16 + x

    def _hardware_to_color(self, val: int, palette: bool = False) -> str:
        if palette:
            return LK_PALETTE_TO_COLOR.get(val, "OFF")
        return MK1_VELOCITY_TO_COLOR.get(val, "OFF")

    def connect_midi(self):
        if self._midi_in:
            return
        try:
            self._midi_in = rtmidi.MidiIn()
            self._midi_out = rtmidi.MidiOut()
            self._midi_in.open_virtual_port(self.port_name)
            self._midi_out.open_virtual_port(self.port_name)
            self.connected = True
            log.info(f"Virtual MIDI ports: '{self.port_name}' (in+out)")
        except Exception as e:
            log.error(f"MIDI port creation failed: {e}")
            if self._midi_in:
                self._midi_in.close_port()
            self._midi_in = None
            self._midi_out = None

    def disconnect_midi(self):
        if self._midi_in:
            self._midi_in.close_port()
            self._midi_in = None
        if self._midi_out:
            self._midi_out.close_port()
            self._midi_out = None
        self.connected = False
        log.info(f"Virtual MIDI ports closed: '{self.port_name}'")

    def handle_midi_in(self, msg: list[int]):
        if len(msg) < 3:
            return
        status, d1, d2 = msg[0], msg[1], msg[2]
        p = self.profile
        ch = status & 0x0F
        typ = status & 0xF0

        if p["protocol"] == "launchkey" and ch == 15 and typ == 0x90:
            xy = self._cmd_from_grid_pos(d1)
            if xy:
                self.grid[xy[1]][xy[0]] = self._hardware_to_color(d2, palette=True)

        elif p["protocol"] in ("mk1", "mk3") and ch == 0:
            if typ == 0x90:
                col_notes = p.get("col_notes", [])
                if d1 in col_notes:
                    self.right_col[col_notes.index(d1)] = self._hardware_to_color(d2)
                else:
                    xy = self._cmd_from_grid_pos(d1)
                    if xy:
                        self.grid[xy[1]][xy[0]] = self._hardware_to_color(d2)
            elif typ == 0xB0:
                if d1 == 0x00:
                    self.clear()
                elif p.get("row_cc", 0x68) <= d1 < p.get("row_cc", 0x68) + 8:
                    self.top_row[d1 - p["row_cc"]] = self._hardware_to_color(d2)

    def _send_press_release(self, msg_factory):
        if not self._midi_out:
            return
        self._midi_out.send_message(msg_factory(127))
        self._midi_out.send_message(msg_factory(0))

    def simulate_press(self, x: int, y: int):
        note = self._grid_pos_to_cmd(x, y)
        self._send_press_release(lambda v: [0x90, note, v])

    def simulate_top_row(self, index: int):
        cc = self.profile.get("row_cc", 0x68) + index
        self._send_press_release(lambda v: [0xB0, cc, v])

    def simulate_right_col(self, index: int):
        note = self.profile.get("col_notes", [])[index]
        self._send_press_release(lambda v: [0x90, note, v])

    def simulate_left_col(self, index: int):
        pass

    def simulate_knob(self, index: int, value: int):
        if not self._midi_out:
            return
        self._midi_out.send_message([0xB0, self.profile["knob_cc"][index], value])

    def simulate_fader(self, index: int, value: int):
        if not self._midi_out:
            return
        cc = self.profile["master_fader_cc"] if index >= 8 else self.profile["fader_cc"][index]
        self._midi_out.send_message([0xB0, cc, value])

    def simulate_transport(self, index: int):
        cc = self.profile["transport_cc"][index]
        self._send_press_release(lambda v: [0xB0, cc, v])

    def clear(self):
        p = self.profile
        self.grid = [["OFF"] * p["grid_w"] for _ in range(p["grid_h"])]
        self.top_row = ["OFF"] * len(self.top_row)
        self.right_col = ["OFF"] * len(self.right_col)
        self.left_col = ["OFF"] * len(self.left_col)

    def state_dict(self):
        p = self.profile

        def colors_for(arr):
            return [[color_to_rgb(c) for c in row] for row in arr] if arr and isinstance(arr[0], list) else [list(color_to_rgb(c)) for c in arr]

        return {
            "type": self.profile_key,
            "grid_w": p["grid_w"],
            "grid_h": p["grid_h"],
            "grid": self.grid,
            "grid_rgb": [[list(color_to_rgb(c)) for c in row] for row in self.grid],
            "top_row": list(self.top_row),
            "top_rgb": [list(color_to_rgb(c)) for c in self.top_row],
            "right_col": list(self.right_col),
            "right_rgb": [list(color_to_rgb(c)) for c in self.right_col],
            "left_col": list(self.left_col),
            "left_rgb": [list(color_to_rgb(c)) for c in self.left_col],
            "has_rgb": p["has_rgb"],
            "has_velocity": p["has_velocity"],
            "function_row": p["function_row"],
            "function_col": p["function_col"],
            "function_col_left": p.get("function_col_left", False),
            "num_knobs": p["num_knobs"],
            "num_faders": p["num_faders"],
            "has_transport": p["has_transport"],
            "connected": self.connected,
            "top_labels": p.get("top_labels", []),
            "right_labels": p.get("right_labels", []),
            "left_labels": p.get("left_labels", []),
            "extra_buttons": p.get("extra_buttons", []),
            "transport_labels": p.get("transport_labels", []),
            "device_brand": p.get("device_brand", ""),
            "model_line": p.get("model_line", ""),
            "mode": self.mode_name,
            "page": self.page_name,
            "subpage": self.subpage_name,
        }


# ── Server ──────────────────────────────────────────────────────────────────

class VirtualizerServer:
    def __init__(self):
        self.device = VirtualDevice("Launchpad Mini MK1")
        self.clients: set = set()
        self._running = False
        self._server = None

    def switch_device(self, profile_key: str):
        was_connected = self.device.connected
        self.device.disconnect_midi()
        self.device = VirtualDevice(profile_key)
        if was_connected:
            self.device.connect_midi()

    async def _midi_poll(self):
        while self._running:
            dev = self.device
            if dev._midi_in:
                msg = dev._midi_in.get_message()
                if msg:
                    dev.handle_midi_in(msg[0])
                    await self._broadcast_state()
            await asyncio.sleep(0.001)

    async def _broadcast_state(self):
        if not self.clients:
            return
        state = json.dumps(self.device.state_dict())
        dead = set()
        for ws in list(self.clients):
            try:
                await ws.send(state)
            except websockets.ConnectionClosed:
                dead.add(ws)
            except Exception:
                dead.add(ws)
        self.clients -= dead

    async def _ws_handler(self, ws):
        self.clients.add(ws)
        log.info(f"Browser connected ({len(self.clients)} total)")
        try:
            await ws.send(json.dumps(self.device.state_dict()))
            async for raw in ws:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                await self._handle_action(ws, data)
        except websockets.ConnectionClosed:
            pass
        finally:
            self.clients.discard(ws)
            log.info(f"Browser disconnected ({len(self.clients)} total)")

    async def _handle_action(self, ws, action: dict):
        d = self.device
        act = action.get("action", "")
        try:
            if act == "press_pad":
                d.simulate_press(action["x"], action["y"])
            elif act == "press_top":
                d.simulate_top_row(action["index"])
            elif act == "press_right":
                d.simulate_right_col(action["index"])
            elif act == "press_left":
                d.simulate_left_col(action["index"])
            elif act == "knob":
                d.simulate_knob(action["index"], action["value"])
            elif act == "fader":
                d.simulate_fader(action["index"], action["value"])
            elif act == "transport":
                d.simulate_transport(action["index"])
            elif act == "switch_device":
                self.switch_device(action["profile"])
            elif act == "connect":
                d.connect_midi()
            elif act == "disconnect":
                d.disconnect_midi()
            elif act == "clear":
                d.clear()
            elif act == "get_state":
                await ws.send(json.dumps(d.state_dict()))
                return
            elif act == "set_info":
                d.mode_name = action.get("mode", "")
                d.page_name = action.get("page", "")
                d.subpage_name = action.get("subpage", "")
        except Exception as e:
            log.error(f"Action '{act}' failed: {e}")
        await self._broadcast_state()

    async def run(self, port: int = 8766):
        self._running = True
        self.device.connect_midi()

        log.info(f"WebSocket server: ws://localhost:{port}")
        log.info(f"Open tools/novation-virtualizer.html in your browser")
        log.info(f"Virtual MIDI ports ready — nova-script can connect now")

        self._server = await serve(self._ws_handler, "localhost", port)
        midi_task = asyncio.create_task(self._midi_poll())
        try:
            await self._server.serve_forever()
        finally:
            self._running = False
            midi_task.cancel()
            self.device.disconnect_midi()

    async def shutdown(self):
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        self._running = False


def main():
    srv = VirtualizerServer()

    def shutdown_handler():
        srv.device.disconnect_midi()
        if srv._server:
            srv._server.close()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, shutdown_handler)
        except NotImplementedError:
            signal.signal(sig, lambda s, f: shutdown_handler())

    try:
        loop.run_until_complete(srv.run())
    except KeyboardInterrupt:
        pass
    finally:
        shutdown_handler()
        loop.close()


if __name__ == "__main__":
    main()
