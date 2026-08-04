from enum import IntEnum, auto


class LogicalColor(IntEnum):
    OFF = 0
    RED_LOW = auto()
    RED_MED = auto()
    RED_HIGH = auto()
    GREEN_LOW = auto()
    GREEN_MED = auto()
    GREEN_HIGH = auto()
    AMBER_LOW = auto()
    AMBER_MED = auto()
    AMBER_HIGH = auto()
    YELLOW_LOW = auto()
    YELLOW_MED = auto()
    YELLOW_HIGH = auto()
    ORANGE_LOW = auto()
    ORANGE_MED = auto()
    ORANGE_HIGH = auto()
    WHITE_LOW = auto()
    WHITE_MED = auto()
    WHITE_HIGH = auto()
    BLUE_LOW = auto()
    BLUE_MED = auto()
    BLUE_HIGH = auto()
    PURPLE_LOW = auto()
    PURPLE_MED = auto()
    PURPLE_HIGH = auto()
    CYAN_LOW = auto()
    CYAN_MED = auto()
    CYAN_HIGH = auto()

    def brightness(self) -> str:
        name = self.name
        if name.endswith("_LOW"):
            return "low"
        elif name.endswith("_MED"):
            return "med"
        elif name.endswith("_HIGH"):
            return "high"
        return "off"

    def base_color(self) -> str:
        name = self.name
        for color in [
            "RED", "GREEN", "AMBER", "YELLOW", "ORANGE",
            "WHITE", "BLUE", "PURPLE", "CYAN"
        ]:
            if name.startswith(color):
                return color.lower()
        return "off"


MK1_COLOR_MAP: dict[LogicalColor, int] = {
    LogicalColor.OFF: 0,
    LogicalColor.RED_LOW: 1,
    LogicalColor.RED_MED: 2,
    LogicalColor.RED_HIGH: 3,
    LogicalColor.GREEN_LOW: 16,
    LogicalColor.GREEN_MED: 32,
    LogicalColor.GREEN_HIGH: 48,
    LogicalColor.AMBER_LOW: 17,
    LogicalColor.AMBER_MED: 34,
    LogicalColor.AMBER_HIGH: 51,
    LogicalColor.YELLOW_LOW: 17,
    LogicalColor.YELLOW_MED: 50,
    LogicalColor.YELLOW_HIGH: 51,
    LogicalColor.ORANGE_LOW: 17,
    LogicalColor.ORANGE_MED: 33,
    LogicalColor.ORANGE_HIGH: 51,
    LogicalColor.WHITE_LOW: 17,
    LogicalColor.WHITE_MED: 34,
    LogicalColor.WHITE_HIGH: 51,
    LogicalColor.BLUE_LOW: 16,
    LogicalColor.BLUE_MED: 32,
    LogicalColor.BLUE_HIGH: 48,
    LogicalColor.PURPLE_LOW: 17,
    LogicalColor.PURPLE_MED: 33,
    LogicalColor.PURPLE_HIGH: 51,
    LogicalColor.CYAN_LOW: 16,
    LogicalColor.CYAN_MED: 32,
    LogicalColor.CYAN_HIGH: 48,
}

MK3_COLOR_PALETTE_INDEX: dict[LogicalColor, int] = {
    LogicalColor.OFF: 0,
    LogicalColor.RED_LOW: 5,
    LogicalColor.RED_MED: 6,
    LogicalColor.RED_HIGH: 7,
    LogicalColor.GREEN_LOW: 17,
    LogicalColor.GREEN_MED: 18,
    LogicalColor.GREEN_HIGH: 19,
    LogicalColor.AMBER_LOW: 9,
    LogicalColor.AMBER_MED: 10,
    LogicalColor.AMBER_HIGH: 11,
    LogicalColor.YELLOW_LOW: 13,
    LogicalColor.YELLOW_MED: 14,
    LogicalColor.YELLOW_HIGH: 15,
    LogicalColor.ORANGE_LOW: 9,
    LogicalColor.ORANGE_MED: 10,
    LogicalColor.ORANGE_HIGH: 11,
    LogicalColor.WHITE_LOW: 1,
    LogicalColor.WHITE_MED: 2,
    LogicalColor.WHITE_HIGH: 3,
    LogicalColor.BLUE_LOW: 41,
    LogicalColor.BLUE_MED: 42,
    LogicalColor.BLUE_HIGH: 43,
    LogicalColor.PURPLE_LOW: 49,
    LogicalColor.PURPLE_MED: 50,
    LogicalColor.PURPLE_HIGH: 51,
    LogicalColor.CYAN_LOW: 33,
    LogicalColor.CYAN_MED: 34,
    LogicalColor.CYAN_HIGH: 35,
}


class ColorMapper:
    def __init__(self, device_type: str):
        if "mk1" in device_type.lower():
            self._map = MK1_COLOR_MAP
            self._use_sysex = False
        else:
            self._map = MK3_COLOR_PALETTE_INDEX
            self._use_sysex = True

    def to_hardware(self, color: LogicalColor) -> int:
        return self._map.get(color, 0)

    @property
    def uses_sysex(self) -> bool:
        return self._use_sysex
