from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from l10_hand_control.config import HandConfig
from l10_hand_control.web_server import (
    PresetStore,
    dashboard_reachable,
    make_handler,
    resolve_backend,
)


class MockConnection:
    def makefile(self, mode: str, bufsize: int = -1) -> BytesIO:
        return BytesIO()


def make_test_handler(tmp_path: Path):
    controller = MagicMock()
    pose_sender = MagicMock()
    store = PresetStore(tmp_path / "presets.json")
    handler_cls = make_handler(
        controller,
        store,
        "dashboard",
        MagicMock(dashboard_url="http://127.0.0.1:7080", hand_type="left", l10_variant="ball_joint"),
        pose_sender,
    )
    handler = handler_cls(MockConnection(), ("127.0.0.1", 8765), None)
    captured: list[bytes] = []

    handler.send_response = lambda code: setattr(handler, "status_code", code)
    handler.send_header = lambda key, value: None
    handler.end_headers = lambda: None
    handler.wfile = MagicMock(write=lambda chunk: captured.append(chunk))
    return handler, captured, controller, store


class TestPresetStore:
    def test_add_list_and_delete_preset(self, tmp_path: Path) -> None:
        store = PresetStore(tmp_path / "presets.json")
        pose = [255, 70, 255, 255, 255, 255, 255, 255, 255, 255]
        preset = store.add_preset("张开", pose)

        assert preset["name"] == "张开"
        assert preset["pose"] == pose
        assert len(store.list_presets()) == 1

        assert store.get_preset(preset["id"]) == preset
        assert store.delete_preset(preset["id"]) is True
        assert store.list_presets() == []


class TestWebAPI:
    def test_joints_endpoint(self, tmp_path: Path) -> None:
        handler, captured, _, _ = make_test_handler(tmp_path)
        handler.path = "/api/joints"
        handler.headers = {}

        handler.do_GET()
        payload = json.loads(captured[0].decode("utf-8"))
        assert len(payload["joints"]) == 10
        assert payload["joints"][1]["max"] == 255
        assert payload["default_pose"][1] == 70

    def test_save_preset_endpoint(self, tmp_path: Path) -> None:
        handler, captured, _, store = make_test_handler(tmp_path)
        handler.path = "/api/presets"
        body = json.dumps(
            {
                "name": "握拳",
                "pose": [80, 70, 80, 80, 80, 80, 80, 80, 80, 80],
            }
        ).encode("utf-8")
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = BytesIO(body)

        handler.do_POST()
        payload = json.loads(captured[0].decode("utf-8"))
        assert payload["preset"]["name"] == "握拳"
        assert len(store.list_presets()) == 1


class TestBackendResolution:
    def test_resolve_backend_prefers_dashboard_when_reachable(self, tmp_path: Path) -> None:
        config = HandConfig()
        with patch("l10_hand_control.web_server.dashboard_reachable", return_value=True):
            backend, resolved = resolve_backend("auto", config, None)
        assert backend == "dashboard"
        assert resolved == config

    def test_resolve_backend_falls_back_to_sdk(self, tmp_path: Path) -> None:
        sdk_path = tmp_path / "linkerhand-python-sdk"
        sdk_path.mkdir()
        config = HandConfig()
        with patch("l10_hand_control.web_server.dashboard_reachable", return_value=False):
            backend, resolved = resolve_backend("auto", config, sdk_path)
        assert backend == "sdk"
        assert resolved.sdk_path == sdk_path

    def test_dashboard_reachable_false_on_connection_error(self) -> None:
        config = HandConfig(dashboard_url="http://127.0.0.1:1")
        assert dashboard_reachable(config, timeout_seconds=0.2) is False
