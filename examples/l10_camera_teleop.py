"""Teleoperate a Linker Hand L10 from a webcam using hand pose tracking.

Reads your palm/fingers from the camera and mirrors the pose onto the L10 hand.

Requirements (install once):
    py -m pip install -e ".[vision]"

Dashboard backend (default):
    1. Start the official Linker Hand dashboard.
    2. Run:
       py examples/l10_camera_teleop.py

SDK backend (dashboard must be closed):
    py -m pip install -e ".[sdk]"
    py examples/l10_camera_teleop.py --backend sdk --sdk-path vendor/linkerhand-python-sdk

Dry-run without hardware (preview only, hand will NOT move):
    py examples/l10_camera_teleop.py --dry-run

Control real L10 hand (pick ONE backend):
    py examples/l10_camera_teleop.py --backend sdk --sdk-path vendor/linkerhand-python-sdk
    py examples/l10_camera_teleop.py --backend dashboard

Note: On Windows, use `py` instead of `python` if `python` does nothing.
Do NOT pass --dry-run when you want the L10 to move.
"""

from __future__ import annotations

import argparse
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SDK_PATH = ROOT / "vendor" / "linkerhand-python-sdk"


def _startup(message: str) -> None:
    print(message, flush=True)


def _import_vision_deps():
    try:
        import cv2
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing OpenCV. Install vision dependencies with:\n"
            "  py -m pip install -e \".[vision]\""
        ) from exc
    return cv2


def _import_control_deps():
    from l10_hand_control.cli import build_controller
    from l10_hand_control.config import HandConfig, load_config
    from l10_hand_control.errors import ControlError
    from l10_hand_control.hand_tracking import PoseSmoother, landmarks_to_pose, teleop_open_palm_pose
    from l10_hand_control.l10_pose import L10_JOINTS
    from l10_hand_control.mediapipe_hands import HandTracker, draw_hand_landmarks

    return (
        ControlError,
        HandConfig,
        HandTracker,
        L10_JOINTS,
        PoseSmoother,
        build_controller,
        draw_hand_landmarks,
        landmarks_to_pose,
        load_config,
        teleop_open_palm_pose,
    )


def _draw_status_banner(frame, lines: list[str], cv2, color: tuple[int, int, int]) -> None:
    y = 28
    for line in lines:
        cv2.putText(
            frame,
            line,
            (12, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2,
            cv2.LINE_AA,
        )
        y += 28


def _draw_pose_overlay(
    frame,
    pose: list[int],
    joint_names: list[str],
    cv2,
    y_offset: int = 90,
) -> None:
    lines = ["L10 pose:"]
    for name, value in zip(joint_names, pose, strict=True):
        lines.append(f"  {name}={value}")
    y = y_offset
    for line in lines:
        cv2.putText(
            frame,
            line,
            (12, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 255, 0),
            1,
            cv2.LINE_AA,
        )
        y += 18


def _validate_sdk_path(path: Path) -> None:
    if path.exists():
        return
    raise SystemExit(
        f"SDK path not found: {path}\n"
        "Clone the official SDK first:\n"
        "  .\\scripts\\install_official_sdk.ps1"
    )


def _open_camera(cv2, camera_index: int):
    if sys.platform == "win32":
        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(camera_index)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def _make_pose_sender(args, controller, min_interval: float):
    from l10_hand_control.async_pose_sender import AsyncPoseSender

    last_pose: list[int] | None = None

    def on_sent(pose: list[int], count: int) -> None:
        nonlocal last_pose
        if args.verbose and pose != last_pose:
            print(f"sent pose #{count}: {pose}", flush=True)
        last_pose = list(pose)

    sender = AsyncPoseSender(controller, min_interval=min_interval, on_sent=on_sent)
    sender.start()
    return sender


def _hardware_self_test(controller, open_pose: list[int]) -> None:
    from l10_hand_control.l10_pose import build_pose

    _startup("Running hardware self-test: index finger close -> open ...")
    controller.move_pose(build_pose({"index_root": 40}))
    time.sleep(0.8)
    controller.move_pose(open_pose)
    _startup("Hardware self-test done. If the index finger did not move, check CAN/dashboard.")


def _connect_controller(args, config, build_controller, teleop_open_pose, ControlError):
    if args.backend == "sdk":
        _validate_sdk_path(Path(args.sdk_path))

    _startup(f"Connecting to L10 via {args.backend} backend...")
    try:
        controller = build_controller(args.backend, config)
        if args.backend == "dashboard":
            controller.set_speed(args.speed)
        else:
            controller.set_speed([args.speed] * 10)
        controller.move_pose(teleop_open_pose)
    except ControlError as exc:
        raise SystemExit(f"ERROR: {exc}") from exc

    _startup("L10 hand connected.")
    if args.self_test:
        _hardware_self_test(controller, teleop_open_pose)
    return controller


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, help="YAML config path")
    parser.add_argument(
        "--backend",
        choices=["dashboard", "sdk"],
        default="dashboard",
        help="Control backend. Use sdk only when the dashboard is closed.",
    )
    parser.add_argument("--sdk-path", type=Path, default=DEFAULT_SDK_PATH)
    parser.add_argument("--camera", type=int, default=0, help="Webcam device index")
    parser.add_argument(
        "--tracked-hand",
        choices=["Left", "Right"],
        default="Right",
        help="Which hand MediaPipe should track in the camera view",
    )
    parser.add_argument("--mirror", action="store_true", help="Flip the camera preview horizontally")
    parser.add_argument("--speed", type=int, default=120, help="Hand movement speed (0..255)")
    parser.add_argument(
        "--update-hz",
        type=float,
        default=15.0,
        help="Maximum pose commands sent to the hand per second",
    )
    parser.add_argument(
        "--smoothing",
        type=float,
        default=0.28,
        help="Pose smoothing factor in (0, 1]; lower = smoother but slower",
    )
    parser.add_argument(
        "--finger-smoothing",
        type=float,
        default=0.10,
        help="Extra smoothing for the four finger-root joints (lower = steadier)",
    )
    parser.add_argument(
        "--sensitivity",
        type=float,
        default=1.2,
        help="Amplify hand motion mapping (>1 = larger L10 movement)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Track hand only, do not move hardware")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="On startup, briefly move the index finger to verify hardware",
    )
    parser.add_argument(
        "--sync-hand",
        action="store_true",
        help="Send poses synchronously (can freeze preview if CAN is slow)",
    )
    parser.add_argument("--verbose", action="store_true", help="Print each pose sent to the L10")
    parser.add_argument("--no-preview", action="store_true", help="Disable OpenCV preview window")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _startup("Starting L10 camera teleop...")
    args = parse_args(argv)
    cv2 = _import_vision_deps()
    _startup("Loading control modules...")
    (
        ControlError,
        HandConfig,
        HandTracker,
        L10_JOINTS,
        PoseSmoother,
        build_controller,
        draw_hand_landmarks,
        landmarks_to_pose,
        load_config,
        teleop_open_palm_pose,
    ) = _import_control_deps()

    teleop_open_pose = teleop_open_palm_pose()

    config = load_config(args.config)
    if args.sdk_path is not None:
        config = HandConfig(**{**config.__dict__, "sdk_path": args.sdk_path})

    controller = None
    if not args.dry_run:
        controller = _connect_controller(
            args, config, build_controller, teleop_open_pose, ControlError
        )
    else:
        print(
            "WARNING: --dry-run is ON. The L10 will NOT move. "
            "Remove --dry-run to control the real hand.",
            flush=True,
        )

    _startup(f"Opening camera {args.camera}...")
    cap = _open_camera(cv2, args.camera)
    if not cap.isOpened():
        print(f"ERROR: Cannot open camera {args.camera}", file=sys.stderr, flush=True)
        return 1

    _startup("Loading hand tracking model (first run may download ~10 MB)...")
    tracker = HandTracker(num_hands=1)
    smoother = PoseSmoother(
        alpha=args.smoothing,
        thumb_alpha=min(1.0, args.smoothing * 1.8),
        finger_alpha=max(0.06, args.finger_smoothing),
    )
    min_interval = 1.0 / max(args.update_hz, 1.0)
    last_send = 0.0
    tracked_label = args.tracked_hand
    send_count = 0
    last_pose: list[int] | None = None
    pose_sender = None
    if controller is not None and not args.sync_hand:
        pose_sender = _make_pose_sender(args, controller, min_interval)
        _startup("Hand control running in background (camera loop will stay responsive).")

    print("Camera teleop started. Press Q or Esc in the preview window to quit.", flush=True)
    if args.dry_run:
        print("Dry-run mode: camera tracking only.", flush=True)
    else:
        print(f"Live mode: sending poses to L10 via {args.backend}.", flush=True)

    try:
        first_frame = True
        while True:
            ok, frame = cap.read()
            if not ok:
                print("ERROR: Failed to read camera frame", file=sys.stderr, flush=True)
                return 1

            if first_frame:
                _startup("Camera preview running.")
                first_frame = False

            if args.mirror:
                frame = cv2.flip(frame, 1)

            if args.dry_run:
                _draw_status_banner(
                    frame,
                    ["DRY-RUN: L10 will NOT move", "Remove --dry-run for live control"],
                    cv2,
                    (0, 0, 255),
                )
            elif controller is not None:
                active_send_count = pose_sender.sent_count if pose_sender is not None else send_count
                _draw_status_banner(
                    frame,
                    [f"LIVE: controlling L10 ({args.backend})", f"Commands sent: {active_send_count}"],
                    cv2,
                    (0, 220, 0),
                )

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            detected_hands = tracker.detect(rgb)
            pose = None
            selected = None

            for hand in detected_hands:
                if hand.handedness == tracked_label:
                    selected = hand
                    break
            if selected is None and detected_hands:
                selected = detected_hands[0]

            if selected is not None:
                raw_pose = landmarks_to_pose(
                    selected.landmarks,
                    sensitivity=args.sensitivity,
                    hand_type=config.hand_type,
                )
                pose = smoother.update(raw_pose)
                now = time.monotonic()
                if controller is not None and (now - last_send) >= min_interval:
                    if pose_sender is not None:
                        pose_sender.submit(pose)
                        last_send = now
                    else:
                        try:
                            controller.move_pose(pose)
                            last_send = now
                            send_count += 1
                            if args.verbose and pose != last_pose:
                                print(f"sent pose #{send_count}: {pose}", flush=True)
                            last_pose = list(pose)
                        except Exception as exc:
                            print(f"WARNING: move_pose failed: {exc}", flush=True)
                if not args.no_preview:
                    draw_hand_landmarks(frame, selected.landmarks, cv2)
                    _draw_pose_overlay(frame, pose, L10_JOINTS, cv2)
            else:
                smoother.reset()
                if not args.no_preview:
                    cv2.putText(
                        frame,
                        f"Show your {tracked_label.lower()} hand to the camera",
                        (12, 28),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 180, 255),
                        2,
                        cv2.LINE_AA,
                    )

            if not args.no_preview:
                cv2.imshow("L10 Camera Teleop", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in {27, ord("q"), ord("Q")}:
                    break
            elif pose is not None:
                print("pose:", pose, flush=True)

    finally:
        if pose_sender is not None:
            pose_sender.stop()
        tracker.close()
        cap.release()
        if not args.no_preview:
            cv2.destroyAllWindows()
        if controller is not None and args.sync_hand:
            try:
                controller.move_pose(teleop_open_pose)
            except Exception as exc:
                print(f"WARNING: final move_pose failed: {exc}", flush=True)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nStopped by user.", flush=True)
        raise SystemExit(0)
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
