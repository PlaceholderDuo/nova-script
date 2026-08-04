import asyncio
import logging
import time
from pathlib import Path
from queue import Queue, Empty
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
from src.controllers.color_map import LogicalColor

logger = logging.getLogger(__name__)


class Engine:
    def __init__(self, config_path: Optional[Path] = None):
        self.config = self._load_config(config_path)
        self.midi_manager = MidiManager(poll_interval=0.5)
        self.grid = LogicalGrid(8, 8)
        self.mode_manager: Optional[ModeManager] = None
        self.controllers: dict[str, "NovationController"] = {}
        self._running = False
        self._last_tick = time.monotonic()
        self._idle_since = time.monotonic()
        self._tui_queue: Optional[Queue] = None

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

        await self.midi_manager.stop()

    def _setup_controllers(self):
        launchpad = LaunchpadMiniMK1(self.midi_manager)
        launchpad.set_callbacks(
            on_grid_event=self._on_grid_event,
            on_control_event=self._on_control_event,
        )
        self.controllers["Launchpad Mini"] = launchpad
        self.midi_manager.register_device("Launchpad Mini", launchpad.handle_raw_midi)

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
        if self.mode_manager:
            self.mode_manager.handle_grid_event(event)

    def _on_control_event(self, event):
        self._idle_since = time.monotonic()
        if self.mode_manager:
            self.mode_manager.handle_control_event(event)

    def _on_menu_select(self, mode_name: str):
        logger.info(f"[ENGINE] Menu selected mode: {mode_name}")
        if mode_name not in self.mode_manager._modes:
            logger.warning(f"Mode '{mode_name}' not yet implemented, staying in menu")
            return
        self.mode_manager.switch_to(mode_name)

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
                    device_name, message, timestamp = await asyncio.wait_for(
                        queue.get(), timeout=0.1
                    )
                except asyncio.TimeoutError:
                    self._tick()
                    continue

                controller = self.controllers.get(device_name)
                if controller:
                    controller.handle_raw_midi(message)

                self._tick()

            except Exception as e:
                logger.error(f"Event loop error: {e}", exc_info=True)

    def _tick(self):
        now = time.monotonic()
        delta_ms = (now - self._last_tick) * 1000
        self._last_tick = now

        if self.mode_manager:
            self.mode_manager.tick(delta_ms)
