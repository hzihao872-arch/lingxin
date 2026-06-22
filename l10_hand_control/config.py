from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class HandConfig:
    hand_type: str = "left"
    hand_joint: str = "L10"
    can: str = "PCAN_USBBUS1"
    dashboard_url: str = "http://127.0.0.1:7080"
    dashboard_interface: str = "can1"
    l10_variant: str = "ball_joint"
    sdk_path: Path | None = None
    timeout_seconds: float = 5.0


def load_config(path: str | Path | None = None) -> HandConfig:
    if path is None:
        return HandConfig()

    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle) or {}

    if "sdk_path" in raw and raw["sdk_path"]:
        raw["sdk_path"] = Path(raw["sdk_path"])

    return HandConfig(**raw)
