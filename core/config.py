"""Configuration loader for the quant trading framework."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "default.yaml"

TF_SECONDS: dict[str, int] = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}

BARS_PER_YEAR: dict[str, int] = {
    "15m": 365 * 96,
    "1h": 365 * 24,
    "4h": 365 * 6,
    "1d": 365,
}


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load YAML config and .env environment variables."""
    load_dotenv(PROJECT_ROOT / ".env")
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    with cfg_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)
