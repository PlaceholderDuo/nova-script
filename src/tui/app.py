"""
Nova-Script TUI — profile management, device status, settings, grid mirror.
"""
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container, ScrollableContainer
from textual.widgets import Static, Header, Footer, Button, ListView, ListItem, Label, Select, Input
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
    """Settings modal — configurable BPM clock sources, timeouts, etc."""
    CSS = """
        SettingsScreen {
            align: center middle;
        }
        #settings-dialog {
            width: 58;
            height: 32;
            border: thick $primary;
            background: $surface;
            padding: 1 2;
        }
        .setting-row {
            height: 3;
            margin: 1 0;
        }
        .setting-label {
            width: 16;
            padding: 0 1;
        }
        Select {
            width: 38;
            margin: 0 1;
        }
    """

    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, config: dict, profile_name: str):
        super().__init__()
        self._config = config
        self._profile_name = profile_name

    def compose(self) -> ComposeResult:
        import rtmidi
        sources = ["Reaper (OSC)", "Internal"]
        try:
            mi = rtmidi.MidiIn()
            for p in mi.get_ports():
                if p not in sources:
                    sources.append(p)
            mi.delete()
        except Exception:
            pass

        clock = self._config.get("midi", {}).get("clock", {})
        preferred = clock.get("preferred", "Reaper (OSC)")
        fallback = clock.get("fallback", "Internal")
        bpm = clock.get("internal_bpm", 120)
        idle = self._config.get("ui", {}).get("idle_timeout_ms", 30000)
        downbeat = self._config.get("ui", {}).get("downbeat_flash", "tempo_led")
        downbeat_color = self._config.get("ui", {}).get("downbeat_color", "GREEN_HIGH")
        hints_on = self._config.get("ui", {}).get("hints_enabled", True)

        pref_options = [(s, s) for s in sources]
        fallback_options = [(s, s) for s in sources]
        downbeat_options = [
            ("Tempo LED (beat 1 distinct)", "tempo_led"),
            ("4 corners flash", "4 corners"),
            ("Disable", "disable"),
        ]
        downbeat_color_opts = [(c, c) for c in ["GREEN_HIGH", "RED_HIGH", "AMBER_HIGH", "GREEN_MED", "RED_MED", "AMBER_MED"]]
        hints_options = [("ON", True), ("OFF", False)]

        with Container(id="settings-dialog"):
            yield Static("⚙ Settings — nova-script")
            yield Static("")

            yield Static("— Clock —")
            with Horizontal(classes="setting-row"):
                yield Static("Preferred source:", classes="setting-label")
                yield Select(pref_options, prompt=preferred, value=preferred, id="preferred-select")
            with Horizontal(classes="setting-row"):
                yield Static("Fallback source:", classes="setting-label")
                yield Select(fallback_options, prompt=fallback, value=fallback, id="fallback-select")
            yield Static(f"  Internal BPM: {bpm}   |   Idle timeout: {idle // 1000}s")
            yield Static("")

            yield Static("— Visual —")
            with Horizontal(classes="setting-row"):
                yield Static("Downbeat flash:", classes="setting-label")
                yield Select(downbeat_options, prompt=downbeat, value=downbeat, id="downbeat-select")
            with Horizontal(classes="setting-row"):
                yield Static("Downbeat color:", classes="setting-label")
                yield Select(downbeat_color_opts, prompt=downbeat_color, value=downbeat_color, id="downbeat-color-select")
            with Horizontal(classes="setting-row"):
                yield Static("Visual hints:", classes="setting-label")
                yield Select(hints_options, prompt="ON" if hints_on else "OFF", value=hints_on, id="hints-select")
            yield Static("")
            yield Static("— ARP —")
            arp_transpose = self._config.get("arp", {}).get("diatonic", True)
            arp_transpose_options = [("Diatonic (in-key)", True), ("Chromatic (absolute)", False)]
            with Horizontal(classes="setting-row"):
                yield Static("Transpose mode:", classes="setting-label")
                yield Select(arp_transpose_options, prompt="Diatonic" if arp_transpose else "Chromatic", value=arp_transpose, id="arp-transpose-select")
            yield Static(f"  Current profile: {self._profile_name}")
            yield Static("")
            yield Static("— OSC —")
            osc_scroll = self._config.get("osc", {}).get("scroll_speed_ms", 60)
            with Horizontal(classes="setting-row"):
                yield Static("Msg char speed (ms):", classes="setting-label")
                yield Input(value=str(osc_scroll), placeholder="10-500", id="osc-scroll-speed")
            yield Static("  Per-character scroll speed for OSC text messages (10–500ms)")
            yield Static("")
            with Horizontal():
                yield Button("Save & Close", variant="primary", id="save-settings")
                yield Button("Mixer Setup", id="open-mixer")
                yield Button("Cancel", id="close-settings")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "close-settings":
            self.dismiss()
        elif event.button.id == "save-settings":
            ui = self._config.setdefault("ui", {})
            midi = self._config.setdefault("midi", {}).setdefault("clock", {})

            p = self.query_one("#preferred-select", Select).value
            f = self.query_one("#fallback-select", Select).value
            d = self.query_one("#downbeat-select", Select).value
            dc = self.query_one("#downbeat-color-select", Select).value
            if p: midi["preferred"] = str(p)
            if f: midi["fallback"] = str(f)
            if d: ui["downbeat_flash"] = str(d)
            if dc: ui["downbeat_color"] = str(dc)
            h = self.query_one("#hints-select", Select).value
            if h is not None: ui["hints_enabled"] = bool(h) if str(h) != "False" else False
            osc = self._config.setdefault("osc", {})
            ss = self.query_one("#osc-scroll-speed", Input).value
            try:
                osc["scroll_speed_ms"] = max(10, min(500, int(ss)))
            except ValueError:
                pass
            arp = self._config.setdefault("arp", {})
            at = self.query_one("#arp-transpose-select", Select).value
            if at is not None: arp["diatonic"] = bool(at) if str(at) != "False" else False
            self.dismiss(self._config)
        elif event.button.id == "open-mixer":
            self.app.push_screen(MixerSettingsScreen(self._config))


class MixerSettingsScreen(ModalScreen):
    """Mixer channel configuration — per-channel output, curve, alias."""
    CSS = """
        MixerSettingsScreen {
            align: center middle;
        }
        #mixer-dialog {
            width: 62;
            height: 30;
            border: thick $primary;
            background: $surface;
            padding: 1;
        }
        #mixer-list {
            height: 20;
            border: solid $border;
            overflow-y: scroll;
        }
    """

    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, config: dict):
        super().__init__()
        self._config = config
        self._channels = config.get("mixer", {}).get("channels", [])
        if not self._channels:
            self._channels = [self._default_channel(i) for i in range(16)]

    @staticmethod
    def _default_channel(i: int) -> dict:
        return {
            "index": i,
            "alias": f"Track {i+1}",
            "output": "OSC",
            "curve": "linear",
            "osc_addr": f"/track/{i+1}/volume",
            "midi_channel": 0,
            "midi_cc": 21 + i,
        }

    def compose(self) -> ComposeResult:
        with Container(id="mixer-dialog"):
            yield Static("Mixer Channel Configuration")
            yield Static("(each channel: output type, curve, alias)")
            yield Static("")
            yield ListView(id="mixer-list")
            yield Static("")
            with Horizontal():
                yield Button("Close", variant="primary", id="close-mixer")

    def on_mount(self):
        lst = self.query_one("#mixer-list", ListView)
        for ch in self._channels:
            alias = ch.get("alias", f"Track {ch['index']+1}")
            out = ch.get("output", "OSC")
            curve = ch.get("curve", "linear")
            label = f"  CH{ch['index']+1:2d}: {alias:20s} [{out:4s}] curve={curve}"
            lst.append(ListItem(Label(label)))

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "close-mixer":
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

    def __init__(self, engine_queue, config: dict = None):
        super().__init__()
        self._engine_queue = engine_queue
        self._config = config or {}
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
        def handle(result):
            if result:
                try:
                    from src.profiles import ProfileManager
                    pm = ProfileManager()
                    pm.save("live-show", result)
                    self._add_log("Settings saved to profile")
                except Exception as e:
                    self._add_log(f"Save failed: {e}")

        self.push_screen(SettingsScreen(self._config, "live-show"), handle)

    def _add_log(self, text: str):
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_lines.append(f"{ts} {text}")
        if len(self._log_lines) > 50:
            self._log_lines = self._log_lines[-50:]
        if self._log:
            self._log.update("\n".join(self._log_lines))


def run_tui(engine_queue, config: dict = None):
    app = NovaTUI(engine_queue, config)
    app.run()
