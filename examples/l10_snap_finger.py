"""Snap-finger gesture flow for a Linker Hand L10.

Close the official dashboard before running this SDK example.
Values are 0..255. Larger values usually mean more open, smaller values more bent.

The flow mimics a human finger snap:
1. open palm
2. curl index, ring, and pinky while keeping the middle finger ready
3. press thumb and middle finger together
4. quickly extend the middle finger to release the snap
5. return to open palm and repeat
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TypedDict

from l10_hand_control.config import HandConfig
from l10_hand_control.l10_pose import build_pose
from l10_hand_control.sdk_backend import SdkController


class SnapStep(TypedDict):
    name: str
    pose: list[int]
    delay_seconds: float
    speed: list[int]


ROOT = Path(__file__).resolve().parents[1]
SDK_PATH = ROOT / "vendor" / "linkerhand-python-sdk"

LOOP_COUNT = 5
NORMAL_SPEED = [80] * 10
SNAP_SPEED = [90, 90, 80, 255, 80, 80, 80, 80, 80, 90]

# Reuse the curled-finger baseline from examples/custom_l10_control.py.
FOLDED_FINGERS = {
    "index_root": 80,
    "ring_root": 80,
    "pinky_root": 80,
}

# Thumb posture reused from the number-gesture example.
CURLED_THUMB = {
    "thumb_root": 80,
    "thumb_swing": 80,
    "thumb_rotation": 80,
}

OPEN_POSE = build_pose({})

PREPARE_POSE = build_pose(
    {
        **FOLDED_FINGERS,
        **CURLED_THUMB,
        "middle_root": 210,
        "index_swing": 255,
        "ring_swing": 180,
        "pinky_swing": 180,
    }
)

PRELOAD_POSE = build_pose(
    {
        **FOLDED_FINGERS,
        "middle_root": 60,
        "thumb_root": 65,
        "thumb_swing": 55,
        "thumb_rotation": 110,
        "index_swing": 255,
        "ring_swing": 180,
        "pinky_swing": 180,
    }
)

SNAP_POSE = build_pose(
    {
        **FOLDED_FINGERS,
        "middle_root": 255,
        "thumb_root": 95,
        "thumb_swing": 70,
        "thumb_rotation": 100,
        "index_swing": 255,
        "ring_swing": 180,
        "pinky_swing": 180,
    }
)

SNAP_CYCLE: list[SnapStep] = [
    {"name": "open", "pose": OPEN_POSE, "delay_seconds": 0.4, "speed": NORMAL_SPEED},
    {"name": "prepare", "pose": PREPARE_POSE, "delay_seconds": 0.5, "speed": NORMAL_SPEED},
    {"name": "preload", "pose": PRELOAD_POSE, "delay_seconds": 0.35, "speed": NORMAL_SPEED},
    {"name": "snap", "pose": SNAP_POSE, "delay_seconds": 0.12, "speed": SNAP_SPEED},
    {"name": "settle", "pose": OPEN_POSE, "delay_seconds": 0.35, "speed": NORMAL_SPEED},
]


def snap_sequence(loop_count: int = LOOP_COUNT) -> list[SnapStep]:
    """Build the full snap plan, repeated loop_count times."""
    sequence: list[SnapStep] = []
    for _round_index in range(loop_count):
        sequence.extend(SNAP_CYCLE)
    return sequence


def main() -> None:
    hand = SdkController(
        HandConfig(
            hand_type="left",
            hand_joint="L10",
            can="PCAN_USBBUS1",
            sdk_path=SDK_PATH,
        )
    )

    for step_index, step in enumerate(snap_sequence(), start=1):
        print(
            f"Step {step_index}: {step['name']}, "
            f"delay={step['delay_seconds']}s, pose={step['pose']}"
        )
        hand.set_speed(step["speed"])
        hand.move_pose(step["pose"])
        time.sleep(step["delay_seconds"])

    print("Current state:", hand.get_state())


if __name__ == "__main__":
    main()
