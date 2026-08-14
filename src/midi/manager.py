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

    extra_inputs: dict[str, tuple[Optional[MidiPort], Optional[rtmidi.MidiIn]]] = field(default_factory=dict)
    extra_outputs: dict[str, tuple[Optional[MidiPort], Optional[rtmidi.MidiOut]]] = field(default_factory=dict)
    secondary_connected: bool = False
    _reported_secondary: bool = field(default=False, repr=False)
    _on_connect_fired: bool = field(default=False, repr=False)


class MidiManager:
    def __init__(self, poll_interval: float = 0.5):
        self.poll_interval = poll_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None

        self._midi_in = rtmidi.MidiIn()
        self._midi_out = rtmidi.MidiOut()

        self.devices: dict[str, DeviceConnection] = {}
        self._input_callbacks: dict[str, Callable] = {}
        self._device_configs: dict[str, dict] = {}

        self._on_connect: Optional[Callable] = None
        self._on_disconnect: Optional[Callable] = None
        self._midi_event_queue: asyncio.Queue = asyncio.Queue()

        self.force_device: Optional[str] = None

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

    def register_device(
        self,
        name: str,
        input_callback: Callable,
        extra_input_patterns: Optional[dict[str, str]] = None,
        extra_output_patterns: Optional[dict[str, str]] = None,
        input_only: bool = False,
        output_only: bool = False,
        input_pattern: Optional[str] = None,
        output_pattern: Optional[str] = None,
    ):
        self.devices[name] = DeviceConnection(name=name)
        self._input_callbacks[name] = input_callback
        self._device_configs[name] = {
            "extra_inputs": extra_input_patterns or {},
            "extra_outputs": extra_output_patterns or {},
            "input_only": input_only,
            "output_only": output_only,
            "input_pattern": input_pattern,
            "output_pattern": output_pattern,
        }
        logger.info(f"Registered device: {name}")
        if extra_input_patterns:
            for key, pattern in extra_input_patterns.items():
                logger.info(f"  + extra input '{key}': pattern='{pattern}'")

    def register_input(self, name: str, input_callback: Callable, pattern: Optional[str] = None):
        """Register an input-only device (no MIDI output opened)."""
        self.register_device(name, input_callback, input_only=True, input_pattern=pattern)

    def register_output(self, name: str, pattern: Optional[str] = None):
        """Register an output-only device (no MIDI input opened)."""
        if name in self.devices:
            return
        self.register_device(name, lambda msg: None, output_only=True, output_pattern=pattern)

    def register_force_output(self, port_pattern: str):
        """Register the Akai Force as a routable output-only device."""
        if not port_pattern:
            return
        self.force_device = port_pattern
        self.register_device(
            port_pattern,
            input_callback=lambda msg: None,
        )

    def _find_matching_port(self, ports: list[str], pattern: str) -> Optional[MidiPort]:
        for idx, port_name in enumerate(ports):
            if pattern.lower() in port_name.lower():
                return MidiPort(name=port_name, index=idx)
        return None

    def _try_connect_device(self, device_name: str) -> bool:
        conn = self.devices.get(device_name)
        config = self._device_configs.get(device_name, {})
        if conn is None:
            return False

        if conn.connected:
            if not config.get("extra_inputs") and not config.get("extra_outputs"):
                return True
            if conn.secondary_connected:
                return True

        in_ports, out_ports = self.scan_ports()

        if not conn.connected:
            input_only = config.get("input_only", False)
            output_only = config.get("output_only", False)
            in_pat = config.get("input_pattern") or device_name
            out_pat = config.get("output_pattern") or device_name

            input_port = self._find_matching_port(in_ports, in_pat) if not output_only else None
            output_port = self._find_matching_port(out_ports, out_pat) if not input_only else None

            if (not output_only and input_port is None) or (not input_only and output_port is None):
                return False

            try:
                midi_in = None
                midi_out = None
                if input_port is not None:
                    midi_in = rtmidi.MidiIn()
                    midi_in.open_port(input_port.index)
                    midi_in.ignore_types(sysex=False, timing=False, active_sense=False)
                    midi_in.set_callback(self._make_callback(device_name, "main"))
                if output_port is not None:
                    midi_out = rtmidi.MidiOut()
                    midi_out.open_port(output_port.index)

                conn.input_port = input_port
                conn.output_port = output_port
                conn.midi_in = midi_in
                conn.midi_out = midi_out
                conn.connected = True
                conn.last_seen = time.monotonic()

                in_name = input_port.name if input_port else "-"
                out_name = output_port.name if output_port else "-"
                logger.info(
                    f"Connected {device_name}: "
                    f"in={in_name} ({input_port.index if input_port else '-'}), "
                    f"out={out_name} ({output_port.index if output_port else '-'})"
                )
            except Exception as e:
                logger.error(f"Failed to connect {device_name}: {e}")
                return False

        extra_inputs = config.get("extra_inputs", {})
        extra_outputs = config.get("extra_outputs", {})

        for key, pattern in extra_inputs.items():
            if key not in conn.extra_inputs or conn.extra_inputs[key][0] is None:
                port = self._find_matching_port(in_ports, pattern)
                if port is None:
                    continue
                try:
                    mi = rtmidi.MidiIn()
                    mi.open_port(port.index)
                    mi.ignore_types(sysex=False, timing=False, active_sense=False)
                    mi.set_callback(self._make_callback(device_name, key))
                    conn.extra_inputs[key] = (port, mi)
                    logger.info(f"  + {device_name} extra in '{key}': {port.name} ({port.index})")
                except Exception as e:
                    logger.error(f"Failed extra in {key} for {device_name}: {e}")

        for key, pattern in extra_outputs.items():
            if key not in conn.extra_outputs or conn.extra_outputs[key][0] is None:
                port = self._find_matching_port(out_ports, pattern)
                if port is None:
                    continue
                try:
                    mo = rtmidi.MidiOut()
                    mo.open_port(port.index)
                    conn.extra_outputs[key] = (port, mo)
                    logger.info(f"  + {device_name} extra out '{key}': {port.name} ({port.index})")
                except Exception as e:
                    logger.error(f"Failed extra out {key} for {device_name}: {e}")

        has_extras = bool(extra_inputs) or bool(extra_outputs)
        if not has_extras:
            conn.secondary_connected = True
        else:
            all_extra_in = all(
                key in conn.extra_inputs and conn.extra_inputs[key][0] is not None
                for key in extra_inputs
            ) if extra_inputs else True
            all_extra_out = all(
                key in conn.extra_outputs and conn.extra_outputs[key][0] is not None
                for key in extra_outputs
            ) if extra_outputs else True
            conn.secondary_connected = all_extra_in and all_extra_out
            if conn.secondary_connected and not conn._reported_secondary:
                conn._reported_secondary = True
                logger.info(f"{device_name}: all extra ports connected")

        if conn.connected and (not has_extras or conn.secondary_connected):
            if self._on_connect and not getattr(conn, "_on_connect_fired", False):
                conn._on_connect_fired = True
                self._on_connect(device_name)

        return conn.connected

    def _disconnect_device(self, device_name: str):
        conn = self.devices.get(device_name)
        if conn is None:
            return

        try:
            if conn.midi_in:
                conn.midi_in.cancel_callback()
                conn.midi_in.close_port()
            if conn.midi_out:
                conn.midi_out.close_port()
            for key, (_, mi) in list(conn.extra_inputs.items()):
                if mi:
                    mi.cancel_callback()
                    mi.close_port()
            for key, (_, mo) in list(conn.extra_outputs.items()):
                if mo:
                    mo.close_port()
        except Exception as e:
            logger.warning(f"Error closing ports for {device_name}: {e}")

        conn.connected = False
        conn.secondary_connected = False
        conn._on_connect_fired = False
        conn._reported_secondary = False
        conn.midi_in = None
        conn.midi_out = None
        conn.input_port = None
        conn.output_port = None
        conn.extra_inputs.clear()
        conn.extra_outputs.clear()

        logger.warning(f"Disconnected: {device_name}")

        if self._on_disconnect:
            self._on_disconnect(device_name)

    def _check_connection_health(self):
        in_ports, out_ports = self.scan_ports()

        for device_name, conn in self.devices.items():
            if not conn.connected:
                continue
            if conn.input_port is None and conn.output_port is None:
                continue

            in_still = True
            out_still = True
            if conn.input_port is not None:
                in_still = any(conn.input_port.name == p for p in in_ports)
            if conn.output_port is not None:
                out_still = any(conn.output_port.name == p for p in out_ports)

            if not in_still or not out_still:
                logger.warning(
                    f"Device {device_name} disappeared "
                    f"(in={in_still}, out={out_still}). Reconnecting..."
                )
                self._disconnect_device(device_name)

    def _make_callback(self, device_name: str, port_key: str = "main"):
        def callback(event, data=None):
            message, delta_time = event
            self._midi_event_queue.put_nowait(
                (device_name, message, time.monotonic(), port_key)
            )
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

    def send_message(self, device_name: str, message: list[int], target: str = "main"):
        conn = self.devices.get(device_name)
        if conn is None:
            return

        if target == "main":
            if not conn.connected or conn.midi_out is None:
                return
            try:
                conn.midi_out.send_message(message)
            except Exception as e:
                logger.error(f"Error sending MIDI to {device_name}: {e}")
                self._disconnect_device(device_name)
        else:
            if target not in conn.extra_outputs or conn.extra_outputs[target][1] is None:
                return
            try:
                conn.extra_outputs[target][1].send_message(message)
            except Exception as e:
                logger.error(f"Error sending MIDI to {device_name}/{target}: {e}")

    def send_force(self, message: list[int]):
        """Send a MIDI message to the Akai Force output device if connected."""
        if self.force_device and self.force_device in self.devices:
            self.send_message(self.force_device, message, target="main")

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
