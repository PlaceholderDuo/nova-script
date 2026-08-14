import asyncio
import json
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
from src.ui.modes.performance import PerformanceMode
from src.ui.modes.clip_launcher import ClipLauncherMode
from src.ui.modes.instrument import InstrumentMode
from src.ui.modes.arp_edit import ArpEditMode
from src.ui.modes.light_show import LightShowMode
from src.ui.overlay_manager import OverlayManager
from src.ui.startup_wave import StartupWave
from src.ui.image_store import ImageStore
from src.osc.bridge import OscBridge
from src.controllers.color_map import LogicalColor
from src.ui.combo_detector import ComboDetector
from src.midi.clock import BPMClock

logger = logging.getLogger(__name__)


class Engine:
    def __init__(self, config: Optional[dict] = None, tui_queue: Optional[Queue] = None):
        self.config = config or {}
        self.midi_manager = MidiManager(poll_interval=0.5)
        self.grid = LogicalGrid(8, 8)
        self.mode_manager: Optional[ModeManager] = None
        self.controllers: dict[str, object] = {}
        self.osc: Optional[OscBridge] = None
        self.overlay: Optional[OverlayManager] = None
        self._combo: Optional[ComboDetector] = None
        self._startup_wave: Optional[StartupWave] = None
        self._image_store: Optional[ImageStore] = None
        self._clock: Optional[BPMClock] = None
        self._running = False
        self._last_tick = time.monotonic()
        self._tui_queue: Optional[Queue] = tui_queue
        self._idle_timeout_ms: int = 30000
        self._beat_led_on: bool = False
        self._beat_led_off_time: float = 0.0
        self._press_feedback: dict[tuple[int, int], float] = {}
        self._downbeat_count: int = 0
        self._last_downbeat: int = -1
        self._message_mode: Optional[MessageMode] = None
        self._virt_ws = None
        self._virt_last_info: str = ""
        self._arp_exit_pending_release: bool = False

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
        logger.info(f"Starting Nova-Script (profile: {self.config.get('_profile_name', '?')})")

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

        self._idle_timeout_ms = self.config.get("ui", {}).get("idle_timeout_ms", 30000)
        self._image_store = ImageStore()
        self._setup_overlay()

        await asyncio.sleep(0.15)

        self._startup_wave = StartupWave(self.grid, self.controllers["Launchpad Mini"])
        self._startup_wave.start()
        while self._startup_wave.tick():
            await asyncio.sleep(0.03)

        await asyncio.sleep(0.2)

        self._setup_modes()

        self._running = True
        self._last_tick = time.monotonic()

        if self._tui_queue is not None:
            asyncio.create_task(self._tui_broadcast_loop())
        asyncio.create_task(self._virt_sync_loop())

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

        force = (
            self.config.get("midi", {}).get("outputs", {}).get("force")
            or self.config.get("midi", {}).get("force_output", {}).get("port_name")
        )
        if force:
            self.midi_manager.register_force_output(force)

        # Alesis V25 — separate, non-Novation input device (MIDI thru to Force).
        v25_cfg = self.config.get("midi", {}).get("v25", {})
        if v25_cfg:
            from src.controllers.alesis_v25 import AlesisV25
            self.controllers[AlesisV25.DEVICE_NAME] = AlesisV25(
                self.midi_manager,
                v25_cfg.get("target", ""),
                input_pattern=v25_cfg.get("input_pattern", "V25"),
                cc_remap=v25_cfg.get("cc_remap"),
            )

        # Generic MIDI thru routes (for future devices beyond the V25).
        for route in self.config.get("midi", {}).get("thru", []):
            src = route.get("source", "")
            tgt = route.get("target", "")
            chs = route.get("channels", None)
            note = route.get("note_only", False)
            remap = route.get("cc_remap", None)
            if src and tgt:
                try:
                    from src.midi.routing import MidiThru
                    MidiThru(self.midi_manager, src, tgt, channels=chs,
                             note_only=note, cc_remap=remap)
                    logger.info(f"MIDI thru: {src} → {tgt} (channels={chs}, note_only={note}, cc_remap={remap})")
                except Exception as e:
                    logger.warning(f"MIDI thru setup failed ({src}→{tgt}): {e}")

    def _setup_overlay(self):
        bpm = float(self.config.get("midi", {}).get("clock", {}).get("internal_bpm", 120))
        self.overlay = OverlayManager(
            self.grid,
            self.controllers["Launchpad Mini"],
            self._image_store,
            idle_timeout_ms=self._idle_timeout_ms,
            bpm=bpm,
        )
        self.overlay.start()
        self._combo = ComboDetector()
        clock_cfg = self.config.get("midi", {}).get("clock", {})
        self._clock = BPMClock(
            default_bpm=float(clock_cfg.get("internal_bpm", 120)),
            preferred=clock_cfg.get("preferred", "Reaper"),
            fallback=clock_cfg.get("fallback", "Internal"),
        )
        self._clock.set_on_beat(self._on_beat)
        sc_config = self.config.get("screensaver", {})
        self.overlay.set_screensaver_brightness(sc_config.get("brightness", 100))
        self.overlay.set_screensaver_enabled(sc_config.get("enabled", True))
        osc_msg_speed = self.config.get("osc", {}).get("scroll_speed_ms", 60)
        self.overlay.set_hud_scroll_speed_ms(osc_msg_speed)

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
                {"label": "PERF", "mode": "performance", "color": "RED_HIGH", "x": 0, "y": 6, "w": 2, "h": 2},
                {"label": "CLIP", "mode": "clip_launcher", "color": "RED_MED", "x": 2, "y": 6, "w": 2, "h": 2},
                {"label": "SEQ", "mode": "sequencer", "color": "AMBER_HIGH", "x": 4, "y": 6, "w": 2, "h": 2},
                {"label": "MIX", "mode": "mixer", "color": "GREEN_HIGH", "x": 0, "y": 4, "w": 2, "h": 2},
                {"label": "INST", "mode": "instrument", "color": "GREEN_MED", "x": 2, "y": 4, "w": 2, "h": 2},
                {"label": "ARP", "mode": "arp_edit", "color": "AMBER_MED", "x": 4, "y": 4, "w": 2, "h": 2},
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
            osc_bridge=self.osc,
        )
        self.mode_manager.register(mixer)

        self._message_mode = MessageMode(
            self.grid,
            self.controllers["Launchpad Mini"],
        )
        self.mode_manager.register(self._message_mode)

        performance = PerformanceMode(
            self.grid,
            self.controllers["Launchpad Mini"],
            config=self.config.get("performance"),
            osc_bridge=self.osc,
        )
        self.mode_manager.register(performance)

        clip_launcher = ClipLauncherMode(
            self.grid,
            self.controllers["Launchpad Mini"],
            config=self.config.get("clip_launcher"),
            osc_bridge=self.osc,
            midi_manager=self.midi_manager,
        )
        self.mode_manager.register(clip_launcher)

        instrument = InstrumentMode(
            self.grid,
            self.controllers["Launchpad Mini"],
            config=self.config.get("instrument"),
            midi_manager=self.midi_manager,
        )
        self.mode_manager.register(instrument)

        arp_edit = ArpEditMode(
            self.grid,
            self.controllers["Launchpad Mini"],
            midi_manager=self.midi_manager,
        )
        self.mode_manager.register(arp_edit)

        light_show = LightShowMode(
            self.grid,
            self.controllers["Launchpad Mini"],
            config=self.config.get("light_show"),
        )
        self.mode_manager.register(light_show)

        instrument.set_arp_edit_callback(self._enter_arp_edit)

        default_mode = self.config.get("ui", {}).get("default_mode", "performance")
        self.mode_manager.switch_to(default_mode)

    def _enter_arp_edit(self, from_menu: bool = False):
        inst = self.mode_manager._modes.get("instrument")
        arp = self.mode_manager._modes.get("arp_edit")
        if not arp:
            return
        if inst and not from_menu:
            state = inst.get_arp_state()
            arp.set_state(**state)
        self.mode_manager.switch_to("arp_edit")

    def _exit_arp_edit(self):
        inst = self.mode_manager._modes.get("instrument")
        arp = self.mode_manager._modes.get("arp_edit")
        if not arp:
            return
        if inst:
            state = arp.get_state()
            inst.update_from_arp_edit(state)
        if getattr(self.mode_manager, "_previous_mode_name", "") == "menu":
            self.mode_manager.switch_to("menu")
        else:
            self.mode_manager.switch_to("instrument")

    def _on_device_connect(self, device_name: str):
        logger.info(f"[ENGINE] Device connected: {device_name}")
        ctrl = self.controllers.get(device_name)
        if ctrl is not None:
            on_connect = getattr(ctrl, "on_connect", None)
            if callable(on_connect):
                on_connect()
            if self.mode_manager and self.mode_manager.active_mode:
                self.mode_manager.active_mode.enter()

    def _on_device_disconnect(self, device_name: str):
        logger.warning(f"[ENGINE] Device disconnected: {device_name}")
        ctrl = self.controllers.get(device_name)
        if ctrl is not None:
            on_disconnect = getattr(ctrl, "on_disconnect", None)
            if callable(on_disconnect):
                on_disconnect()

    def _on_grid_event(self, event):
        if event.pressed:
            if self.overlay:
                self.overlay.mark_activity()
            lp = self.controllers.get("Launchpad Mini")
            if lp:
                lp.set_grid_color(event.x, event.y, LogicalColor.AMBER_HIGH)
                self._press_feedback[(event.x, event.y)] = time.monotonic() + 0.12
        if self.overlay:
            if self.overlay.handle_grid_event(event):
                return
        if self.mode_manager:
            self.mode_manager.handle_grid_event(event)

    def _on_control_event(self, event):
        is_press = "PRESS" in event.event_type.name
        if self.overlay and is_press:
            self.overlay.mark_activity()

        # Mode-specific exits take priority over global combos, otherwise a
        # combo (e.g. 200 = "home") would shadow the ARP-edit exit button.
        # We must swallow the paired RELEASE too, or it decays into "home".
        if is_press and self.mode_manager and not self.overlay.is_overlay_active:
            if self.mode_manager.active_mode_name == "arp_edit" and event.control_id == 200:
                arp = self.mode_manager._modes.get("arp_edit")
                if arp is not None and getattr(arp, "is_note_length_mode", lambda: False)():
                    # Top-1 in note-length mode = back to the pattern editor.
                    self._arp_exit_pending_release = True
                    arp.exit_note_length()
                    return
                self._arp_exit_pending_release = True
                self._exit_arp_edit()
                return
        if self._arp_exit_pending_release:
            self._arp_exit_pending_release = False
            return

        if self._combo:
            result = self._combo.feed(event.control_id, is_press)
            if result == "consumed":
                return
            if result == "home":
                self.mode_manager.switch_to("performance")
                return
            if result == "screensaver":
                self.overlay.trigger_screensaver()
                return
            if result == "fireworks":
                self.overlay.trigger_fireworks()
                return

        if self.overlay:
            if self.overlay.handle_control_event(event):
                return

        if is_press and not self.overlay.is_overlay_active:
            if 201 <= event.control_id <= 208:
                top_idx = event.control_id - 200
                menu_mode = self.mode_manager._modes.get("menu")
                if menu_mode and top_idx < len(menu_mode._items):
                    item = menu_mode._items[top_idx]
                    if "mode" in item and item["mode"] in self.mode_manager._modes:
                        self.mode_manager.switch_to(item["mode"])
                        return
        if self.mode_manager:
            self.mode_manager.handle_control_event(event)

    def _on_menu_select(self, mode_name: str):
        logger.info(f"[ENGINE] Menu selected mode: {mode_name}")
        if mode_name not in self.mode_manager._modes:
            logger.warning(f"Mode '{mode_name}' not yet implemented, staying in menu")
            return
        self.mode_manager.switch_to(mode_name)

    def _set_home_led(self, color_override: LogicalColor | None = None):
        lp = self.controllers.get("Launchpad Mini")
        if lp is None:
            return
        if not self._beat_led_on:
            lp.send_top_row_led(0, LogicalColor.OFF)
            return
        if color_override is not None:
            lp.send_top_row_led(0, color_override)
            return
        at_home = self.mode_manager and self.mode_manager.active_mode_name == "performance"
        color = LogicalColor.AMBER_HIGH if at_home else LogicalColor.GREEN_HIGH
        lp.send_top_row_led(0, color)

    def _on_beat(self, beat_count: int):
        self._beat_led_on = True
        self._beat_led_off_time = time.monotonic() + 0.12

        # Forward the beat to the active mode if it wants one (Light Show
        # pulses are beat-quantized so flashes land on the grid).
        if self.mode_manager:
            m = self.mode_manager._modes.get(self.mode_manager.active_mode_name)
            if m and hasattr(m, "on_beat"):
                try:
                    m.on_beat(beat_count)
                except Exception:
                    pass

        mode = self.config.get("ui", {}).get("downbeat_flash", "tempo_led")

        is_downbeat = (beat_count % 4 == 1)
        is_new = (is_downbeat and self._last_downbeat != beat_count)
        if is_new:
            self._last_downbeat = beat_count

        if mode == "disable":
            self._set_home_led()
        elif mode == "tempo_led":
            if is_downbeat:
                self._set_home_led(self._get_downbeat_color())
            else:
                self._set_home_led()
        elif mode == "4 corners":
            if is_downbeat:
                self._set_home_led(self._get_downbeat_color())
                self._flash_downbeat_corners()
            else:
                self._set_home_led()

    def _get_downbeat_color(self) -> LogicalColor:
        color_name = self.config.get("ui", {}).get("downbeat_color", "GREEN_HIGH")
        try:
            return LogicalColor[color_name]
        except KeyError:
            return LogicalColor.GREEN_HIGH

    def _flash_downbeat_corners(self):
        color = self._get_downbeat_color()
        lp = self.controllers.get("Launchpad Mini")
        if lp is None:
            return
        corners = [(0, 0), (7, 0), (0, 7), (7, 7)]
        for x, y in corners:
            lp.set_grid_color(x, y, color)
        self._press_feedback[(-1, 0)] = time.monotonic() + 0.15

    def _on_osc_message(self, msg: dict):
        msg_type = msg.get("type")
        logger.debug(f"OSC received: {msg_type}")

        if msg_type == "display_message":
            text = msg.get("text", "")
            if self.overlay:
                self.overlay.trigger_hud(text=text)
        elif msg_type == "mode_set":
            mode_name = msg.get("mode", "")
            if mode_name in self.mode_manager._modes:
                self.mode_manager.switch_to(mode_name)
        elif msg_type == "beat":
            if self._clock:
                self._clock.feed_osc_beat(msg.get("position", 0.0))
        elif msg_type == "track_vu":
            if self.mode_manager:
                mixer = self.mode_manager._modes.get("mixer")
                if mixer and hasattr(mixer, "set_track_vu"):
                    mixer.set_track_vu(msg.get("track", 0), msg.get("level", 0.0))
        elif msg_type == "master_vu":
            if self.mode_manager:
                mixer = self.mode_manager._modes.get("mixer")
                if mixer and hasattr(mixer, "set_master_vu"):
                    mixer.set_master_vu(msg.get("level", 0.0))
        elif msg_type == "play_state":
            state = msg.get("state", 0)
            if self.mode_manager:
                pm = self.mode_manager._modes.get("performance")
                if pm and hasattr(pm, "set_play_state"):
                    pm.set_play_state(state)
        elif msg_type == "tuner":
            if self.mode_manager:
                pm = self.mode_manager._modes.get("performance")
                if pm and hasattr(pm, "update_tuner"):
                    pm.update_tuner(msg.get("cents", 0.0), msg.get("channel", "GTR"))

    def _tick(self):
        now = time.monotonic()
        delta_ms = (now - self._last_tick) * 1000
        self._last_tick = now

        if self._clock:
            self._clock.tick(now)

        self._tick_press_feedback(now)

        if self._beat_led_on and now >= self._beat_led_off_time:
            self._beat_led_on = False
            self._set_home_led()

        if self._combo:
            result = self._combo.tick()
            if result == "home":
                self.mode_manager.switch_to("menu")

        if self.overlay:
            self.overlay.tick(delta_ms, now=now)
            if not self.overlay.is_overlay_active and self.mode_manager:
                self.mode_manager.tick(delta_ms)
        elif self.mode_manager:
            self.mode_manager.tick(delta_ms)

        if self._clock and self.mode_manager:
            for mode_name in ("performance", "clip_launcher", "light_show"):
                m = self.mode_manager._modes.get(mode_name)
                if m and hasattr(m, "set_bpm"):
                    m.set_bpm(self._clock.bpm)
            inst = self.mode_manager._modes.get("instrument")
            if inst and hasattr(inst, "set_bpm"):
                inst.set_bpm(self._clock.bpm)
            if inst and hasattr(inst, "set_arp_transpose"):
                transpose_cfg = self.config.get("arp", {})
                inst.set_arp_transpose(transpose_cfg.get("diatonic", True))
            pm = self.mode_manager._modes.get("performance")
            if pm and hasattr(pm, "set_hints_config"):
                ui = self.config.get("ui", {})
                pm.set_hints_config(
                    ui.get("hints_enabled", True),
                    ui.get("hints_color", "AMBER_HIGH"),
                )

    def _tick_press_feedback(self, now: float):
        expired = [k for k, v in self._press_feedback.items() if now >= v]
        for key in expired:
            del self._press_feedback[key]
            if key == (-1, 0):
                if self.mode_manager and self.mode_manager.active_mode:
                    self.mode_manager.active_mode.enter()
            elif self.mode_manager and self.mode_manager.active_mode:
                self.mode_manager.active_mode.enter()

    def _build_virt_info(self) -> dict:
        mode = self.mode_manager.active_mode_name if self.mode_manager else ""
        page = ""
        subpage = ""

        if mode == "instrument":
            m = self.mode_manager._modes.get("instrument")
            if m:
                if getattr(m, "_editing_offset", False):
                    page = "offset_select"
                else:
                    page = "play"
        elif mode == "arp_edit":
            arp = self.mode_manager._modes.get("arp_edit")
            if arp:
                page = f"page_{getattr(arp, '_arp_page', 0) + 1}"
                if getattr(arp, "_note_length_mode", False):
                    subpage = "note_length"

        if self.overlay and self.overlay.is_overlay_active:
            if self.overlay._active == 2:
                mode = "screensaver"
                page = str(getattr(self.overlay, "_active_screensaver_mode", 0))

        return {"mode": mode, "page": page, "subpage": subpage}

    async def _virt_sync_loop(self):
        fail_backoff = 1.0
        while self._running:
            try:
                if self._virt_ws is None:
                    import websockets
                    self._virt_ws = await websockets.connect(
                        "ws://localhost:8766", open_timeout=2, close_timeout=1
                    )
                    logger.info("Virt sync: connected to virtualizer")
                    fail_backoff = 1.0
                info = self._build_virt_info()
                info_str = json.dumps(info)
                if info_str != self._virt_last_info:
                    await self._virt_ws.send(json.dumps({"action": "set_info", **info}))
                    self._virt_last_info = info_str
                await asyncio.sleep(0.2)
            except Exception:
                self._virt_ws = None
                # Virtualizer not running — retry infrequently, don't spam the log.
                await asyncio.sleep(fail_backoff)
                fail_backoff = min(fail_backoff * 2, 15.0)

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
                    continue

                device_name, message, timestamp = event_data[0], event_data[1], event_data[2]

                if self._clock and any(b == 0xF8 for b in (message or [])):
                    self._clock.feed_midi_clock()

                controller = self.controllers.get(device_name)
                if controller:
                    controller.handle_raw_midi(message)

                self._tick()

            except Exception as e:
                logger.error(f"Event loop error: {e}", exc_info=True)
