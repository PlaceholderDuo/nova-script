import time
from typing import Optional

from src.controllers.base import GridEvent, ControlEvent, LogicalColor
from src.ui.mode import Mode


class MenuMode(Mode):
    def __init__(self, grid, controller, on_mode_select=None):
        super().__init__("menu", grid, controller)
        self._on_mode_select = on_mode_select
        self._items: list[dict] = []
        self._selected_index: int = -1
        self._last_press_time: float = 0.0
        self._debounce_ms: int = 100
        self._page: int = 0
        self._items_per_page: int = 8

    def set_items(self, items: list[dict]):
        self._items = items
        self._page = 0
        self._selected_index = -1

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

        start_idx = self._page * self._items_per_page
        item_idx = start_idx + event.x + event.y * 8

        if item_idx < len(self._items):
            item = self._items[item_idx]
            if self._on_mode_select and "mode" in item:
                self._on_mode_select(item["mode"])

    def handle_control_event(self, event: ControlEvent):
        if not event.event_type.name.endswith("_PRESS"):
            return

        if event.control_id >= 200:
            top_idx = event.control_id - 200
            if top_idx < len(self._items):
                item = self._items[top_idx]
                if self._on_mode_select and "mode" in item:
                    self._on_mode_select(item["mode"])

        elif event.control_id >= 100:
            col_idx = event.control_id - 100
            total_pages = (len(self._items) - 1) // self._items_per_page + 1
            self._page = (self._page + 1) % total_pages
            self._render()

    def _render(self):
        self.clear()
        start_idx = self._page * self._items_per_page

        for i in range(min(self._items_per_page, len(self._items) - start_idx)):
            item = self._items[start_idx + i]
            x = i % 8
            y = i // 8
            color_name = item.get("color", "AMBER_HIGH")
            color = LogicalColor[color_name]
            self.grid.set_cell(x, y, color)

        self.commit()
