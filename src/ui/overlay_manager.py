"""
Overlay Manager — priority-based overlay system.

Manages: Fireworks → HUD → Screensaver → Active Mode.
First button press on any overlay is consumed (dismisses overlay).
Second press flows to the active mode.
"""
import logging
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
        self._screensaver_image: int = 0
        self._screensaver_cycle: bool = False
        self._screensaver_cycle_index: int = 0
        self._screensaver_last_cycle: float = 0.0
        self._screensaver_cycle_interval: float = 4.0
        self._brightness_pct: int = 100

    @property
    def active(self) -> OverlayPriority:
        return self._active

    @property
    def is_overlay_active(self) -> bool:
        return self._active != OverlayPriority.ACTIVE_MODE

    def start(self):
        """Start idle tracking."""
        self._idle_since = time.monotonic()
        self._screensaver_image = self.image_store.last_image

    def set_mode_context(self, mode_name: str):
        """Called when active mode changes."""
        self._previous_mode_name = mode_name

    # ── Triggering ───────────────────────────────────

    def trigger_screensaver(self):
        self._enter_overlay(OverlayPriority.SCREENSAVER)
        self._screensaver_last_cycle = time.monotonic()
        self._render_screensaver_image()

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
        """Returns True if event was consumed by overlay."""
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
        """Returns True if event was consumed by overlay."""
        is_press = "PRESS" in event.event_type.name
        if not is_press:
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

    # ── Tick ──────────────────────────────────────────

    def tick(self, delta_ms: float, now: float | None = None):
        """Called each engine tick. Updates active overlay rendering."""
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

    # ── Private: idle detection ───────────────────────

    def _check_idle(self, now: float):
        if self._active != OverlayPriority.ACTIVE_MODE:
            return
        idle_ms = (now - self._idle_since) * 1000
        if idle_ms >= self.idle_timeout_ms:
            self.trigger_screensaver()

    def mark_activity(self):
        self._idle_since = time.monotonic()

    # ── Private: fireworks tick ───────────────────────

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

    # ── Private: HUD tick ─────────────────────────────

    def _tick_hud(self, now: float):
        elapsed = (now - self._hud_timeout) * 1000
        if elapsed >= self._hud_duration_ms:
            self._auto_dismiss_to_previous()
            return

        if self._hud_message:
            self.grid.clear()
            from src.ui.modes.message import FONT_5X5

            msg = self._hud_message[:1] if len(self._hud_message) <= 1 else self._hud_message[:8]
            char = msg[0] if msg else "?"
            glyph = FONT_5X5.get(char, FONT_5X5.get("?", ["00000"] * 5))

            for row in range(5):
                for col in range(5):
                    if glyph[row][col] == "1":
                        x = col + 1
                        y = 6 - row
                        if 0 <= x < 8 and 0 <= y < 8:
                            self.grid.set_cell(x, y, LogicalColor.AMBER_HIGH)
            self._commit()

    # ── Private: screensaver tick ─────────────────────

    def _tick_screensaver(self, now: float):
        if self._screensaver_cycle:
            if now - self._screensaver_last_cycle >= self._screensaver_cycle_interval:
                self._screensaver_last_cycle = now
                self._screensaver_cycle_index = (self._screensaver_cycle_index + 1) % 2
                img_id = self.image_store.get_quick_slot(self._screensaver_cycle_index)
                if img_id is not None:
                    self._screensaver_image = img_id
                    self._render_screensaver_image()

    def _render_screensaver_image(self):
        img = self.image_store.get_image(self._screensaver_image)
        if img is None:
            return
        self.grid.clear()
        for y, row in enumerate(img):
            display_y = 7 - y
            for x, color in enumerate(row):
                dimmed = self.dim_color(color, self._brightness_pct)
                self.grid.set_cell(x, display_y, dimmed)
        self._commit()

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
        self._screensaver_cycle = enabled

    def set_bpm(self, bpm: float):
        self.bpm = bpm

    def set_screensaver_brightness(self, pct: int):
        self._brightness_pct = max(0, min(100, pct))

    @staticmethod
    def dim_color(color: LogicalColor, pct: int) -> LogicalColor:
        """Map a LogicalColor to appropriate brightness based on percentage.
        MK1: 0-33%=LOW, 34-66%=MED, 67-100%=HIGH. OFF stays OFF."""
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
