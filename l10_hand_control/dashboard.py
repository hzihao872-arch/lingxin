from __future__ import annotations

from typing import Any

import requests

from l10_hand_control.config import HandConfig
from l10_hand_control.errors import ControlError
from l10_hand_control.l10_pose import clamp_pose


class DashboardController:
    """Controller for the official dashboard HTTP API."""

    def __init__(self, config: HandConfig, session: Any | None = None):
        self.config = config
        self.session = session or requests.Session()
        self.base_url = config.dashboard_url.rstrip("/")

    def _target(self) -> dict[str, str]:
        return {
            "model": self.config.hand_joint,
            "variant": self.config.l10_variant,
            "interface": self.config.dashboard_interface,
            "hand": self.config.hand_type,
        }

    def _post(self, path: str, payload: dict[str, Any]) -> Any:
        url = f"{self.base_url}{path}"
        try:
            response = self.session.post(
                url,
                json=payload,
                timeout=self.config.timeout_seconds,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise self._connection_error(url, exc) from exc

    def list_devices(self) -> Any:
        url = f"{self.base_url}/api/hand/devices"
        try:
            response = self.session.get(url, timeout=self.config.timeout_seconds)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise self._connection_error(url, exc) from exc
        return payload.get("data", payload)

    def execute_gesture(self, name: str) -> Any:
        return self._post(
            "/api/hand/exec",
            {
                "mode": "gesture",
                "name": name,
                "targets": [self._target()],
            },
        )

    def stop(self) -> Any:
        return self._post("/api/hand/exec", {"mode": "stop"})

    def set_speed(self, speed: int) -> Any:
        return self._post(
            "/api/hand/speed",
            {
                "speed": speed,
                "targets": [self._target()],
            },
        )

    def move_pose(self, pose: list[int]) -> Any:
        if len(pose) != 10:
            raise ValueError("L10 pose must contain 10 values")
        safe_pose = clamp_pose(pose, self.config.l10_variant)
        return self._post(
            "/api/hand/joint/logical",
            {
                "logical_values": {"basic": _pose_to_basic_values(safe_pose)},
                "targets": [self._target()],
            },
        )

    def get_state(self) -> Any:
        messages_url = f"{self.base_url}/api/messages/{self.config.dashboard_interface}"
        try:
            response = self.session.get(
                messages_url, timeout=self.config.timeout_seconds
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise self._connection_error(messages_url, exc) from exc

    def _connection_error(self, url: str, exc: Exception) -> ControlError:
        return ControlError(
            "Dashboard API is not reachable at "
            f"{self.base_url}. Start the official dashboard, or use --backend sdk "
            f"after closing dashboard. Failed request: {url}. Cause: {exc}"
        )


def _pose_to_basic_values(pose: list[int]) -> dict[str, int]:
    names = [
        "thumb",
        "thumb_rot",
        "index",
        "middle",
        "ring",
        "pinky",
        "thumbswing",
        "thumb_swing",
        "index_swing",
        "middle_swing",
    ]
    return dict(zip(names, pose, strict=True))
