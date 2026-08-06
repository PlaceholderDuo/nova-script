import time
from abc import ABC, abstractmethod

from src.controllers.base import GridEvent, ControlEvent, LogicalColor


class Mode(ABC):
    def __init__(self, name: str, grid, controller):
        self.name = name
        self.grid = grid
        self.controller = controller
        self._long_press_ms: int = 500
        self._debounce_ms: int = 80
        self._pending_x: int | None = None
        self._pending_y: int | None = None
        self._pending_time: float = 0.0
        self._last_action_time: float = 0.0
        self._page: int = 0
        self._num_pages: int = 1
        self._needs_render: bool = True

    def mark_dirty(self):
        """Call when visual state changes. Triggers next render."""
        self._needs_render = True

    def render_pages(self):
        """Light right-column buttons as page indicators.
        Amber = total pages, Green = current page.
        Bottom button (H) = page 1, G = page 2, etc.
        Call this in your _render() method."""
        for i in range(8):
            if i < self._num_pages:
                color = LogicalColor.GREEN_HIGH if i == self._page else LogicalColor.AMBER_LOW
                self.controller.send_right_column_led(i, color)
            else:
                self.controller.send_right_column_led(i, LogicalColor.OFF)

    def clear_pages(self):
        for i in range(8):
            self.controller.send_right_column_led(i, LogicalColor.OFF)

    @abstractmethod
    def enter(self):
        ...

    @abstractmethod
    def exit(self):
        ...

    @abstractmethod
    def handle_grid_event(self, event: GridEvent):
        ...

    def handle_control_event(self, event: ControlEvent):
        pass

    def tick(self, delta_ms: float):
        if self._needs_render:
            self._needs_render = False
            self._render()

    def is_debounced(self) -> bool:
        now = time.monotonic() * 1000
        if now - self._last_action_time < self._debounce_ms:
            return True
        self._last_action_time = now
        return False

    def track_press(self, event: GridEvent):
        """Call on GRID_PRESS to track for long-press detection."""
        self._pending_x = event.x
        self._pending_y = event.y
        self._pending_time = time.monotonic()

    def resolve_press(self, event: GridEvent) -> str:
        """Call on GRID_RELEASE. Returns 'short', 'long', or 'invalid'."""
        if self._pending_x is None or self._pending_y is None:
            return "invalid"
        if event.x != self._pending_x or event.y != self._pending_y:
            self._pending_x = None
            self._pending_y = None
            return "invalid"

        elapsed = (time.monotonic() - self._pending_time) * 1000
        self._pending_x = None
        self._pending_y = None

        if elapsed < 0.5:  # sub-millisecond noise filter only
            return "invalid"
        if elapsed >= self._long_press_ms:
            return "long"
        return "short"

    def clear(self):
        self.grid.clear()

    def commit(self):
        for x, y in self.grid.dirty_cells():
            color = self.grid.get_cell(x, y)
            self.controller.set_grid_color(x, y, color)
