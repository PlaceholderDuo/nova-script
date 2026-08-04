"""
Combo detector — detects multi-button combos on the control row.
Used by the Engine to intercept Top-1+2 (screensaver) and Top-1+3 (fireworks).
"""
import time


class ComboDetector:
    def __init__(self, combo_window_ms: int = 250):
        self._combo_window_ms = combo_window_ms
        self._held: dict[int, float] = {}
        self._pending_home = False
        self._home_press_time = 0.0
        self._combo_fired = False
        self._combo_partner: int | None = None

    def feed(self, control_id: int, pressed: bool) -> str | None:
        """Returns: None (normal), 'home', 'screensaver', 'fireworks', or 'consumed'."""
        if pressed:
            self._held[control_id] = time.monotonic()

            if control_id == 200:
                self._pending_home = True
                self._home_press_time = time.monotonic()
                return "consumed"

            if self._held.get(200) is not None:
                if control_id == 201:
                    self._pending_home = False
                    self._combo_fired = True
                    self._combo_partner = 201
                    return "screensaver"
                elif control_id == 202:
                    self._pending_home = False
                    self._combo_fired = True
                    self._combo_partner = 202
                    return "fireworks"

            return None
        else:
            self._held.pop(control_id, None)

            if control_id == 200:
                self._pending_home = False
                if self._combo_fired:
                    return "consumed"
                return "home"

            if self._combo_fired and control_id == self._combo_partner:
                if len(self._held) == 0:
                    self._combo_fired = False
                    self._combo_partner = None
                return "consumed"

            return None

    def tick(self) -> str | None:
        """Call periodically. Returns 'home' if combo window expired."""
        if self._pending_home:
            elapsed = (time.monotonic() - self._home_press_time) * 1000
            if elapsed >= self._combo_window_ms:
                self._pending_home = False
                return "home"
        return None

