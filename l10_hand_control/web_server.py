"""Local web UI for adjusting and saving L10 joint poses."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from l10_hand_control.async_pose_sender import AsyncPoseSender
from l10_hand_control.cli import build_controller
from l10_hand_control.config import HandConfig, load_config
from l10_hand_control.errors import ControlError
from l10_hand_control.l10_pose import (
    L10_JOINTS,
    L10_PROTOCOL_MAX,
    L10_PROTOCOL_MIN,
    OPEN_PALM_POSE,
    clamp_pose,
    get_joint_hints,
    get_joint_limits,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
DEFAULT_PRESETS_PATH = Path(__file__).resolve().parent.parent / "data" / "saved_poses.json"
DEFAULT_SDK_PATH = Path(__file__).resolve().parent.parent / "vendor" / "linkerhand-python-sdk"

JOINT_LABELS: dict[str, str] = {
    "thumb_root": "拇指根部",
    "thumb_swing": "拇指侧摆",
    "index_root": "食指根部",
    "middle_root": "中指根部",
    "ring_root": "无名指根部",
    "pinky_root": "小指根部",
    "index_swing": "食指侧摆",
    "ring_swing": "无名指侧摆",
    "pinky_swing": "小指侧摆",
    "thumb_rotation": "拇指旋转",
}


class PresetStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"presets": []})

    def _read(self) -> dict[str, Any]:
        with self.path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write(self, payload: dict[str, Any]) -> None:
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    def list_presets(self) -> list[dict[str, Any]]:
        return self._read().get("presets", [])

    def add_preset(self, name: str, pose: list[int]) -> dict[str, Any]:
        preset = {
            "id": uuid.uuid4().hex[:12],
            "name": name.strip(),
            "pose": pose,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        data = self._read()
        data.setdefault("presets", []).append(preset)
        self._write(data)
        return preset

    def delete_preset(self, preset_id: str) -> bool:
        data = self._read()
        presets = data.get("presets", [])
        kept = [item for item in presets if item.get("id") != preset_id]
        if len(kept) == len(presets):
            return False
        data["presets"] = kept
        self._write(data)
        return True

    def get_preset(self, preset_id: str) -> dict[str, Any] | None:
        for preset in self.list_presets():
            if preset.get("id") == preset_id:
                return preset
        return None


def _supports_teach(controller: Any, backend: str) -> bool:
    return backend == "sdk" and hasattr(controller, "enter_teach_mode")


def _teach_status(controller: Any, backend: str) -> dict[str, Any]:
    return {
        "supported": _supports_teach(controller, backend),
        "active": bool(getattr(controller, "teach_active", False)),
        "note": (
            "L10 无硬件失能指令，示教模式会将扭矩置零后读取关节反馈。"
            if _supports_teach(controller, backend)
            else "示教模式需要 SDK 后端（--backend sdk）。"
        ),
    }


def make_handler(
    controller: Any,
    preset_store: PresetStore,
    backend: str,
    config: HandConfig,
    pose_sender: AsyncPoseSender,
) -> type[BaseHTTPRequestHandler]:
    class WebUIHandler(BaseHTTPRequestHandler):
        server_version = "L10WebUI/1.0"

        def log_message(self, format: str, *args: Any) -> None:
            sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))

        def _send_json(self, status: int, payload: Any) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_file(self, path: Path, content_type: str) -> None:
            if not path.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            body = path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_json_body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                return {}
            raw = self.rfile.read(length)
            parsed = json.loads(raw.decode("utf-8"))
            if not isinstance(parsed, dict):
                raise ValueError("JSON body must be an object")
            return parsed

        def _validate_pose(self, pose: Any, *, clamp: bool = True) -> list[int]:
            if not isinstance(pose, list) or len(pose) != 10:
                raise ValueError("pose must be an array of 10 integers")
            values = [int(value) for value in pose]
            limits = get_joint_limits(config.l10_variant)
            if clamp:
                return clamp_pose(values, config.l10_variant)
            for index, (joint, value) in enumerate(zip(L10_JOINTS, values, strict=True)):
                minimum, maximum = limits[joint]
                if value < minimum or value > maximum:
                    raise ValueError(
                        f"{joint} value {value} out of range ({minimum}..{maximum})"
                    )
            return values

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path

            try:
                if path in {"/", "/index.html"}:
                    self._send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
                    return
                if path == "/app.js":
                    self._send_file(STATIC_DIR / "app.js", "application/javascript; charset=utf-8")
                    return
                if path == "/style.css":
                    self._send_file(STATIC_DIR / "style.css", "text/css; charset=utf-8")
                    return
                if path == "/api/joints":
                    limits = get_joint_limits(config.l10_variant)
                    hints = get_joint_hints()
                    self._send_json(
                        HTTPStatus.OK,
                        {
                            "joints": [
                                {
                                    "name": name,
                                    "label": JOINT_LABELS.get(name, name),
                                    "index": index,
                                    "min": limits[name][0],
                                    "max": limits[name][1],
                                    "hint": hints.get(name),
                                }
                                for index, name in enumerate(L10_JOINTS)
                            ],
                            "default_pose": list(OPEN_PALM_POSE),
                            "variant": config.l10_variant,
                            "range": {"min": L10_PROTOCOL_MIN, "max": L10_PROTOCOL_MAX},
                        },
                    )
                    return
                if path == "/api/status":
                    try:
                        if backend == "dashboard":
                            devices = controller.list_devices()
                        else:
                            controller.get_state()
                            devices = controller.list_devices()
                        connected = True
                        error = None
                        hint = None
                    except ControlError as exc:
                        devices = []
                        connected = False
                        error = str(exc)
                        hint = _connection_hint(backend, config)
                    except Exception as exc:
                        devices = []
                        connected = False
                        error = str(exc)
                        hint = _connection_hint(backend, config)
                    self._send_json(
                        HTTPStatus.OK,
                        {
                            "connected": connected,
                            "backend": backend,
                            "dashboard_url": config.dashboard_url,
                            "sdk_path": str(config.sdk_path) if config.sdk_path else None,
                            "hand_type": config.hand_type,
                            "devices": devices,
                            "error": error,
                            "hint": hint,
                            "teach": _teach_status(controller, backend),
                        },
                    )
                    return
                if path == "/api/teach":
                    self._send_json(HTTPStatus.OK, _teach_status(controller, backend))
                    return
                if path == "/api/teach/pose":
                    if not _supports_teach(controller, backend):
                        self._send_json(
                            HTTPStatus.BAD_REQUEST,
                            {"error": "示教读取仅支持 SDK 后端"},
                        )
                        return
                    pose = controller.read_pose()
                    self._send_json(HTTPStatus.OK, {"pose": pose})
                    return
                if path == "/api/presets":
                    self._send_json(HTTPStatus.OK, {"presets": preset_store.list_presets()})
                    return
                self.send_error(HTTPStatus.NOT_FOUND)
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path

            try:
                body = self._read_json_body()

                if path == "/api/pose":
                    if getattr(controller, "teach_active", False):
                        raise ValueError("示教模式中不能发送姿态，请先恢复使能")
                    pose = self._validate_pose(body.get("pose"))
                    live = body.get("live", False)
                    if live:
                        pose_sender.submit(pose)
                        self._send_json(HTTPStatus.OK, {"ok": True, "queued": True})
                    else:
                        result = controller.move_pose(pose)
                        self._send_json(HTTPStatus.OK, {"ok": True, "result": result})
                    return

                if path == "/api/speed":
                    speed = int(body.get("speed", 120))
                    if speed < 0 or speed > 255:
                        raise ValueError("speed must be between 0 and 255")
                    result = controller.set_speed(speed)
                    self._send_json(HTTPStatus.OK, {"ok": True, "result": result})
                    return

                if path == "/api/teach/start":
                    if not _supports_teach(controller, backend):
                        raise ValueError("示教模式仅支持 SDK 后端")
                    result = controller.enter_teach_mode()
                    self._send_json(HTTPStatus.OK, {"ok": True, **result})
                    return

                if path == "/api/teach/stop":
                    if not _supports_teach(controller, backend):
                        raise ValueError("示教模式仅支持 SDK 后端")
                    restore_torque = body.get("torque")
                    if restore_torque is not None:
                        restore_torque = self._validate_pose(restore_torque)
                    result = controller.exit_teach_mode(restore_torque)
                    self._send_json(HTTPStatus.OK, {"ok": True, **result})
                    return

                if path == "/api/presets":
                    name = str(body.get("name", "")).strip()
                    if not name:
                        raise ValueError("preset name is required")
                    pose = self._validate_pose(body.get("pose"))
                    preset = preset_store.add_preset(name, pose)
                    self._send_json(HTTPStatus.CREATED, {"preset": preset})
                    return

                if path.startswith("/api/presets/") and path.endswith("/apply"):
                    preset_id = path.removeprefix("/api/presets/").removesuffix("/apply")
                    preset = preset_store.get_preset(preset_id)
                    if preset is None:
                        self._send_json(HTTPStatus.NOT_FOUND, {"error": "preset not found"})
                        return
                    pose = self._validate_pose(preset["pose"])
                    pose_sender.submit(pose)
                    self._send_json(
                        HTTPStatus.OK,
                        {"ok": True, "preset": preset, "queued": True},
                    )
                    return

                self.send_error(HTTPStatus.NOT_FOUND)
            except ControlError as exc:
                self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})
            except (ValueError, json.JSONDecodeError) as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        def do_DELETE(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path

            if not path.startswith("/api/presets/"):
                self.send_error(HTTPStatus.NOT_FOUND)
                return

            preset_id = path.removeprefix("/api/presets/")
            if preset_id.endswith("/apply"):
                self.send_error(HTTPStatus.NOT_FOUND)
                return

            try:
                deleted = preset_store.delete_preset(preset_id)
                if not deleted:
                    self._send_json(HTTPStatus.NOT_FOUND, {"error": "preset not found"})
                    return
                self._send_json(HTTPStatus.OK, {"ok": True})
            except Exception as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

    return WebUIHandler


def dashboard_reachable(config: HandConfig, timeout_seconds: float = 1.5) -> bool:
    url = f"{config.dashboard_url.rstrip('/')}/api/hand/devices"
    try:
        response = requests.get(url, timeout=timeout_seconds)
        response.raise_for_status()
        return True
    except requests.RequestException:
        return False


def _connection_hint(backend: str, config: HandConfig) -> str:
    if backend == "dashboard":
        return (
            f"请先启动官方 Linker Hand dashboard（{config.dashboard_url}），"
            "或改用 SDK 启动：py -3 -m l10_hand_control.web_server --backend sdk"
        )
    sdk_path = config.sdk_path or DEFAULT_SDK_PATH
    return (
        "请确认 PCAN 已连接、官方 dashboard 已关闭，且 SDK 路径正确。"
        f" SDK: {sdk_path}"
    )


def resolve_backend(
    backend: str,
    config: HandConfig,
    sdk_path: Path | None,
) -> tuple[str, HandConfig]:
    resolved_sdk_path = sdk_path or config.sdk_path or DEFAULT_SDK_PATH

    if backend != "auto":
        if backend == "sdk" and resolved_sdk_path:
            return backend, HandConfig(**{**config.__dict__, "sdk_path": resolved_sdk_path})
        return backend, config

    if dashboard_reachable(config):
        return "dashboard", config

    if resolved_sdk_path.exists():
        print(
            f"Dashboard not reachable at {config.dashboard_url}; "
            f"using SDK backend ({resolved_sdk_path})"
        )
        return "sdk", HandConfig(**{**config.__dict__, "sdk_path": resolved_sdk_path})

    raise RuntimeError(
        "No control backend is available. Either start the official dashboard at "
        f"{config.dashboard_url}, or install the SDK at {resolved_sdk_path} "
        "(run scripts\\install_official_sdk.cmd)."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="L10 joint control web UI")
    parser.add_argument("--config", type=Path, help="YAML config path")
    parser.add_argument(
        "--backend",
        choices=["auto", "dashboard", "sdk"],
        default="sdk",
        help="Control backend (default: sdk — use dashboard only when dashboard.exe is running)",
    )
    parser.add_argument(
        "--sdk-path",
        type=Path,
        default=None,
        help=f"Official SDK checkout path (default: {DEFAULT_SDK_PATH})",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Web server bind address")
    parser.add_argument("--port", type=int, default=8765, help="Web server port")
    parser.add_argument(
        "--presets",
        type=Path,
        default=DEFAULT_PRESETS_PATH,
        help="JSON file for saved pose presets",
    )
    args = parser.parse_args(argv)

    config = load_config(args.config)
    try:
        backend, config = resolve_backend(args.backend, config, args.sdk_path)
        controller = build_controller(backend, config)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    preset_store = PresetStore(args.presets)
    pose_sender = AsyncPoseSender(controller, min_interval=0.033)
    pose_sender.start()
    handler = make_handler(controller, preset_store, backend, config, pose_sender)
    server = ThreadingHTTPServer((args.host, args.port), handler)

    url = f"http://{args.host}:{args.port}/"
    print(f"L10 Web UI running at {url}")
    print(f"Backend: {backend} | Presets: {args.presets}")
    print("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping web UI.")
        pose_sender.stop()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
