from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

from l10_hand_control.config import HandConfig
from l10_hand_control.l10_pose import clamp_pose
from l10_hand_control.l10_state import normalize_l10_pose

DEFAULT_L10_TORQUE = [120] * 10


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
        self._saved_torque: list[int] | None = None
        self._teach_active = False

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
            missing = exc.name or str(exc)
            if missing == "can":
                raise RuntimeError(
                    "SDK CAN dependency is missing. Install with:\n"
                    "  py -m pip install -e \".[sdk]\"\n"
                    "or:\n"
                    "  py -m pip install python-can python-can-candle"
                ) from exc
            raise RuntimeError(
                "Official LinkerHand SDK is not importable. Clone "
                "https://github.com/linker-bot/linkerhand-python-sdk and pass "
                "--sdk-path or set sdk_path in config."
            ) from exc

        return LinkerHandApi

    def _create_hand(self, factory: Callable[..., Any]) -> Any:
        try:
            return factory(
                hand_joint=self.config.hand_joint,
                hand_type=self.config.hand_type,
                can=self.config.can,
            )
        except ModuleNotFoundError as exc:
            missing = exc.name or str(exc)
            if missing == "can":
                raise RuntimeError(
                    "SDK CAN dependency is missing. Install with:\n"
                    "  py -m pip install -e \".[sdk]\"\n"
                    "or:\n"
                    "  py -m pip install python-can python-can-candle"
                ) from exc
            raise

    @property
    def hand(self) -> Any:
        if self._hand is None:
            factory = self._load_api_factory()
            self._hand = self._create_hand(factory)
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
        safe_pose = clamp_pose(pose, self.config.l10_variant)
        return self.hand.finger_move(pose=safe_pose)

    def get_state(self) -> Any:
        return self.hand.get_state()

    @property
    def teach_active(self) -> bool:
        return self._teach_active

    def read_pose(self) -> list[int]:
        return normalize_l10_pose(self.get_state())

    def _read_torque(self) -> list[int]:
        torque = self.hand.get_torque()
        if not isinstance(torque, (list, tuple)) or len(torque) != 10:
            return list(DEFAULT_L10_TORQUE)
        values = [int(value) for value in torque]
        if any(value < 0 for value in values):
            return list(DEFAULT_L10_TORQUE)
        return values

    def enter_teach_mode(self) -> dict[str, Any]:
        """Release holding torque so the hand can be moved by hand."""
        if self._teach_active:
            return {"teach_active": True}
        self._saved_torque = self._read_torque()
        self.hand.set_torque([0] * 10)
        self._teach_active = True
        return {
            "teach_active": True,
            "saved_torque": self._saved_torque,
            "note": "L10 通过扭矩置零进入示教，请用手轻轻拨动关节。",
        }

    def exit_teach_mode(self, restore_torque: list[int] | None = None) -> dict[str, Any]:
        torque = restore_torque or self._saved_torque or DEFAULT_L10_TORQUE
        if len(torque) != 10:
            raise ValueError("restore torque must contain 10 values")
        self.hand.set_torque([int(value) for value in torque])
        self._teach_active = False
        self._saved_torque = None
        return {"teach_active": False, "torque": torque}
