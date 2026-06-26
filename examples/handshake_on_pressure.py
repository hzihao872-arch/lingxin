"""Close the L10 hand when selected touch/pressure input is detected.

L10 SDK touch data is finger-based. In the current SDK, the sixth value returned
by get_touch() is palm and is hard-coded to 0, so real palm triggering is only
available if your hardware/SDK returns palm matrix data.
"""

from __future__ import annotations

import time
from numbers import Number
from pathlib import Path
from typing import Any

from l10_hand_control.config import HandConfig
from l10_hand_control.l10_pose import build_pose, move_pose_smoothed
from l10_hand_control.sdk_backend import SdkController


ROOT = Path(__file__).resolve().parents[1]
SDK_PATH = ROOT / "vendor" / "linkerhand-python-sdk"

CAN_CHANNEL = "PCAN_USBBUS1"
THRESHOLD = 0.0001
POLL_SECONDS = 0.15
GRIP_SECONDS = 5
COOLDOWN_SECONDS = 1.0
TRIGGER_SOURCE = "finger_tip"  # Options: "finger_tip", "any_force", "palm"

OPEN_POSE = build_pose({})

# Gentle handshake-like grip. If it is too loose, lower root values gradually.
HANDSHAKE_POSE = build_pose(
    {
        "thumb_root": 90,
        "thumb_swing": 80,
        "thumb_rotation": 80,
        "index_root": 95,
        "middle_root": 95,
        "ring_root": 110,
        "pinky_root": 110,
        "index_swing": 85,
        "ring_swing": 180,
        "pinky_swing": 180,
    }
)


def flatten_numbers(value: Any) -> list[float]:
    numbers: list[float] = []
    if isinstance(value, Number):
        numbers.append(float(value))
    elif isinstance(value, dict):
        for item in value.values():
            numbers.extend(flatten_numbers(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            numbers.extend(flatten_numbers(item))
    elif hasattr(value, "tolist"):
        numbers.extend(flatten_numbers(value.tolist()))
    return numbers


def has_pressure(value: Any, threshold: float = THRESHOLD) -> bool:
    return any(number > threshold for number in flatten_numbers(value))


def has_finger_pressure(value: Any, threshold: float = THRESHOLD) -> bool:
    numbers = flatten_numbers(value)
    return any(number > threshold for number in numbers[:5])


def has_palm_pressure(value: Any, threshold: float = THRESHOLD) -> bool:
    numbers = flatten_numbers(value)
    if len(numbers) < 6:
        return False
    return numbers[5] > threshold


def read_pressure(hand: Any) -> Any:
    touch_type = hand.get_touch_type()
    if touch_type == 2:
        return hand.get_matrix_touch()
    if touch_type == 1:
        return hand.get_force()
    if touch_type == -1:
        return [-1]
    return hand.get_touch()


def read_finger_touch(hand: Any) -> Any:
    return hand.get_touch()


def read_palm_touch(hand: Any) -> Any:
    if hasattr(hand, "get_palm_matrix_touch"):
        palm_touch = hand.get_palm_matrix_touch()
        if palm_touch is not None:
            return palm_touch
    return hand.get_touch()


def should_close_hand(value: Any) -> bool:
    if TRIGGER_SOURCE == "finger_tip":
        return has_finger_pressure(value)
    if TRIGGER_SOURCE == "palm":
        return has_palm_pressure(value)
    if TRIGGER_SOURCE == "any_force":
        return has_pressure(value)
    raise ValueError(f"Unsupported TRIGGER_SOURCE: {TRIGGER_SOURCE}")


def main() -> None:
    controller = SdkController(
        HandConfig(
            hand_type="left",
            hand_joint="L10",
            can=CAN_CHANNEL,
            sdk_path=SDK_PATH,
        )
    )
    hand = controller.hand

    controller.set_speed([80] * 10)
    current_pose = list(OPEN_POSE)
    current_pose = move_pose_smoothed(controller, OPEN_POSE, src=current_pose, steps=10, hz=50.0)

    print("Waiting for selected pressure input. Press Ctrl+C to stop.")
    print(f"CAN={CAN_CHANNEL}, threshold={THRESHOLD}, source={TRIGGER_SOURCE}")
    if TRIGGER_SOURCE == "palm":
        print("Note: current L10 SDK get_touch() marks palm as unavailable/0.")

    try:
        while True:
            if TRIGGER_SOURCE == "finger_tip":
                pressure = read_finger_touch(hand)
            elif TRIGGER_SOURCE == "palm":
                pressure = read_palm_touch(hand)
            else:
                pressure = read_pressure(hand)
            values = flatten_numbers(pressure)
            max_value = max(values) if values else None
            print(f"pressure max={max_value}, raw={pressure}")

            if should_close_hand(pressure):
                print("Pressure detected. Closing hand.")
                controller.set_speed([100] * 10)
                current_pose = move_pose_smoothed(
                    controller, HANDSHAKE_POSE, src=current_pose, steps=18, hz=60.0
                )
                time.sleep(GRIP_SECONDS)
                controller.set_speed([80] * 10)
                current_pose = move_pose_smoothed(
                    controller, OPEN_POSE, src=current_pose, steps=18, hz=60.0
                )
                time.sleep(COOLDOWN_SECONDS)
            else:
                time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        print()
        print("Stopped. Opening hand.")
        controller.set_speed([80] * 10)
        move_pose_smoothed(controller, OPEN_POSE, src=current_pose, steps=18, hz=60.0)


if __name__ == "__main__":
    main()
