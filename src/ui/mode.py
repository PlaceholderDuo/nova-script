from abc import ABC, abstractmethod

from src.controllers.base import GridEvent, ControlEvent, LogicalColor


class Mode(ABC):
    def __init__(self, name: str, grid, controller):
        self.name = name
        self.grid = grid
        self.controller = controller

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
        pass

    def clear(self):
        self.grid.clear()

    def commit(self):
        for x, y in self.grid.dirty_cells():
            color = self.grid.get_cell(x, y)
            self.controller.set_grid_color(x, y, color)
