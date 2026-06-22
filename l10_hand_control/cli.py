from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable

from l10_hand_control.config import HandConfig, load_config
from l10_hand_control.dashboard import DashboardController
from l10_hand_control.errors import ControlError
from l10_hand_control.l10_pose import L10_JOINTS, build_pose, parse_joint_assignments
from l10_hand_control.sdk_backend import SdkController


def build_controller(backend: str, config: HandConfig):
    if backend == "dashboard":
        return DashboardController(config)
    if backend == "sdk":
        return SdkController(config)
    raise ValueError(f"Unsupported backend: {backend}")


def main(
    argv: list[str] | None = None,
    controller_factory: Callable[[str, HandConfig], object] = build_controller,
) -> int:
    parser = argparse.ArgumentParser(
        prog="l10-hand",
        description="Control a Linker Hand L10 left hand via dashboard API or official SDK.",
    )
    parser.add_argument("--config", type=Path, help="YAML config path")
    parser.add_argument(
        "--backend",
        choices=["dashboard", "sdk"],
        default="dashboard",
        help="Control backend. dashboard is safe when the official dashboard is running.",
    )
    parser.add_argument("--sdk-path", type=Path, help="Official SDK checkout path")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor")
    subparsers.add_parser("list-devices")

    gesture_parser = subparsers.add_parser("gesture")
    gesture_parser.add_argument("name")

    speed_parser = subparsers.add_parser("speed")
    speed_parser.add_argument("value", type=int)

    pose_parser = subparsers.add_parser("pose")
    pose_parser.add_argument("values", help="10 comma-separated values, e.g. 80,80,...")

    joint_parser = subparsers.add_parser("joint")
    joint_parser.add_argument(
        "assignments",
        nargs="+",
        help="Named L10 joint assignments, e.g. index_root=0 thumb_rotation=30",
    )

    subparsers.add_parser("state")

    args = parser.parse_args(argv)
    config = load_config(args.config)
    if args.sdk_path is not None:
        config = HandConfig(**{**config.__dict__, "sdk_path": args.sdk_path})

    if args.command == "doctor":
        print(json.dumps(_doctor_payload(args.backend, config), ensure_ascii=False, indent=2))
        return 0

    try:
        controller = controller_factory(args.backend, config)

        if args.command == "list-devices":
            result = controller.list_devices()
        elif args.command == "gesture":
            result = controller.execute_gesture(args.name)
        elif args.command == "speed":
            result = controller.set_speed(args.value)
        elif args.command == "pose":
            result = controller.move_pose(_parse_csv_ints(args.values))
        elif args.command == "joint":
            result = controller.move_pose(
                build_pose(parse_joint_assignments(args.assignments))
            )
        elif args.command == "state":
            result = controller.get_state()
        else:
            parser.error(f"Unsupported command: {args.command}")
    except ControlError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _parse_csv_ints(value: str) -> list[int]:
    try:
        values = [int(part.strip()) for part in value.split(",") if part.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("pose values must be integers") from exc
    if len(values) != 10:
        raise argparse.ArgumentTypeError("L10 pose requires exactly 10 values")
    return values


def _doctor_payload(backend: str, config: HandConfig) -> dict[str, object]:
    return {
        "backend": backend,
        "hand_type": config.hand_type,
        "hand_joint": config.hand_joint,
        "can": config.can,
        "dashboard_url": config.dashboard_url,
        "dashboard_interface": config.dashboard_interface,
        "l10_variant": config.l10_variant,
        "sdk_path": str(config.sdk_path) if config.sdk_path else None,
        "l10_joints": L10_JOINTS,
    }
