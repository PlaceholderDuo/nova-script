import asyncio
import logging
from typing import Optional, Callable
from queue import Queue

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

from .namespace import OSC_ADDRESS, INCOMING_ADDRESS

logger = logging.getLogger(__name__)


class OscBridge:
    def __init__(
        self,
        listen_host: str = "127.0.0.1",
        listen_port: int = 9001,
        reaper_host: str = "127.0.0.1",
        reaper_port: int = 8000,
    ):
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.reaper_host = reaper_host
        self.reaper_port = reaper_port

        self._server: Optional[AsyncIOOSCUDPServer] = None
        self._transport = None
        self._client: Optional[SimpleUDPClient] = None
        self._running = False

        self._dispatcher = Dispatcher()
        self._event_queue: list = []

        self._on_message: Optional[Callable] = None

        for _handler_name, addr in INCOMING_ADDRESS.items():
            pattern = addr.replace("{n}", "*").replace("{k}", "*")
            self._dispatcher.map(pattern, self._handle_generic)

    def set_on_message(self, callback: Callable):
        self._on_message = callback

    def _handle_generic(self, address: str, *args):
        msg = {
            "address": address,
            "args": args,
        }
        if address.startswith("/nova/display/message"):
            msg["type"] = "display_message"
            msg["text"] = str(args[0]) if args else ""
        elif address.startswith("/nova/mode/set"):
            msg["type"] = "mode_set"
            msg["mode"] = str(args[0]) if args else ""
        elif address.startswith("/nova/beat"):
            msg["type"] = "beat"
            msg["position"] = float(args[0]) if args else 0.0
        elif address.startswith("/nova/play_state"):
            msg["type"] = "play_state"
            msg["state"] = int(args[0]) if args else 0
        elif "/track/" in address and "/vu" in address:
            msg["type"] = "track_vu"
            parts = address.split("/")
            try:
                track_idx = int(parts[2]) if parts[2] != "*" else 0
                msg["track"] = track_idx
                msg["level"] = float(args[0]) if args else 0.0
            except (ValueError, IndexError):
                pass
        elif "/master/vu" in address:
            msg["type"] = "master_vu"
            msg["level"] = float(args[0]) if args else 0.0

        if self._on_message:
            self._on_message(msg)

    def send(self, address: str, *args):
        if self._client:
            try:
                self._client.send_message(address, args if len(args) > 1 else (args[0] if args else None))
            except Exception as e:
                logger.error(f"OSC send error: {e}")

    def send_track_volume(self, track: int, value: float):
        self.send(f"/track/{track}/volume", value)

    def send_track_pan(self, track: int, value: float):
        self.send(f"/track/{track}/pan", value)

    def send_track_mute(self, track: int, value: int):
        self.send(f"/track/{track}/mute", value)

    def send_track_solo(self, track: int, value: int):
        self.send(f"/track/{track}/solo", value)

    def send_track_recarm(self, track: int, value: int):
        self.send(f"/track/{track}/recarm", value)

    def send_track_select(self, track: int, value: int):
        self.send(f"/track/{track}/select", value)

    def send_fx_param(self, track: int, fx: int, param: int, value: float):
        self.send(f"/track/{track}/fx/{fx}/fxparam/{param}/value", value)

    def send_fx_bypass(self, track: int, fx: int, value: int):
        self.send(f"/track/{track}/fx/{fx}/bypass", value)

    def send_transport_play(self):
        self.send("/play", 1)

    def send_transport_stop(self):
        self.send("/stop", 1)

    def send_transport_record(self):
        self.send("/record", 1)

    def send_action(self, action_id: int):
        self.send("/action", action_id)

    def send_tempo(self, bpm: float):
        self.send("/tempo", bpm)

    async def start(self):
        if self._running:
            return

        try:
            self._client = SimpleUDPClient(self.reaper_host, self.reaper_port)
            logger.info(f"OSC client → {self.reaper_host}:{self.reaper_port}")

            self._server = AsyncIOOSCUDPServer(
                (self.listen_host, self.listen_port),
                self._dispatcher,
                asyncio.get_event_loop(),
            )
            self._transport, _ = await self._server.create_serve_endpoint()
            self._running = True
            logger.info(f"OSC server listening on {self.listen_host}:{self.listen_port}")
        except Exception as e:
            logger.warning(f"OSC bridge start warning (may be normal if nothing listening): {e}")
            self._running = True

    async def stop(self):
        self._running = False
        if self._transport:
            self._transport.close()
            self._transport = None
        self._client = None
        logger.info("OSC bridge stopped")
