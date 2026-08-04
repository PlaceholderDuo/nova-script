"""
Minimal TUI for chill mode — toggle demo LEDs on/off.
"""
from textual.app import App, ComposeResult
from textual.widgets import Static, Footer
from textual.reactive import reactive
from textual.binding import Binding


class ChillTUI(App):
    CSS = """
    Screen {
        align: center middle;
    }
    #chill-box {
        width: 40;
        height: 6;
        border: solid $primary;
        padding: 1 2;
        text-align: center;
    }
    """

    BINDINGS = [
        Binding("l", "toggle_leds", "Toggle LEDs"),
        Binding("q", "quit", "Quit"),
    ]

    leds_on = reactive(True)

    def __init__(self, engine_queue):
        super().__init__()
        self._queue = engine_queue

    def compose(self) -> ComposeResult:
        yield Static("", id="chill-box")
        yield Footer()

    def action_toggle_leds(self):
        self.leds_on = not self.leds_on
        self._queue.put({"action": "toggle_leds"})
        self._update_display()

    def watch_leds_on(self, value: bool):
        self._update_display()

    def _update_display(self):
        box = self.query_one("#chill-box", Static)
        state = "ON  ambient patterns" if self.leds_on else "OFF ■ dark"
        box.update(
            f"nova-script · chill mode\n\n"
            f"LEDs: {state}\n\n"
            f"L = toggle   Q = quit"
        )

    def on_mount(self):
        self._update_display()


def run_chill_tui(engine_queue):
    app = ChillTUI(engine_queue)
    app.run()
