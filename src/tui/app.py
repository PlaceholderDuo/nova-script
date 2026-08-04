"""
Nova-Script TUI — profile management, device status, settings, grid mirror.
"""
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container, ScrollableContainer
from textual.widgets import Static, Header, Footer, Button, ListView, ListItem, Label
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.binding import Binding

from src.controllers.color_map import LogicalColor


class GridCell(Static):
    color_name = reactive("off")

    COLORS = {
        "off": "#1a1a2e",
        "red": [("low", "#4a1010"), ("med", "#8b2020"), ("high", "#e03030")],
        "green": [("low", "#104a10"), ("med", "#208b20"), ("high", "#30e030")],
        "amber": [("low", "#4a3a10"), ("med", "#8b6b20"), ("high", "#e0b030")],
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


class SettingsScreen(ModalScreen):
    """Settings modal overlay."""
    CSS = """
        SettingsScreen {
            align: center middle;
        }
        #settings-dialog {
            width: 50;
            height: 20;
            border: thick $primary;
            background: $surface;
            padding: 1;
        }
    """

    BINDINGS = [("escape", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        with Container(id="settings-dialog"):
            yield Static("Settings — coming soon")
            yield Static("Ports, timeouts, BPM, and more will be configurable here.")
            yield Button("Close", variant="primary", id="close-settings")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "close-settings":
            self.dismiss()


class ProfileScreen(ModalScreen):
    """Profile management modal."""
    CSS = """
        ProfileScreen {
            align: center middle;
        }
        #profile-dialog {
            width: 50;
            height: 24;
            border: thick $primary;
            background: $surface;
            padding: 1;
        }
        #profile-list {
            height: 10;
            border: solid $border;
        }
    """

    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, profile_manager):
        super().__init__()
        self._pm = profile_manager

    def compose(self) -> ComposeResult:
        with Container(id="profile-dialog"):
            yield Static("Profiles")
            yield ListView(id="profile-list")
            with Horizontal():
                yield Button("Load", variant="primary", id="load-profile")
                yield Button("Save As...", id="save-profile")
                yield Button("Close", id="close-profiles")

    def on_mount(self):
        lst = self.query_one("#profile-list", ListView)
        for name in self._pm.list():
            lst.append(ListItem(Label(name)))

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "close-profiles":
            self.dismiss()
        elif event.button.id == "load-profile":
            lst = self.query_one("#profile-list", ListView)
            if lst.highlighted_child:
                name = str(lst.highlighted_child.children[0].render())
                self.dismiss(name)
        elif event.button.id == "save-profile":
            self.dismiss("__save__")


class NovaTUI(App):
    CSS = """
    .grid-cell {
        width: 4;
        height: 2;
        content-align: center middle;
        border: solid #2a2a4a;
    }
    #status-bar {
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 1;
    }
    #device-status {
        height: 3;
        padding: 0 1;
        background: $surface;
    }
    #right-panel {
        width: 40;
    }
    #log-panel {
        height: 12;
        border: solid $border;
    }
    #log-content {
        height: 10;
    }
    Button {
        margin: 1 0;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("p", "profiles", "Profiles"),
        Binding("s", "settings", "Settings"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self, engine_queue):
        super().__init__()
        self._engine_queue = engine_queue
        self._grid: LaunchpadGrid | None = None
        self._status: Static | None = None
        self._devices: Static | None = None
        self._log: Static | None = None
        self._log_lines: list[str] = []
        from src.profiles import ProfileManager
        self._pm = ProfileManager()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("Nova-Script v0.1 | Profile: live-show | No device connected", id="status-bar")

        with Horizontal():
            with Vertical():
                self._grid = LaunchpadGrid(8, 8)
                yield self._grid

            with Vertical(id="right-panel"):
                with Container(id="device-status"):
                    yield Static("Devices: scanning...")
                with Container(id="log-panel"):
                    yield Static("Event Log", classes="log-header")
                    yield ScrollableContainer(Static("", id="log-content"))

        yield Footer()

    def on_mount(self):
        self._status = self.query_one("#status-bar", Static)
        self._devices = self.query_one("#device-status Static", Static)
        self._log = self.query_one("#log-content", Static)
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

    def _handle_grid_state(self, msg: dict):
        mode = msg.get("mode", "")
        devices = msg.get("devices", {})

        lp = "✓" if devices.get("Launchpad Mini") else "✗"
        lk = "✓" if devices.get("Launchkey 49") else "✗"
        self._status.update(f"Nova-Script v0.1 | Mode: {mode} | LP:{lp} LK:{lk} OSC:✓")

        if self._devices:
            lines = ["Device Status:"]
            for name, connected in devices.items():
                status = "CONNECTED" if connected else "disconnected"
                lines.append(f"  {name}: {status}")
            self._devices.update("\n".join(lines))

        if self._grid and "grid" in msg:
            self._grid.update_grid(msg["grid"])

    def action_profiles(self):
        def handle(result):
            if result == "__save__":
                self._pm.save("live-show", {})
                self._add_log("Profile saved: live-show")
            elif result:
                self._add_log(f"Profile loaded: {result}")

        self.push_screen(ProfileScreen(self._pm), handle)

    def action_settings(self):
        self.push_screen(SettingsScreen())

    def _add_log(self, text: str):
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_lines.append(f"{ts} {text}")
        if len(self._log_lines) > 50:
            self._log_lines = self._log_lines[-50:]
        if self._log:
            self._log.update("\n".join(self._log_lines))


def run_tui(engine_queue):
    app = NovaTUI(engine_queue)
    app.run()
