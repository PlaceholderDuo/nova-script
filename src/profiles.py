"""
Profile system — save/load/export/import configuration profiles.

Profiles live in config/profiles/<alias>.yaml
Defaults fall back to config/default.yaml
"""
import logging
import shutil
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)


class ProfileManager:
    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            base_dir = Path(__file__).parent.parent / "config"
        self._base_dir = base_dir
        self._profiles_dir = base_dir / "profiles"
        self._defaults_path = base_dir / "default.yaml"

        self._profiles_dir.mkdir(parents=True, exist_ok=True)

    def load(self, alias: str = "live-show") -> dict:
        config = {}

        if self._defaults_path.exists():
            with open(self._defaults_path) as f:
                config = yaml.safe_load(f) or {}

        profile_path = self._profiles_dir / f"{alias}.yaml"
        if profile_path.exists():
            with open(profile_path) as f:
                profile = yaml.safe_load(f) or {}
            config = self._deep_merge(config, profile)
            logger.info(f"Loaded profile: {alias}")
        else:
            logger.info(f"Profile '{alias}' not found. Using defaults.")
            self._ensure_default_profile()

        config["_profile_name"] = alias
        return config

    def save(self, alias: str, config: dict):
        clean = {k: v for k, v in config.items() if not k.startswith("_")}
        profile_path = self._profiles_dir / f"{alias}.yaml"
        with open(profile_path, "w") as f:
            yaml.dump(clean, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Saved profile: {alias}")

    def list(self) -> list[str]:
        if not self._profiles_dir.exists():
            return ["live-show"]
        profiles = []
        for p in sorted(self._profiles_dir.glob("*.yaml")):
            profiles.append(p.stem)
        if not profiles:
            profiles = ["live-show"]
        return profiles

    def export_profile(self, alias: str, output_path: Path):
        profile_path = self._profiles_dir / f"{alias}.yaml"
        if not profile_path.exists():
            raise FileNotFoundError(f"Profile '{alias}' not found")
        shutil.copy(profile_path, output_path)
        logger.info(f"Exported profile '{alias}' to {output_path}")

    def import_profile(self, input_path: Path, alias: Optional[str] = None):
        if not input_path.exists():
            raise FileNotFoundError(f"Import file not found: {input_path}")

        with open(input_path) as f:
            data = yaml.safe_load(f)

        if alias is None:
            alias = input_path.stem

        dest = self._profiles_dir / f"{alias}.yaml"
        with open(dest, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Imported profile '{alias}' from {input_path}")
        return alias

    def _ensure_default_profile(self):
        default = self._profiles_dir / "live-show.yaml"
        if not default.exists():
            logger.info("Creating default live-show profile")
            self.save("live-show", {})

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        result = dict(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ProfileManager._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
