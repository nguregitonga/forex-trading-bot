"""Load config/settings.yaml."""

from pathlib import Path
from typing import Any, Dict

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "settings.yaml"


def load_settings(path: str = None) -> Dict[str, Any]:
    """Return the settings as a dict ({} sections are filled in so .get() chains work)."""
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    with open(config_path, encoding="utf-8") as fh:
        settings = yaml.safe_load(fh) or {}
    for section in ("trading", "risk_management", "strategy", "backtesting", "performance"):
        settings.setdefault(section, {})
    return settings
