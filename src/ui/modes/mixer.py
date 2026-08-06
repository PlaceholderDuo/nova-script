"""
Mixer Mode — track volume faders + mute + reverb sends.
"""
from src.controllers.base import GridEvent, ControlEvent, LogicalColor
from src.ui.mode import Mode


class MixerMode(Mode):
    def __init__(self, grid, controller, osc_bridge=None):
        super().__init__("mixer", grid, controller)
        self.osc_bridge = osc_bridge
        self._track_count = 8
        self._volumes = [0.75] * self._track_count
        self._muted = [False] * self._track_count
        self._reverb_send = [0] * self._track_count
        self._fader_rows = 6

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

        if event.y == 0:
            self._reverb_send[event.x] = (self._reverb_send[event.x] + 1) % 3
            self._send_reverb_osc(event.x)
        elif 1 <= event.y <= self._fader_rows:
            new_vol = (event.y) / self._fader_rows
            self._volumes[event.x] = new_vol
        elif event.y == self._fader_rows + 1:
            self._muted[event.x] = not self._muted[event.x]

        self._render()

    def handle_control_event(self, event: ControlEvent):
        pass

    def _send_reverb_osc(self, track: int):
        if not self.osc_bridge:
            return
        level = self._reverb_send[track]
        self.osc_bridge.send(f"/track/{track + 1}/fx/rev/send", level / 2.0)

    def _render(self):
        self.clear()

        for track in range(self._track_count):
            vol = self._volumes[track]
            filled = int(vol * self._fader_rows)

            for row in range(1, self._fader_rows + 1):
                if row <= filled:
                    color = LogicalColor.GREEN_MED
                else:
                    color = LogicalColor.OFF

                if row == filled and filled > 0:
                    color = LogicalColor.GREEN_HIGH

                self.grid.set_cell(track, row, color)

            mute_color = LogicalColor.RED_HIGH if self._muted[track] else LogicalColor.AMBER_LOW
            self.grid.set_cell(track, self._fader_rows + 1, mute_color)

            rev_level = self._reverb_send[track]
            if rev_level == 0:
                rev_color = LogicalColor.OFF
            elif rev_level == 1:
                rev_color = LogicalColor.AMBER_MED
            else:
                rev_color = LogicalColor.GREEN_HIGH
            self.grid.set_cell(track, 0, rev_color)

        self.commit()
