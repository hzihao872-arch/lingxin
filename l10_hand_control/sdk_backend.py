from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

from l10_hand_control.config import HandConfig


class SdkController:
    """Controller backed by the official LinkerHand Python SDK."""

    def __init__(
        self,
        config: HandConfig,
        api_factory: Callable[..., Any] | None = None,
    ):
        self.config = config
        self._api_factory = api_factory
        self._hand: Any | None = None

    def _load_api_factory(self) -> Callable[..., Any]:
        if self._api_factory is not None:
            return self._api_factory

        if self.config.sdk_path is not None:
            sdk_root = Path(self.config.sdk_path)
            if not sdk_root.exists():
                raise FileNotFoundError(f"SDK path does not exist: {sdk_root}")
            sys.path.insert(0, str(sdk_root))

        try:
            from LinkerHand.linker_hand_api import LinkerHandApi
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Official LinkerHand SDK is not importable. Clone "
                "https://github.com/linker-bot/linkerhand-python-sdk and pass "
                "--sdk-path or set sdk_path in config."
            ) from exc

        return LinkerHandApi

    @property
    def hand(self) -> Any:
        if self._hand is None:
            factory = self._load_api_factory()
            self._hand = factory(
                hand_joint=self.config.hand_joint,
                hand_type=self.config.hand_type,
                can=self.config.can,
            )
        return self._hand

    def list_devices(self) -> list[dict[str, str]]:
        return [
            {
                "hand_type": self.config.hand_type,
                "hand_joint": self.config.hand_joint,
                "can": self.config.can,
            }
        ]

    def execute_gesture(self, name: str) -> dict[str, Any]:
        if name in {"握拳_Fist", "fist"}:
            self.set_speed([120] * 10)
            self.move_pose([80] * 10)
            return {"status": "ok", "gesture": name}
        raise ValueError(f"SDK backend has no built-in gesture: {name}")

    def set_speed(self, speed: int | list[int]) -> Any:
        values = [speed] * 10 if isinstance(speed, int) else list(speed)
        if len(values) != 10:
            raise ValueError("L10 speed must contain 10 values")
        return self.hand.set_speed(speed=values)

    def move_pose(self, pose: list[int]) -> Any:
        if len(pose) != 10:
            raise ValueError("L10 pose must contain 10 values")
        return self.hand.finger_move(pose=pose)

    def get_state(self) -> Any:
        return self.hand.get_state()
