"""
Image storage system for screensaver.
64 images, 8 quick-access slots, YAML persistence.
"""
import logging
from pathlib import Path
from typing import Optional

import yaml

from src.controllers.color_map import LogicalColor

logger = logging.getLogger(__name__)

DEFAULT_IMAGES: dict[int, dict] = {
    0: {
        "name": "waves",
        "grid": [
            ["AMBER_LOW", "OFF", "OFF", "OFF", "OFF", "OFF", "OFF", "OFF"],
            ["AMBER_MED", "AMBER_LOW", "OFF", "OFF", "OFF", "OFF", "OFF", "OFF"],
            ["AMBER_HIGH", "AMBER_MED", "AMBER_LOW", "OFF", "OFF", "OFF", "OFF", "OFF"],
            ["AMBER_HIGH", "AMBER_HIGH", "AMBER_MED", "AMBER_LOW", "OFF", "OFF", "OFF", "OFF"],
            ["AMBER_HIGH", "AMBER_HIGH", "AMBER_HIGH", "AMBER_MED", "AMBER_LOW", "OFF", "OFF", "OFF"],
            ["AMBER_HIGH", "AMBER_HIGH", "AMBER_HIGH", "AMBER_HIGH", "AMBER_MED", "AMBER_LOW", "OFF", "OFF"],
            ["AMBER_HIGH", "AMBER_HIGH", "AMBER_HIGH", "AMBER_HIGH", "AMBER_HIGH", "AMBER_MED", "AMBER_LOW", "OFF"],
            ["AMBER_HIGH", "AMBER_HIGH", "AMBER_HIGH", "AMBER_HIGH", "AMBER_HIGH", "AMBER_HIGH", "AMBER_MED", "AMBER_LOW"],
        ],
    },
    1: {
        "name": "heart",
        "grid": [
            ["OFF", "RED_HIGH", "RED_HIGH", "OFF", "OFF", "RED_HIGH", "RED_HIGH", "OFF"],
            ["RED_HIGH", "RED_HIGH", "RED_HIGH", "RED_HIGH", "RED_HIGH", "RED_HIGH", "RED_HIGH", "RED_HIGH"],
            ["RED_HIGH", "RED_HIGH", "RED_HIGH", "RED_HIGH", "RED_HIGH", "RED_HIGH", "RED_HIGH", "RED_HIGH"],
            ["OFF", "RED_HIGH", "RED_HIGH", "RED_HIGH", "RED_HIGH", "RED_HIGH", "RED_HIGH", "OFF"],
            ["OFF", "OFF", "RED_HIGH", "RED_HIGH", "RED_HIGH", "RED_HIGH", "OFF", "OFF"],
            ["OFF", "OFF", "OFF", "RED_HIGH", "RED_HIGH", "OFF", "OFF", "OFF"],
            ["OFF", "OFF", "OFF", "OFF", "OFF", "OFF", "OFF", "OFF"],
            ["OFF", "OFF", "OFF", "OFF", "OFF", "OFF", "OFF", "OFF"],
        ],
    },
    2: {
        "name": "checker",
        "grid": [
            ["GREEN_HIGH", "OFF", "GREEN_HIGH", "OFF", "GREEN_HIGH", "OFF", "GREEN_HIGH", "OFF"],
            ["OFF", "GREEN_HIGH", "OFF", "GREEN_HIGH", "OFF", "GREEN_HIGH", "OFF", "GREEN_HIGH"],
            ["GREEN_HIGH", "OFF", "GREEN_HIGH", "OFF", "GREEN_HIGH", "OFF", "GREEN_HIGH", "OFF"],
            ["OFF", "GREEN_HIGH", "OFF", "GREEN_HIGH", "OFF", "GREEN_HIGH", "OFF", "GREEN_HIGH"],
            ["GREEN_HIGH", "OFF", "GREEN_HIGH", "OFF", "GREEN_HIGH", "OFF", "GREEN_HIGH", "OFF"],
            ["OFF", "GREEN_HIGH", "OFF", "GREEN_HIGH", "OFF", "GREEN_HIGH", "OFF", "GREEN_HIGH"],
            ["GREEN_HIGH", "OFF", "GREEN_HIGH", "OFF", "GREEN_HIGH", "OFF", "GREEN_HIGH", "OFF"],
            ["OFF", "GREEN_HIGH", "OFF", "GREEN_HIGH", "OFF", "GREEN_HIGH", "OFF", "GREEN_HIGH"],
        ],
    },
    3: {
        "name": "xmarks",
        "grid": [
            ["RED_HIGH", "OFF", "OFF", "OFF", "OFF", "OFF", "OFF", "RED_HIGH"],
            ["OFF", "RED_HIGH", "OFF", "OFF", "OFF", "OFF", "RED_HIGH", "OFF"],
            ["OFF", "OFF", "RED_HIGH", "OFF", "OFF", "RED_HIGH", "OFF", "OFF"],
            ["OFF", "OFF", "OFF", "RED_HIGH", "RED_HIGH", "OFF", "OFF", "OFF"],
            ["OFF", "OFF", "OFF", "RED_HIGH", "RED_HIGH", "OFF", "OFF", "OFF"],
            ["OFF", "OFF", "RED_HIGH", "OFF", "OFF", "RED_HIGH", "OFF", "OFF"],
            ["OFF", "RED_HIGH", "OFF", "OFF", "OFF", "OFF", "RED_HIGH", "OFF"],
            ["RED_HIGH", "OFF", "OFF", "OFF", "OFF", "OFF", "OFF", "RED_HIGH"],
        ],
    },
    4: {
        "name": "diamond",
        "grid": [
            ["OFF", "OFF", "OFF", "AMBER_HIGH", "AMBER_HIGH", "OFF", "OFF", "OFF"],
            ["OFF", "OFF", "AMBER_HIGH", "AMBER_MED", "AMBER_MED", "AMBER_HIGH", "OFF", "OFF"],
            ["OFF", "AMBER_HIGH", "AMBER_MED", "AMBER_LOW", "AMBER_LOW", "AMBER_MED", "AMBER_HIGH", "OFF"],
            ["AMBER_HIGH", "AMBER_MED", "AMBER_LOW", "OFF", "OFF", "AMBER_LOW", "AMBER_MED", "AMBER_HIGH"],
            ["AMBER_HIGH", "AMBER_MED", "AMBER_LOW", "OFF", "OFF", "AMBER_LOW", "AMBER_MED", "AMBER_HIGH"],
            ["OFF", "AMBER_HIGH", "AMBER_MED", "AMBER_LOW", "AMBER_LOW", "AMBER_MED", "AMBER_HIGH", "OFF"],
            ["OFF", "OFF", "AMBER_HIGH", "AMBER_MED", "AMBER_MED", "AMBER_HIGH", "OFF", "OFF"],
            ["OFF", "OFF", "OFF", "AMBER_HIGH", "AMBER_HIGH", "OFF", "OFF", "OFF"],
        ],
    },
    5: {
        "name": "all_amber",
        "grid": [["AMBER_LOW"] * 8] * 8,
    },
    6: {
        "name": "all_red",
        "grid": [["RED_LOW"] * 8] * 8,
    },
    7: {
        "name": "all_green",
        "grid": [["GREEN_LOW"] * 8] * 8,
    },
    8: {
        "name": "peace",
        "grid": [
            ["OFF", "OFF", "AMBER_HIGH", "AMBER_HIGH", "AMBER_HIGH", "AMBER_HIGH", "OFF", "OFF"],
            ["OFF", "AMBER_HIGH", "OFF", "OFF", "OFF", "OFF", "AMBER_HIGH", "OFF"],
            ["AMBER_HIGH", "OFF", "AMBER_HIGH", "OFF", "OFF", "AMBER_HIGH", "OFF", "AMBER_HIGH"],
            ["AMBER_HIGH", "OFF", "OFF", "AMBER_HIGH", "AMBER_HIGH", "OFF", "OFF", "AMBER_HIGH"],
            ["AMBER_HIGH", "OFF", "OFF", "AMBER_HIGH", "AMBER_HIGH", "OFF", "OFF", "AMBER_HIGH"],
            ["AMBER_HIGH", "OFF", "AMBER_HIGH", "OFF", "OFF", "AMBER_HIGH", "OFF", "AMBER_HIGH"],
            ["OFF", "AMBER_HIGH", "OFF", "OFF", "OFF", "OFF", "AMBER_HIGH", "OFF"],
            ["OFF", "OFF", "AMBER_HIGH", "AMBER_HIGH", "AMBER_HIGH", "AMBER_HIGH", "OFF", "OFF"],
        ],
    },
}


class ImageStore:
    def __init__(self, path: Optional[Path] = None):
        if path is None:
            path = Path(__file__).parent.parent.parent / "config" / "screensaver-images.yaml"
        self._path = path
        self.images: dict[int, dict] = {}
        self.quick_slots: dict[int, int] = {}
        self.last_image: int = 0
        self._load()

    def _load(self):
        try:
            if self._path.exists():
                with open(self._path) as f:
                    data = yaml.safe_load(f) or {}
                self.images = data.get("images", {})
                self.quick_slots = data.get("quick_slots", {})
                self.last_image = data.get("last_image", 0)
                logger.info(f"Loaded {len(self.images)} images from {self._path}")
            else:
                self._init_defaults()
        except Exception as e:
            logger.warning(f"Failed to load images: {e}. Using defaults.")
            self._init_defaults()

    def _init_defaults(self):
        self.images = dict(DEFAULT_IMAGES)
        self.quick_slots = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7}
        self.last_image = 0
        self.save()

    def save(self):
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "images": self.images,
                "quick_slots": self.quick_slots,
                "last_image": self.last_image,
            }
            with open(self._path, "w") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            logger.error(f"Failed to save images: {e}")

    def get_image(self, image_id: int) -> Optional[list[list[LogicalColor]]]:
        img = self.images.get(image_id)
        if img is None:
            return None
        return [[LogicalColor[cell] for cell in row] for row in img["grid"]]

    def store_image(self, image_id: int, name: str, grid: list[list[LogicalColor]]):
        color_grid = [[cell.name for cell in row] for row in grid]
        self.images[image_id] = {"name": name, "grid": color_grid}
        self.save()

    def get_quick_slot(self, slot: int) -> Optional[int]:
        return self.quick_slots.get(slot)

    def set_quick_slot(self, slot: int, image_id: int):
        self.quick_slots[slot] = image_id
        self.save()

    def set_last_image(self, image_id: int):
        self.last_image = image_id
        self.save()

    def render_to_grid(self, image_id: int, target_grid):
        img = self.get_image(image_id)
        if img is None:
            return False
        target_grid.clear()
        for y, row in enumerate(img):
            display_y = 7 - y
            for x, color in enumerate(row):
                if 0 <= x < 8 and 0 <= display_y < 8:
                    target_grid.set_cell(x, display_y, color)
        return True


def test_image_store():
    """Test load, save, quick slots, and grid rendering."""
    import tempfile
    from pathlib import Path

    from tests.virtualizer import VirtualLaunchpad
    from src.layout.grid import LogicalGrid

    print("=== IMAGE STORE TEST ===\n")

    # Test with temp file
    tmp = Path(tempfile.mktemp(suffix=".yaml"))
    store = ImageStore(tmp)

    print(f"  ✓ Default images: {len(store.images)}")
    assert len(store.images) >= 8, f"Expected 8+ images, got {len(store.images)}"

    # Test quick slots
    slot = store.get_quick_slot(0)
    print(f"  ✓ Quick slot 0 → image {slot} ('{store.images[slot]['name']}')")
    assert slot is not None

    # Test get_image returns proper LogicalColor grid
    img = store.get_image(0)
    assert img is not None
    assert isinstance(img[0][0], LogicalColor), f"Expected LogicalColor, got {type(img[0][0])}"
    print(f"  ✓ Image 0 is 8×{len(img[0])} of LogicalColor")

    # Test render to virtual grid
    v = VirtualLaunchpad()
    logical_grid = LogicalGrid(8, 8)

    def commit():
        for x, y in logical_grid.dirty_cells():
            color = logical_grid.get_cell(x, y)
            v.controller.set_grid_color(x, y, color)

    logical_grid.set_on_cell_changed(lambda x, y, c: None)

    store.render_to_grid(2, logical_grid)  # checker
    commit()
    print(v.render("Image #2: checker"))
    print()

    store.render_to_grid(1, logical_grid)  # heart
    commit()
    print(v.render("Image #1: heart"))
    print()

    # Test store + retrieve
    new_img = [[LogicalColor.AMBER_HIGH] * 8 for _ in range(8)]
    store.store_image(50, "test_fill", new_img)
    retrieved = store.get_image(50)
    assert retrieved is not None
    assert retrieved[0][0] == LogicalColor.AMBER_HIGH
    print(f"  ✓ Store/retrieve image #50: all AMBER_HIGH")

    # Test persistence
    store.set_quick_slot(0, 50)
    store.set_last_image(50)
    store.save()

    store2 = ImageStore(tmp)
    assert store2.get_quick_slot(0) == 50, f"Slot persistence failed"
    assert store2.last_image == 50, f"Last image persistence failed"
    print(f"  ✓ Persistence: quick slot 0 → {store2.get_quick_slot(0)}, last_image → {store2.last_image}")

    # Cleanup
    tmp.unlink(missing_ok=True)
    print("\n=== IMAGE STORE TESTS PASSED ===")


if __name__ == "__main__":
    test_image_store()
