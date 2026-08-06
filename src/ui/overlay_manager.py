"""
Overlay Manager — priority-based overlay system.
Screensaver: 3 modes selectable via right column A-C buttons.
Glimmer mode: random red/amber sparkle particles with radial falloff.
"""
import logging
import math
import random
import time
from enum import IntEnum

from src.controllers.base import GridEvent, ControlEvent, LogicalColor
from src.layout.grid import LogicalGrid
from src.ui.image_store import ImageStore
from src.ui.fireworks import Fireworks

logger = logging.getLogger(__name__)


class OverlayPriority(IntEnum):
    ACTIVE_MODE = 1
    SCREENSAVER = 2
    HUD = 3
    FIREWORKS = 4


OVERLAY_NAMES = {
    OverlayPriority.ACTIVE_MODE: "mode",
    OverlayPriority.SCREENSAVER: "screensaver",
    OverlayPriority.HUD: "hud",
    OverlayPriority.FIREWORKS: "fireworks",
}

SCREENSAVER_MODES = ["heart", "waves", "glimmer"]
MODE_IMAGES = {"heart": 1, "waves": 0}


class Sparkle:
    def __init__(self, now: float):
        self.x = random.random() * 8
        self.y = random.random() * 8
        self.birth = now
        self.lifetime = random.uniform(0.3, 0.9)
        self.peak = random.uniform(0.05, 0.18)
        self.is_amber = random.random() < 0.4
        self.strength = random.uniform(0.6, 1.0)

    def alive(self, now: float) -> bool:
        return now - self.birth < self.lifetime

    def intensity(self, now: float) -> float:
        age = now - self.birth
        if age < 0:
            return 0.0
        if age < self.peak:
            curve = age / self.peak
        else:
            tail = self.lifetime - self.peak
            if tail <= 0:
                return 0.0
            curve = 1.0 - (age - self.peak) / tail
        return max(0.0, curve) * self.strength

    def brightness_at(self, px: int, py: int, now: float) -> LogicalColor:
        base = self.intensity(now)
        if base <= 0.0:
            return LogicalColor.OFF
        dx = self.x - (px + 0.5)
        dy = self.y - (py + 0.5)
        dist = math.sqrt(dx * dx + dy * dy)
        if dist <= 0.5:
            spatial = 1.0
        elif dist <= 1.5:
            spatial = 0.55
        elif dist <= 2.5:
            spatial = 0.22
        else:
            return LogicalColor.OFF
        v = base * spatial
        if v > 0.6:
            return LogicalColor.AMBER_HIGH if self.is_amber else LogicalColor.RED_HIGH
        elif v > 0.28:
            return LogicalColor.AMBER_MED if self.is_amber else LogicalColor.RED_MED
        elif v > 0.08:
            return LogicalColor.AMBER_LOW if self.is_amber else LogicalColor.RED_LOW
        return LogicalColor.OFF


class OverlayManager:
    def __init__(
        self,
        grid: LogicalGrid,
        controller,
        image_store: ImageStore,
        idle_timeout_ms: int = 30000,
        bpm: float = 120.0,
    ):
        self.grid = grid
        self.controller = controller
        self.image_store = image_store
        self.idle_timeout_ms = idle_timeout_ms
        self.bpm = bpm

        self._active: OverlayPriority = OverlayPriority.ACTIVE_MODE
        self._previous: OverlayPriority = OverlayPriority.ACTIVE_MODE
        self._previous_mode_name: str = ""
        self._dismissed: bool = False
        self._idle_since: float = 0.0

        self._fireworks: Fireworks | None = None
        self._hud_message: str = ""
        self._hud_timeout: float = 0.0
        self._hud_duration_ms: int = 1500

        self._screensaver_modes: list[str] = SCREENSAVER_MODES[:]
        self._active_screensaver_mode: int = 0
        self._brightness_pct: int = 100

        self._sparkles: list[Sparkle] = []
        self._next_sparkle: float = 0.0

    @property
    def active(self) -> OverlayPriority:
        return self._active

    @property
    def is_overlay_active(self) -> bool:
        return self._active != OverlayPriority.ACTIVE_MODE

    def start(self):
        self._idle_since = time.monotonic()

    def set_mode_context(self, mode_name: str):
        self._previous_mode_name = mode_name

    # ── Triggering ───────────────────────────────────

    def trigger_screensaver(self):
        self._enter_overlay(OverlayPriority.SCREENSAVER)
        self._render_screensaver()

    def trigger_fireworks(self):
        self._fireworks = Fireworks(bpm=self.bpm, bars=8)
        self._fireworks.start()
        self._enter_overlay(OverlayPriority.FIREWORKS)

    def trigger_hud(self, text: str = "", image_id: int | None = None, char: str = ""):
        if char:
            self._hud_message = char
        elif text:
            self._hud_message = text.upper()
        elif image_id is not None:
            self.image_store.render_to_grid(image_id, self.grid)
            self._commit()
            self._hud_message = ""
        self._hud_timeout = time.monotonic()
        self._enter_overlay(OverlayPriority.HUD)

    # ── Event handling ────────────────────────────────

    def handle_grid_event(self, event: GridEvent) -> bool:
        if not event.pressed:
            return False
        if self._active == OverlayPriority.ACTIVE_MODE:
            return False
        if not self._dismissed:
            self._dismiss_overlay()
            self._dismissed = True
            return True
        self._dismissed = False
        self._enter_overlay(OverlayPriority.ACTIVE_MODE)
        return False

    def handle_control_event(self, event: ControlEvent) -> bool:
        is_press = "PRESS" in event.event_type.name
        if not is_press:
            return False
        if self._active == OverlayPriority.ACTIVE_MODE:
            return False

        # Screensaver: right column buttons switch mode
        if self._active == OverlayPriority.SCREENSAVER and 100 <= event.control_id < 108:
            idx = event.control_id - 100
            if 0 <= idx < len(self._screensaver_modes):
                self._active_screensaver_mode = idx
                self._sparkles.clear()
                self._render_screensaver()
                return True

        # Normal dismiss behaviour for all other controls
        if not self._dismissed:
            self._dismiss_overlay()
            self._dismissed = True
            return True
        self._dismissed = False
        self._enter_overlay(OverlayPriority.ACTIVE_MODE)
        return False

    # ── Tick ──────────────────────────────────────────

    def tick(self, delta_ms: float, now: float | None = None):
        if now is None:
            now = time.monotonic()
        self._check_idle(now)
        if self._active == OverlayPriority.FIREWORKS:
            self._tick_fireworks(now)
        elif self._active == OverlayPriority.HUD:
            self._tick_hud(now)
        elif self._active == OverlayPriority.SCREENSAVER:
            self._tick_screensaver(now)

    # ── Private: overlay lifecycle ────────────────────

    def _enter_overlay(self, priority: OverlayPriority):
        if priority == self._active:
            return
        self._previous = self._active
        self._dismissed = False
        self._active = priority
        name = OVERLAY_NAMES.get(priority, "unknown")
        prev = OVERLAY_NAMES.get(self._previous, "?")
        logger.info(f"Overlay: {prev} → {name}")

    def _dismiss_overlay(self):
        name = OVERLAY_NAMES.get(self._active, "?")
        logger.info(f"Overlay dismissed: {name}")

    def _check_idle(self, now: float):
        if self._active != OverlayPriority.ACTIVE_MODE:
            return
        idle_ms = (now - self._idle_since) * 1000
        if idle_ms >= self.idle_timeout_ms:
            self.trigger_screensaver()

    def mark_activity(self):
        self._idle_since = time.monotonic()

    # ── Fireworks ─────────────────────────────────────

    def _tick_fireworks(self, now: float):
        if self._fireworks is None:
            self._fireworks = Fireworks(bpm=self.bpm, bars=8)
            self._fireworks.start()
        active = self._fireworks.tick(now)
        self._fireworks.render(self.grid)
        self._commit()
        if not active:
            logger.info("Fireworks complete → screensaver")
            self._fireworks = None
            self.trigger_screensaver()

    # ── HUD ───────────────────────────────────────────

    def _tick_hud(self, now: float):
        elapsed = (now - self._hud_timeout) * 1000
        if elapsed >= self._hud_duration_ms:
            self._auto_dismiss_to_previous()
            return
        if self._hud_message:
            self.grid.clear()
            from src.ui.modes.message import FONT_5X5
            char = self._hud_message[0]
            glyph = FONT_5X5.get(char, FONT_5X5.get("?", ["00000"] * 5))
            for row in range(5):
                for col in range(5):
                    if glyph[row][col] == "1":
                        x = col + 1
                        y = 6 - row
                        if 0 <= x < 8 and 0 <= y < 8:
                            self.grid.set_cell(x, y, LogicalColor.AMBER_HIGH)
            self._commit()

    # ── Screensaver ───────────────────────────────────

    def _tick_screensaver(self, now: float):
        mode = self._screensaver_modes[self._active_screensaver_mode]
        self.grid.clear()

        if mode == "glimmer":
            self._tick_glimmer(now)
        elif mode in MODE_IMAGES:
            self._render_image(MODE_IMAGES[mode])

        self._render_screensaver_controls()
        self._commit()

    def _tick_glimmer(self, now: float):
        if now >= self._next_sparkle:
            self._sparkles.append(Sparkle(now))
            interval = random.uniform(0.2, 1.2)
            if random.random() < 0.15:
                interval = random.uniform(0.05, 0.15)
                self._sparkles.append(Sparkle(now))
            self._next_sparkle = now + interval

        self._sparkles = [s for s in self._sparkles if s.alive(now)]
        if len(self._sparkles) > 8:
            self._sparkles = self._sparkles[-8:]

        brightness: dict[tuple[int, int], LogicalColor] = {}
        for sparkle in self._sparkles:
            for px in range(8):
                for py in range(8):
                    c = sparkle.brightness_at(px, py, now)
                    if c != LogicalColor.OFF:
                        key = (px, py)
                        if key not in brightness or c.value > brightness[key].value:
                            brightness[key] = c

        for (px, py), color in brightness.items():
            self.grid.set_cell(px, py, color)

    def _render_image(self, image_id: int):
        img = self.image_store.get_image(image_id)
        if img is None:
            return
        for y, row in enumerate(img):
            dy = 7 - y
            for x, color in enumerate(row):
                dimmed = self.dim_color(color, self._brightness_pct)
                self.grid.set_cell(x, dy, dimmed)

    def _render_screensaver_controls(self):
        for i in range(8):
            if i < len(self._screensaver_modes):
                color = LogicalColor.AMBER_HIGH if i == self._active_screensaver_mode else LogicalColor.AMBER_LOW
                if i == self._active_screensaver_mode:
                    color = self.dim_color(color, 80)
                else:
                    color = self.dim_color(color, 20)
                self.controller.send_right_column_led(i, color)
            else:
                self.controller.send_right_column_led(i, LogicalColor.OFF)

    def _render_screensaver(self):
        self._tick_screensaver(time.monotonic())

    # ── Private: helpers ──────────────────────────────

    def _auto_dismiss_to_previous(self):
        if self._previous == OverlayPriority.SCREENSAVER:
            self.trigger_screensaver()
        else:
            self._enter_overlay(OverlayPriority.ACTIVE_MODE)

    def _commit(self):
        for x, y in self.grid.dirty_cells():
            color = self.grid.get_cell(x, y)
            self.controller.set_grid_color(x, y, color)

    def set_screensaver_cycle(self, enabled: bool):
        pass  # deprecated — modes are always available

    def set_bpm(self, bpm: float):
        self.bpm = bpm

    def set_screensaver_brightness(self, pct: int):
        self._brightness_pct = max(0, min(100, pct))

    @staticmethod
    def dim_color(color: LogicalColor, pct: int) -> LogicalColor:
        if color == LogicalColor.OFF:
            return LogicalColor.OFF
        name = color.name
        if "_HIGH" in name:
            if pct <= 33:
                return LogicalColor[name.replace("_HIGH", "_LOW")]
            elif pct <= 66:
                return LogicalColor[name.replace("_HIGH", "_MED")]
            return color
        elif "_MED" in name:
            if pct <= 33:
                return LogicalColor[name.replace("_MED", "_LOW")]
            elif pct <= 66:
                return color
            return LogicalColor[name.replace("_MED", "_HIGH")]
        elif "_LOW" in name:
            if pct <= 33:
                return color
            elif pct <= 66:
                return LogicalColor[name.replace("_LOW", "_MED")]
            return LogicalColor[name.replace("_LOW", "_HIGH")]
        return color
