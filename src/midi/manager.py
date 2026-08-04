import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Callable

import rtmidi

logger = logging.getLogger(__name__)


@dataclass
class MidiPort:
    name: str
    index: int


@dataclass
class DeviceConnection:
    name: str
    input_port: Optional[MidiPort] = None
    output_port: Optional[MidiPort] = None
    midi_in: Optional[rtmidi.MidiIn] = None
    midi_out: Optional[rtmidi.MidiOut] = None
    connected: bool = False
    last_seen: float = 0.0


class MidiManager:
    def __init__(self, poll_interval: float = 0.5):
        self.poll_interval = poll_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None

        self._midi_in = rtmidi.MidiIn()
        self._midi_out = rtmidi.MidiOut()

        self.devices: dict[str, DeviceConnection] = {}
        self._input_callbacks: dict[str, Callable] = {}

        self._on_connect: Optional[Callable] = None
        self._on_disconnect: Optional[Callable] = None
        self._midi_event_queue: asyncio.Queue = asyncio.Queue()

    @property
    def event_queue(self) -> asyncio.Queue:
        return self._midi_event_queue

    def set_on_connect(self, callback: Callable):
        self._on_connect = callback

    def set_on_disconnect(self, callback: Callable):
        self._on_disconnect = callback

    def scan_ports(self) -> tuple[list[str], list[str]]:
        return (
            self._midi_in.get_ports(),
            self._midi_out.get_ports(),
        )

    def register_device(self, name: str, input_callback: Callable):
        self.devices[name] = DeviceConnection(name=name)
        self._input_callbacks[name] = input_callback
        logger.info(f"Registered device: {name}")

    def _find_matching_port(self, ports: list[str], device_name: str) -> Optional[MidiPort]:
        for idx, port_name in enumerate(ports):
            if device_name.lower() in port_name.lower():
                return MidiPort(name=port_name, index=idx)
        return None

    def _try_connect_device(self, device_name: str) -> bool:
        conn = self.devices.get(device_name)
        if conn is None:
            return False

        if conn.connected:
            return True

        in_ports, out_ports = self.scan_ports()

        input_port = self._find_matching_port(in_ports, device_name)
        output_port = self._find_matching_port(out_ports, device_name)

        if input_port is None or output_port is None:
            return False

        try:
            midi_in = rtmidi.MidiIn()
            midi_in.open_port(input_port.index)
            midi_in.ignore_types(sysex=False, timing=False, active_sense=False)
            midi_in.set_callback(self._make_callback(device_name))

            midi_out = rtmidi.MidiOut()
            midi_out.open_port(output_port.index)

            conn.input_port = input_port
            conn.output_port = output_port
            conn.midi_in = midi_in
            conn.midi_out = midi_out
            conn.connected = True
            conn.last_seen = time.monotonic()

            logger.info(
                f"Connected {device_name}: "
                f"in={input_port.name} ({input_port.index}), "
                f"out={output_port.name} ({output_port.index})"
            )

            if self._on_connect:
                self._on_connect(device_name)

            return True

        except Exception as e:
            logger.error(f"Failed to connect {device_name}: {e}")
            return False

    def _disconnect_device(self, device_name: str):
        conn = self.devices.get(device_name)
        if conn is None or not conn.connected:
            return

        try:
            if conn.midi_in:
                conn.midi_in.cancel_callback()
                conn.midi_in.close_port()
            if conn.midi_out:
                conn.midi_out.close_port()
        except Exception as e:
            logger.warning(f"Error closing ports for {device_name}: {e}")

        conn.connected = False
        conn.midi_in = None
        conn.midi_out = None
        conn.input_port = None
        conn.output_port = None

        logger.warning(f"Disconnected: {device_name}")

        if self._on_disconnect:
            self._on_disconnect(device_name)

    def _check_connection_health(self):
        in_ports, out_ports = self.scan_ports()

        for device_name, conn in self.devices.items():
            if not conn.connected:
                continue

            in_still_present = any(
                conn.input_port.name == p for p in in_ports
            )
            out_still_present = any(
                conn.output_port.name == p for p in out_ports
            )

            if not in_still_present or not out_still_present:
                logger.warning(
                    f"Device {device_name} disappeared "
                    f"(in={in_still_present}, out={out_still_present}). "
                    f"Disconnecting and will attempt reconnect."
                )
                self._disconnect_device(device_name)

    def _make_callback(self, device_name: str):
        def callback(event, data=None):
            message, delta_time = event
            self._midi_event_queue.put_nowait((device_name, message, time.monotonic()))
        return callback

    async def _poll_loop(self):
        consecutive_errors = 0
        while self._running:
            try:
                self._check_connection_health()

                for device_name in list(self.devices.keys()):
                    self._try_connect_device(device_name)

                consecutive_errors = 0

            except Exception as e:
                consecutive_errors += 1
                if consecutive_errors <= 3:
                    logger.warning(f"Poll error (attempt {consecutive_errors}): {e}")
                if consecutive_errors > 10:
                    logger.critical(f"Poll loop failing repeatedly: {e}")

            await asyncio.sleep(self.poll_interval)

    def send_message(self, device_name: str, message: list[int]):
        conn = self.devices.get(device_name)
        if conn is None or not conn.connected or conn.midi_out is None:
            logger.debug(f"Cannot send to {device_name}: not connected")
            return

        try:
            conn.midi_out.send_message(message)
        except Exception as e:
            logger.error(f"Error sending MIDI to {device_name}: {e}")
            self._disconnect_device(device_name)

    async def start(self):
        if self._running:
            return

        self._running = True

        for device_name in list(self.devices.keys()):
            self._try_connect_device(device_name)

        self._task = asyncio.create_task(self._poll_loop())
        logger.info("MidiManager started (auto-reconnect polling active)")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        for device_name in list(self.devices.keys()):
            self._disconnect_device(device_name)

        self._midi_in.delete()
        self._midi_out.delete()
        logger.info("MidiManager stopped")
