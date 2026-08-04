"""
BPM Clock — multi-source tempo sync with automatic priority switching.

Priority: OSC beat (Reaper) > MIDI clock (Akai Force) > Internal BPM.
"""
import logging
import time

logger = logging.getLogger(__name__)


class BPMClock:
    SOURCE_INTERNAL = "internal"
    SOURCE_OSC = "osc"
    SOURCE_MIDI = "midi"

    def __init__(self, default_bpm: float = 120.0, preferred: str = "Reaper", fallback: str = "Internal"):
        self._bpm = default_bpm
        self._preferred = preferred
        self._fallback = fallback
        self._source = self.SOURCE_INTERNAL
        self._beat_interval = 60.0 / default_bpm
        self._last_beat_time = 0.0
        self._beat_count = 0
        self._on_beat = None

        self._last_osc_beat = 0.0
        self._midi_clock_count = 0
        self._last_midi_beat = 0.0

        # Track which sources are live
        self._osc_active = False
        self._midi_active = False
        self._osc_last_seen = 0.0
        self._midi_last_seen = 0.0
        self._source_timeout = 2.0  # seconds before source is considered inactive

    def set_on_beat(self, callback):
        self._on_beat = callback

    def feed_osc_beat(self, position: float = 0.0):
        """Called when OSC /beat arrives from Reaper."""
        now = time.monotonic()
        self._osc_last_seen = now
        if not self._osc_active:
            logger.info("BPM source detected: OSC (Reaper)")
        self._osc_active = True

        if self._preferred not in ("Reaper (OSC)", "Reaper"):
            return

        if self._last_osc_beat > 0:
            interval = now - self._last_osc_beat
            if 0.1 < interval < 5.0:
                new_bpm = 60.0 / interval
                if 20 < new_bpm < 300:
                    self._bpm = new_bpm
                    self._beat_interval = interval
                    if self._source != self.SOURCE_OSC:
                        logger.info(f"BPM sync: OSC (Reaper) @ {self._bpm:.0f} BPM")
                    self._source = self.SOURCE_OSC
        self._last_osc_beat = now
        self._last_beat_time = now
        self._beat_count += 1
        self._fire_beat()

    def feed_midi_clock(self):
        """Called on each MIDI clock tick (24 per quarter note)."""
        self._midi_last_seen = time.monotonic()
        if not self._midi_active:
            logger.info("BPM source detected: MIDI clock")
        self._midi_active = True

        self._midi_clock_count += 1
        if self._midi_clock_count >= 24:
            self._midi_clock_count = 0
            now = time.monotonic()

            osc_preferred = self._preferred in ("Reaper (OSC)", "Reaper")
            if osc_preferred and self._osc_active:
                self._last_midi_beat = now
                return

            if self._last_midi_beat > 0:
                interval = now - self._last_midi_beat
                if 0.1 < interval < 5.0:
                    new_bpm = 60.0 / interval
                    if 20 < new_bpm < 300:
                        self._bpm = new_bpm
                        self._beat_interval = interval
                        if self._source != self.SOURCE_MIDI:
                            logger.info(f"BPM sync: MIDI @ {self._bpm:.0f} BPM")
                        self._source = self.SOURCE_MIDI
            self._last_midi_beat = now
            self._last_beat_time = now
            self._beat_count += 1
            self._fire_beat()

    def tick(self, now: float | None = None) -> bool:
        """Returns True on each internal clock beat. Always works as ultimate fallback."""
        if now is None:
            now = time.monotonic()

        if self._preferred == "Reaper" and self._osc_active:
            return False
        if self._preferred == "Reaper" and not self._osc_active and self._midi_active:
            return False
        if self._source not in (self.SOURCE_INTERNAL, self.SOURCE_MIDI):
            if now - self._last_beat_time < self._beat_interval * 2:
                return False

        if now - self._last_beat_time >= self._beat_interval:
            self._last_beat_time = now
            if self._source != self.SOURCE_INTERNAL or self._beat_count == 0:
                if self._source != self.SOURCE_INTERNAL:
                    self._source = self.SOURCE_INTERNAL
            self._beat_count += 1
            self._fire_beat()
            return True
        return False

    @property
    def bpm(self) -> float:
        return self._bpm

    @property
    def source(self) -> str:
        return self._source

    @property
    def beat_count(self) -> int:
        return self._beat_count

    @property
    def beat_interval(self) -> float:
        return self._beat_interval

    def _fire_beat(self):
        if self._on_beat:
            try:
                self._on_beat(self._beat_count)
            except Exception:
                pass
