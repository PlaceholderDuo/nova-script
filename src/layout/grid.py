from dataclasses import dataclass
from typing import Callable, Optional

from src.controllers.color_map import LogicalColor


@dataclass
class Cell:
    x: int
    y: int
    color: LogicalColor = LogicalColor.OFF


class LogicalGrid:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self._cells: dict[tuple[int, int], LogicalColor] = {}
        self._dirty: set[tuple[int, int]] = set()
        self._on_cell_changed: Optional[Callable] = None

    def set_on_cell_changed(self, callback: Callable):
        self._on_cell_changed = callback

    def set_cell(self, x: int, y: int, color: LogicalColor):
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        key = (x, y)
        if self._cells.get(key) != color:
            self._cells[key] = color
            self._dirty.add(key)
            if self._on_cell_changed:
                self._on_cell_changed(x, y, color)

    def get_cell(self, x: int, y: int) -> LogicalColor:
        return self._cells.get((x, y), LogicalColor.OFF)

    def clear(self):
        for y in range(self.height):
            for x in range(self.width):
                self.set_cell(x, y, LogicalColor.OFF)

    def fill_rect(self, x: int, y: int, w: int, h: int, color: LogicalColor):
        for dy in range(h):
            for dx in range(w):
                self.set_cell(x + dx, y + dy, color)

    def fill_row(self, y: int, color: LogicalColor):
        self.fill_rect(0, y, self.width, 1, color)

    def fill_column(self, x: int, color: LogicalColor, start_y: int = 0, end_y: Optional[int] = None):
        if end_y is None:
            end_y = self.height
        for y in range(max(0, start_y), min(self.height, end_y)):
            self.set_cell(x, y, color)

    def draw_text_horizontal(self, x: int, y: int, text: str, color: LogicalColor):
        for i, ch in enumerate(text):
            if x + i >= self.width:
                break
            if ch != " ":
                self.set_cell(x + i, y, color)

    def draw_bar_vertical(
        self,
        x: int,
        value: float,
        max_height: int,
        active_color: LogicalColor,
        inactive_color: LogicalColor = LogicalColor.OFF,
        start_y: int = 0,
    ):
        filled = int(value * max_height)
        filled = max(0, min(max_height, filled))
        for y in range(max_height):
            color = active_color if y < filled else inactive_color
            self.set_cell(x, start_y + y, color)

    def dirty_cells(self) -> set[tuple[int, int]]:
        d = self._dirty
        self._dirty = set()
        return d

    def snapshot(self) -> list[list[LogicalColor]]:
        grid = [
            [self._cells.get((x, y), LogicalColor.OFF) for x in range(self.width)]
            for y in range(self.height)
        ]
        return grid
