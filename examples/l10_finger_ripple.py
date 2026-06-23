"""Ripple wave triggered by L10 fingertip touch.

Close the official dashboard before running this SDK example.

Flow:
1. Hold an open palm and poll fingertip sensors.
2. When one finger is pressed hardest, curl that finger first.
3. Propagate the curl to neighboring fingers, then extend back to open.
"""

from __future__ import annotations

import time
from numbers import Number
from pathlib import Path
from typing import Any

from l10_hand_control.config import HandConfig
from l10_hand_control.l10_pose import build_pose
from l10_hand_control.sdk_backend import SdkController


ROOT = Path(__file__).resolve().parents[1]
SDK_PATH = ROOT / "vendor" / "linkerhand-python-sdk"

CAN_CHANNEL = "PCAN_USBBUS1"
THRESHOLD = 0.0001
POLL_SECONDS = 0.12
STEP_DELAY_SECONDS = 0.18
COOLDOWN_SECONDS = 0.6
MOVE_SPEED = [90] * 10

FINGER_NAMES = ("thumb", "index", "middle", "ring", "pinky")

# Per-finger curl overrides. Smaller root/swing values bend more.
FINGER_CURL_OVERRIDES: dict[int, dict[str, int]] = {
    0: {"thumb_root": 85, "thumb_swing": 75, "thumb_rotation": 85},
    1: {"index_root": 85, "index_swing": 140},
    2: {"middle_root": 85},
    3: {"ring_root": 85, "ring_swing": 140},
    4: {"pinky_root": 85, "pinky_swing": 140},
}

OPEN_POSE = build_pose({})


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


def read_finger_touch(hand: Any) -> Any:
    return hand.get_touch()


def ripple_order(trigger: int) -> list[int]:
    """Spread from the touched finger toward both sides along the hand."""
    if trigger < 0 or trigger > 4:
        raise ValueError(f"Finger index must be 0..4, got {trigger}")

    order = [trigger]
    for distance in range(1, 5):
        for offset in (distance, -distance):
            finger = trigger + offset
            if 0 <= finger <= 4:
                order.append(finger)
    return order


def pose_with_curled(curled: set[int]) -> list[int]:
    overrides: dict[str, int] = {}
    for finger in sorted(curled):
        overrides.update(FINGER_CURL_OVERRIDES[finger])
    return build_pose(overrides)


def ripple_steps(trigger: int, step_delay: float = STEP_DELAY_SECONDS) -> list[tuple[str, list[int], float]]:
    """Build curl-then-extend frames for one ripple starting at trigger."""
    order = ripple_order(trigger)
    steps: list[tuple[str, list[int], float]] = []
    curled: set[int] = set()

    for finger in order:
        curled.add(finger)
        steps.append((f"curl_{FINGER_NAMES[finger]}", pose_with_curled(curled), step_delay))

    for finger in reversed(order):
        curled.remove(finger)
        steps.append((f"extend_{FINGER_NAMES[finger]}", pose_with_curled(curled), step_delay))

    return steps


def dominant_finger(value: Any, threshold: float = THRESHOLD) -> int | None:
    numbers = flatten_numbers(value)[:5]
    if len(numbers) < 5:
        return None

    best_index = max(range(5), key=lambda index: numbers[index])
    if numbers[best_index] <= threshold:
        return None
    return best_index


def wait_for_touch(hand: Any) -> int:
    """Block until one fingertip exceeds the threshold."""
    while True:
        touch = read_finger_touch(hand)
        trigger = dominant_finger(touch)
        values = flatten_numbers(touch)[:5]
        print(f"touch={values}, waiting for ripple trigger")
        if trigger is not None:
            print(f"Ripple trigger: {FINGER_NAMES[trigger]}")
            return trigger
        time.sleep(POLL_SECONDS)


def run_ripple(controller: SdkController, trigger: int) -> None:
    for step_name, pose, delay in ripple_steps(trigger):
        print(f"ripple step: {step_name}, pose={pose}")
        controller.set_speed(MOVE_SPEED)
        controller.move_pose(pose)
        time.sleep(delay)


def main() -> None:
    controller = SdkController(
        HandConfig(
            hand_type="left",
            hand_joint="L10",
            can=CAN_CHANNEL,
            sdk_path=SDK_PATH,
        )
    )

    controller.set_speed(MOVE_SPEED)
    controller.move_pose(OPEN_POSE)

    print("Ripple hand ready. Press a fingertip to start. Ctrl+C to stop.")
    print(f"CAN={CAN_CHANNEL}, threshold={THRESHOLD}")

    try:
        while True:
            trigger = wait_for_touch(controller.hand)
            run_ripple(controller, trigger)
            controller.move_pose(OPEN_POSE)
            time.sleep(COOLDOWN_SECONDS)
    except KeyboardInterrupt:
        print()
        print("Stopped. Opening hand.")
        controller.move_pose(OPEN_POSE)


if __name__ == "__main__":
    main()
