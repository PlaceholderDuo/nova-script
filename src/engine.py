import asyncio
import logging
import time
from pathlib import Path
from queue import Queue
from typing import Optional

import yaml

from src.midi.manager import MidiManager
from src.controllers.launchpad_mk1 import LaunchpadMiniMK1
from src.controllers.launchkey_mk2 import Launchkey49MK2
from src.layout.grid import LogicalGrid
from src.ui.mode_manager import ModeManager
from src.ui.modes.menu import MenuMode
from src.ui.modes.sequencer import SequencerMode
from src.ui.modes.mixer import MixerMode
from src.ui.modes.message import MessageMode
from src.osc.bridge import OscBridge
from src.controllers.color_map import LogicalColor

logger = logging.getLogger(__name__)


class Engine:
    def __init__(self, config_path: Optional[Path] = None):
        self.config = self._load_config(config_path)
        self.midi_manager = MidiManager(poll_interval=0.5)
        self.grid = LogicalGrid(8, 8)
        self.mode_manager: Optional[ModeManager] = None
        self.controllers: dict[str, object] = {}
        self.osc: Optional[OscBridge] = None
        self._running = False
        self._last_tick = time.monotonic()
        self._idle_since = time.monotonic()
        self._tui_queue: Optional[Queue] = None
        self._idle_timeout_ms: int = 2000
        self._message_mode: Optional[MessageMode] = None

    def set_tui_queue(self, queue):
        self._tui_queue = queue

    @staticmethod
    def _load_config(config_path: Optional[Path]) -> dict:
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "default.yaml"

        if config_path.exists():
            with open(config_path) as f:
                return yaml.safe_load(f)

        logger.warning(f"Config not found at {config_path}, using defaults")
        return {}

    async def start(self):
        logger.info("Starting Nova-Script engine...")

        self._setup_controllers()
        await self.midi_manager.start()

        osc_config = self.config.get("osc", {})
        self.osc = OscBridge(
            listen_host=osc_config.get("listen_host", "127.0.0.1"),
            listen_port=osc_config.get("listen_port", 9001),
            reaper_host=osc_config.get("reaper_host", "127.0.0.1"),
            reaper_port=osc_config.get("reaper_port", 8000),
        )
        self.osc.set_on_message(self._on_osc_message)
        await self.osc.start()

        self._idle_timeout_ms = self.config.get("ui", {}).get("idle_timeout_ms", 2000)

        self._setup_modes()

        self._running = True
        self._last_tick = time.monotonic()

        if self._tui_queue is not None:
            asyncio.create_task(self._tui_broadcast_loop())

        await self._event_loop()

    async def stop(self):
        logger.info("Shutting down...")
        self._running = False

        for ctrl in self.controllers.values():
            ctrl.clear_grid()

        if self.osc:
            await self.osc.stop()

        await self.midi_manager.stop()

    def _setup_controllers(self):
        launchpad = LaunchpadMiniMK1(self.midi_manager)
        launchpad.set_callbacks(
            on_grid_event=self._on_grid_event,
            on_control_event=self._on_control_event,
        )
        self.controllers["Launchpad Mini"] = launchpad
        self.midi_manager.register_device("Launchpad Mini", launchpad.handle_raw_midi)

        launchkey = Launchkey49MK2(self.midi_manager)
        launchkey.set_callbacks(
            on_grid_event=self._on_grid_event,
            on_control_event=self._on_control_event,
        )
        self.controllers["Launchkey 49"] = launchkey
        self.midi_manager.register_device(
            "Launchkey 49",
            launchkey.handle_raw_midi,
            extra_input_patterns={"incontrol": "InControl"},
            extra_output_patterns={"incontrol": "InControl"},
        )

        self.midi_manager.set_on_connect(self._on_device_connect)
        self.midi_manager.set_on_disconnect(self._on_device_disconnect)

    def _setup_modes(self):
        self.mode_manager = ModeManager(self.grid, self.controllers["Launchpad Mini"])

        menu_mode = MenuMode(
            self.grid,
            self.controllers["Launchpad Mini"],
            on_mode_select=self._on_menu_select,
        )
        menu_items = self.config.get("modes", {}).get("menu", {}).get("items", [])
        if menu_items:
            menu_mode.set_items(menu_items)
        else:
            menu_mode.set_items([
                {"label": "SEQ", "mode": "sequencer", "color": "AMBER_HIGH"},
                {"label": "MIX", "mode": "mixer", "color": "GREEN_HIGH"},
                {"label": "FX", "mode": "effects", "color": "RED_HIGH"},
                {"label": "PERF", "mode": "performance", "color": "AMBER_HIGH"},
                {"label": "DEV", "mode": "device", "color": "GREEN_HIGH"},
            ])

        self.mode_manager.register(menu_mode)

        sequencer = SequencerMode(
            self.grid,
            self.controllers["Launchpad Mini"],
            midi_manager=self.midi_manager,
        )
        self.mode_manager.register(sequencer)

        mixer = MixerMode(
            self.grid,
            self.controllers["Launchpad Mini"],
        )
        self.mode_manager.register(mixer)

        self._message_mode = MessageMode(
            self.grid,
            self.controllers["Launchpad Mini"],
        )
        self.mode_manager.register(self._message_mode)

        default_mode = self.config.get("ui", {}).get("default_mode", "menu")
        self.mode_manager.switch_to(default_mode)

    def _on_device_connect(self, device_name: str):
        logger.info(f"[ENGINE] Device connected: {device_name}")
        if device_name in self.controllers:
            self.controllers[device_name].on_connect()
            if self.mode_manager and self.mode_manager.active_mode:
                self.mode_manager.active_mode.enter()

    def _on_device_disconnect(self, device_name: str):
        logger.warning(f"[ENGINE] Device disconnected: {device_name}")
        if device_name in self.controllers:
            self.controllers[device_name].on_disconnect()

    def _on_grid_event(self, event):
        self._idle_since = time.monotonic()
        if self.mode_manager.active_mode_name == "message":
            self._dismiss_message()
            return
        if self.mode_manager:
            self.mode_manager.handle_grid_event(event)

    def _on_control_event(self, event):
        self._idle_since = time.monotonic()
        if self.mode_manager.active_mode_name == "message":
            self._dismiss_message()
            return
        if self.mode_manager:
            self.mode_manager.handle_control_event(event)

    def _on_menu_select(self, mode_name: str):
        logger.info(f"[ENGINE] Menu selected mode: {mode_name}")
        if mode_name not in self.mode_manager._modes:
            logger.warning(f"Mode '{mode_name}' not yet implemented, staying in menu")
            return
        self.mode_manager.switch_to(mode_name)

    def _on_osc_message(self, msg: dict):
        msg_type = msg.get("type")
        logger.debug(f"OSC received: {msg_type}")

        if msg_type == "display_message":
            text = msg.get("text", "")
            self._enqueue_display_message(text)
        elif msg_type == "mode_set":
            mode_name = msg.get("mode", "")
            if mode_name in self.mode_manager._modes:
                self.mode_manager.switch_to(mode_name)
        elif msg_type == "beat":
            pass
        elif msg_type == "track_vu":
            pass
        elif msg_type == "play_state":
            pass

    def _enqueue_display_message(self, text: str):
        if not text:
            return
        logger.info(f"Display message: {text}")
        if self._message_mode:
            self._message_mode.enqueue_message(text)

    def _dismiss_message(self):
        logger.info("Message dismissed by user input")
        self.mode_manager.switch_back()

    async def _tui_broadcast_loop(self):
        while self._running:
            if self._tui_queue:
                snapshot = self.grid.snapshot()
                try:
                    self._tui_queue.put_nowait({
                        "type": "grid_state",
                        "grid": snapshot,
                        "mode": self.mode_manager.active_mode_name if self.mode_manager else "",
                        "devices": {
                            name: conn.connected
                            for name, conn in self.midi_manager.devices.items()
                        },
                    })
                except Exception:
                    pass
            await asyncio.sleep(0.05)

    async def _event_loop(self):
        queue = self.midi_manager.event_queue

        while self._running:
            try:
                try:
                    event_data = await asyncio.wait_for(
                        queue.get(), timeout=0.1
                    )
                except asyncio.TimeoutError:
                    self._tick()
                    self._check_idle_message()
                    continue

                device_name, message, timestamp = event_data[0], event_data[1], event_data[2]

                controller = self.controllers.get(device_name)
                if controller:
                    controller.handle_raw_midi(message)

                self._tick()
                self._check_idle_message()

            except Exception as e:
                logger.error(f"Event loop error: {e}", exc_info=True)

    def _check_idle_message(self):
        if self.mode_manager.active_mode_name == "message":
            return

        idle_ms = (time.monotonic() - self._idle_since) * 1000
        if idle_ms < self._idle_timeout_ms:
            return

        if self._message_mode and self._message_mode._current_text:
            logger.debug(f"Auto-activating message display (idle for {idle_ms:.0f}ms)")
            self._message_mode.set_previous_mode(self.mode_manager.active_mode_name)
            self.mode_manager.switch_to("message")

    def _tick(self):
        now = time.monotonic()
        delta_ms = (now - self._last_tick) * 1000
        self._last_tick = now

        if self.mode_manager:
            self.mode_manager.tick(delta_ms)
