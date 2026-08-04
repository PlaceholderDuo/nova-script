from src.controllers.base import GridEvent, ControlEvent, LogicalColor
from src.ui.mode import Mode


class MixerMode(Mode):
    def __init__(self, grid, controller):
        super().__init__("mixer", grid, controller)
        self._track_count = 8
        self._volumes = [0.75] * self._track_count
        self._muted = [False] * self._track_count
        self._fader_rows = 7

    def enter(self):
        self._render()

    def exit(self):
        self.clear()
        self.commit()

    def handle_grid_event(self, event: GridEvent):
        if not event.pressed:
            return

        if event.x >= self._track_count:
            return

        if event.y < self._fader_rows:
            new_vol = (event.y + 1) / self._fader_rows
            self._volumes[event.x] = new_vol
        elif event.y == self._fader_rows:
            self._muted[event.x] = not self._muted[event.x]

        self._render()

    def handle_control_event(self, event: ControlEvent):
        pass

    def _render(self):
        self.clear()

        for track in range(self._track_count):
            vol = self._volumes[track]
            filled = int(vol * self._fader_rows)

            for row in range(self._fader_rows):
                if row < filled:
                    color = LogicalColor.GREEN_MED
                else:
                    color = LogicalColor.OFF

                if row == filled - 1 and filled > 0:
                    color = LogicalColor.GREEN_HIGH

                self.grid.set_cell(track, row, color)

            mute_color = LogicalColor.RED_HIGH if self._muted[track] else LogicalColor.AMBER_LOW
            self.grid.set_cell(track, self._fader_rows, mute_color)

        self.commit()
