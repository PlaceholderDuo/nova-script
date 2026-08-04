"""
Menu Mode — spatially arranged 2×2 mode blocks with distinct colors.
"""
import time

from src.controllers.base import GridEvent, ControlEvent, LogicalColor
from src.ui.mode import Mode


class MenuMode(Mode):
    def __init__(self, grid, controller, on_mode_select=None):
        super().__init__("menu", grid, controller)
        self._on_mode_select = on_mode_select
        self._items: list[dict] = []
        self._last_press_time: float = 0.0
        self._debounce_ms: int = 100

    def set_items(self, items: list[dict]):
        self._items = items

    def enter(self):
        self._render()

    def exit(self):
        self.clear()
        self.commit()

    def handle_grid_event(self, event: GridEvent):
        if not event.pressed:
            return

        now = time.monotonic() * 1000
        if now - self._last_press_time < self._debounce_ms:
            return
        self._last_press_time = now

        for item in self._items:
            ix = item.get("x", 0)
            iy = item.get("y", 0)
            iw = item.get("w", 1)
            ih = item.get("h", 1)

            if ix <= event.x < ix + iw and iy <= event.y < iy + ih:
                if self._on_mode_select and "mode" in item:
                    self._on_mode_select(item["mode"])
                return

    def handle_control_event(self, event: ControlEvent):
        if not event.event_type.name.endswith("_PRESS"):
            return

        if event.control_id >= 200:
            top_idx = event.control_id - 200
            if top_idx < len(self._items):
                item = self._items[top_idx]
                if self._on_mode_select and "mode" in item:
                    self._on_mode_select(item["mode"])

    def _render(self):
        self.clear()
        for item in self._items:
            ix = item.get("x", 0)
            iy = item.get("y", 0)
            iw = item.get("w", 1)
            ih = item.get("h", 1)
            color_name = item.get("color", "AMBER_HIGH")
            color = LogicalColor[color_name]

            for dy in range(ih):
                for dx in range(iw):
                    if 0 <= ix + dx < 8 and 0 <= iy + dy < 8:
                        self.grid.set_cell(ix + dx, iy + dy, color)
        self.commit()
