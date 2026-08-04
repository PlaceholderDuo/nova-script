from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import Static, Header, Footer
from textual.reactive import reactive
from textual import events


from src.controllers.color_map import LogicalColor


class GridCell(Static):
    color_name = reactive("off")

    COLORS = {
        "off": "#1a1a2e",
        "red": [("low", "#4a1010"), ("med", "#8b2020"), ("high", "#e03030")],
        "green": [("low", "#104a10"), ("med", "#208b20"), ("high", "#30e030")],
        "amber": [("low", "#4a3a10"), ("med", "#8b6b20"), ("high", "#e0b030")],
        "yellow": [("low", "#4a4a10"), ("med", "#8b8b20"), ("high", "#e0e030")],
        "orange": [("low", "#4a2a10"), ("med", "#8b4a20"), ("high", "#e07030")],
        "white": [("low", "#3a3a3a"), ("med", "#7a7a7a"), ("high", "#d0d0d0")],
        "blue": [("low", "#10104a"), ("med", "#20208b"), ("high", "#3030e0")],
        "purple": [("low", "#3a104a"), ("med", "#6b208b"), ("high", "#a030e0")],
        "cyan": [("low", "#104a4a"), ("med", "#208b8b"), ("high", "#30e0e0")],
    }

    def render(self) -> str:
        return "  "

    def watch_color_name(self, color_name: str):
        bg = "#1a1a2e"
        if color_name and color_name != "off":
            parts = color_name.lower().split("_")
            if len(parts) >= 2:
                base = parts[0]
                brightness = parts[1]
                for entry in self.COLORS.get(base, []):
                    if entry[0] == brightness:
                        bg = entry[1]
                        break
        self.styles.background = bg


class LaunchpadGrid(Vertical):
    def __init__(self, width: int = 8, height: int = 8):
        super().__init__()
        self.grid_width = width
        self.grid_height = height
        self.cells: list[list[GridCell]] = []

    def compose(self) -> ComposeResult:
        for _ in range(self.grid_height):
            row_cells = []
            with Horizontal():
                for x in range(self.grid_width):
                    cell = GridCell(classes="grid-cell")
                    row_cells.append(cell)
                    yield cell
            self.cells.append(row_cells)

    def update_cell(self, x: int, y: int, color_name: str):
        if 0 <= y < len(self.cells) and 0 <= x < len(self.cells[y]):
            self.cells[y][x].color_name = color_name

    def update_grid(self, grid_data):
        for y, row in enumerate(grid_data):
            for x, val in enumerate(row):
                color = "off"
                if isinstance(val, LogicalColor) and val != LogicalColor.OFF:
                    color = val.name.lower()
                self.update_cell(x, y, color)


class NovaTUI(App):
    CSS = """
    .grid-cell {
        width: 4;
        height: 2;
        content-align: center middle;
        border: solid #2a2a4a;
    }
    #mode-label {
        text-align: center;
        background: #2a2a4a;
        padding: 1;
        margin: 1 0;
    }
    #device-status {
        height: 3;
        background: #1a1a2e;
        padding: 0 1;
    }
    LaunchpadGrid {
        align: center middle;
        margin: 1 0;
    }
    Screen {
        align: center middle;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def __init__(self, engine_queue):
        super().__init__()
        self._engine_queue = engine_queue
        self._grid: LaunchpadGrid | None = None
        self._mode_label: Static | None = None
        self._device_label: Static | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="main-container"):
            yield Static("Nova-Script - No device connected", id="mode-label")
            self._grid = LaunchpadGrid(8, 8)
            yield self._grid
            yield Static("Devices: scanning...", id="device-status")
        yield Footer()

    def on_mount(self):
        self._mode_label = self.query_one("#mode-label", Static)
        self._device_label = self.query_one("#device-status", Static)
        self.set_interval(0.05, self._poll_engine)

    def _poll_engine(self):
        from queue import Empty
        try:
            while True:
                msg = self._engine_queue.get_nowait()
                if msg["type"] == "grid_state":
                    self._handle_grid_state(msg)
        except Empty:
            pass
        except Exception:
            pass

    def _handle_grid_state(self, msg: dict):
        if self._mode_label:
            self._mode_label.update(f"Mode: {msg.get('mode', 'none')} | Nova-Script")

        if self._device_label:
            devices = msg.get("devices", {})
            for name, connected in devices.items():
                status = "CONNECTED" if connected else "disconnected"
                self._device_label.update(f"{name}: {status}")

        if self._grid and "grid" in msg:
            self._grid.update_grid(msg["grid"])


def run_tui(engine_queue):
    app = NovaTUI(engine_queue)
    app.run()
