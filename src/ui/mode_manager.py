import logging
from typing import Optional

from src.ui.mode import Mode
from src.controllers.base import LogicalColor

logger = logging.getLogger(__name__)


class ModeManager:
    def __init__(self, grid, controller):
        self.grid = grid
        self.controller = controller
        self._modes: dict[str, Mode] = {}
        self._active_mode: Optional[Mode] = None
        self._active_mode_name: str = ""
        self._previous_mode_name: str = ""

    def register(self, mode: Mode):
        self._modes[mode.name] = mode
        logger.info(f"Registered mode: {mode.name}")

    def switch_to(self, mode_name: str):
        if mode_name not in self._modes:
            logger.warning(f"Unknown mode: {mode_name}")
            return

        if self._active_mode:
            if self._active_mode_name == mode_name:
                return
            self._previous_mode_name = self._active_mode_name
            self._active_mode.exit()

        self._active_mode_name = mode_name
        self._active_mode = self._modes[mode_name]
        logger.info(f"Switched to mode: {mode_name}")
        self._active_mode.enter()

    def switch_back(self):
        if self._previous_mode_name:
            self.switch_to(self._previous_mode_name)

    def handle_grid_event(self, event):
        if self._active_mode:
            self._active_mode.handle_grid_event(event)

    def handle_control_event(self, event):
        if self._active_mode:
            self._active_mode.handle_control_event(event)

    def tick(self, delta_ms: float):
        if self._active_mode:
            self._active_mode.tick(delta_ms)

    @property
    def active_mode_name(self) -> str:
        return self._active_mode_name

    @property
    def active_mode(self) -> Optional[Mode]:
        return self._active_mode
