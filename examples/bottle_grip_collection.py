"""Collect manual success/fail labels for L10 bottle-grip parameter trials.

Run this script with the bottle safely placed in the hand. Each trial moves the
hand to one preset pose, then asks you to type 1 for success or 0 for failure.
Results are appended to data/bottle_grip_results.csv.
"""

from __future__ import annotations

import csv
import time
from datetime import datetime
from pathlib import Path
from typing import TypedDict

from l10_hand_control.config import HandConfig
from l10_hand_control.l10_pose import L10_JOINTS, build_pose
from l10_hand_control.sdk_backend import SdkController


class BottleGripTrial(TypedDict):
    name: str
    speed: int
    hold_seconds: float
    joints: dict[str, int]


ROOT = Path(__file__).resolve().parents[1]
SDK_PATH = ROOT / "vendor" / "linkerhand-python-sdk"
RESULTS_PATH = ROOT / "data" / "bottle_grip_results.csv"

# Change these three values first if you want a slower or faster experiment.
OPEN_SECONDS = 1.0
REST_SECONDS = 0.8
DEFAULT_SPEED = 80

# Unified parameter area:
# - name: your label for this trial
# - speed: hand movement speed, 0..255
# - hold_seconds: how long to hold the bottle before you type success/fail
# - joints: only the joints you want to override from the open-palm pose
#
# L10 joint names:
# thumb_root, thumb_swing, index_root, middle_root, ring_root, pinky_root,
# index_swing, ring_swing, pinky_swing, thumb_rotation
BOTTLE_GRIP_TRIALS: list[BottleGripTrial] = [
    {
        "name": "soft_wrap_01",
        "speed": 60,
        "hold_seconds": 2.0,
        "joints": {
            "thumb_root": 150,
            "thumb_swing": 70,
            "thumb_rotation": 88,
            "index_root": 155,
            "middle_root": 155,
            "ring_root": 180,
            "pinky_root": 180,
            "index_swing": 130,
            "ring_swing": 220,
            "pinky_swing": 220,
        },
    },
    {
        "name": "soft_wrap_02",
        "speed": 60,
        "hold_seconds": 2.0,
        "joints": {
            "thumb_root": 140,
            "thumb_swing": 70,
            "thumb_rotation": 88,
            "index_root": 145,
            "middle_root": 145,
            "ring_root": 170,
            "pinky_root": 170,
            "index_swing": 120,
            "ring_swing": 215,
            "pinky_swing": 215,
        },
    },
    {
        "name": "soft_wrap_03",
        "speed": 70,
        "hold_seconds": 2.0,
        "joints": {
            "thumb_root": 130,
            "thumb_swing": 70,
            "thumb_rotation": 88,
            "index_root": 135,
            "middle_root": 135,
            "ring_root": 160,
            "pinky_root": 160,
            "index_swing": 115,
            "ring_swing": 210,
            "pinky_swing": 210,
        },
    },
    {
        "name": "medium_wrap_01",
        "speed": 70,
        "hold_seconds": 2.0,
        "joints": {
            "thumb_root": 120,
            "thumb_swing": 70,
            "thumb_rotation": 88,
            "index_root": 125,
            "middle_root": 125,
            "ring_root": 145,
            "pinky_root": 145,
            "index_swing": 105,
            "ring_swing": 200,
            "pinky_swing": 200,
        },
    },
    {
        "name": "medium_wrap_02",
        "speed": 80,
        "hold_seconds": 2.0,
        "joints": {
            "thumb_root": 110,
            "thumb_swing": 70,
            "thumb_rotation": 88,
            "index_root": 115,
            "middle_root": 115,
            "ring_root": 135,
            "pinky_root": 135,
            "index_swing": 100,
            "ring_swing": 195,
            "pinky_swing": 195,
        },
    },
    {
        "name": "medium_wrap_03",
        "speed": 80,
        "hold_seconds": 2.0,
        "joints": {
            "thumb_root": 100,
            "thumb_swing": 70,
            "thumb_rotation": 88,
            "index_root": 105,
            "middle_root": 105,
            "ring_root": 125,
            "pinky_root": 125,
            "index_swing": 95,
            "ring_swing": 190,
            "pinky_swing": 190,
        },
    },
    {
        "name": "firm_wrap_01",
        "speed": 90,
        "hold_seconds": 2.0,
        "joints": {
            "thumb_root": 90,
            "thumb_swing": 70,
            "thumb_rotation": 88,
            "index_root": 95,
            "middle_root": 95,
            "ring_root": 115,
            "pinky_root": 115,
            "index_swing": 90,
            "ring_swing": 185,
            "pinky_swing": 185,
        },
    },
    {
        "name": "firm_wrap_02",
        "speed": 90,
        "hold_seconds": 2.0,
        "joints": {
            "thumb_root": 80,
            "thumb_swing": 70,
            "thumb_rotation": 88,
            "index_root": 85,
            "middle_root": 85,
            "ring_root": 105,
            "pinky_root": 105,
            "index_swing": 85,
            "ring_swing": 180,
            "pinky_swing": 180,
        },
    },
    {
        "name": "firm_wrap_03",
        "speed": 100,
        "hold_seconds": 2.0,
        "joints": {
            "thumb_root": 70,
            "thumb_swing": 70,
            "thumb_rotation": 88,
            "index_root": 75,
            "middle_root": 75,
            "ring_root": 95,
            "pinky_root": 95,
            "index_swing": 80,
            "ring_swing": 175,
            "pinky_swing": 175,
        },
    },
    {
        "name": "parallel_pinch_01",
        "speed": 70,
        "hold_seconds": 2.0,
        "joints": {
            "thumb_root": 130,
            "thumb_swing": 100,
            "thumb_rotation": 65,
            "index_root": 120,
            "middle_root": 140,
            "ring_root": 230,
            "pinky_root": 230,
            "index_swing": 80,
            "ring_swing": 255,
            "pinky_swing": 255,
        },
    },
    {
        "name": "parallel_pinch_02",
        "speed": 80,
        "hold_seconds": 2.0,
        "joints": {
            "thumb_root": 115,
            "thumb_swing": 110,
            "thumb_rotation": 60,
            "index_root": 105,
            "middle_root": 125,
            "ring_root": 220,
            "pinky_root": 220,
            "index_swing": 75,
            "ring_swing": 255,
            "pinky_swing": 255,
        },
    },
    {
        "name": "parallel_pinch_03",
        "speed": 90,
        "hold_seconds": 2.0,
        "joints": {
            "thumb_root": 100,
            "thumb_swing": 120,
            "thumb_rotation": 55,
            "index_root": 90,
            "middle_root": 110,
            "ring_root": 210,
            "pinky_root": 210,
            "index_swing": 70,
            "ring_swing": 255,
            "pinky_swing": 255,
        },
    },
    {
        "name": "three_finger_01",
        "speed": 70,
        "hold_seconds": 2.0,
        "joints": {
            "thumb_root": 125,
            "thumb_swing": 90,
            "thumb_rotation": 70,
            "index_root": 115,
            "middle_root": 115,
            "ring_root": 255,
            "pinky_root": 255,
            "index_swing": 90,
            "ring_swing": 255,
            "pinky_swing": 255,
        },
    },
    {
        "name": "three_finger_02",
        "speed": 80,
        "hold_seconds": 2.0,
        "joints": {
            "thumb_root": 110,
            "thumb_swing": 100,
            "thumb_rotation": 65,
            "index_root": 100,
            "middle_root": 100,
            "ring_root": 245,
            "pinky_root": 245,
            "index_swing": 85,
            "ring_swing": 255,
            "pinky_swing": 255,
        },
    },
    {
        "name": "three_finger_03",
        "speed": 90,
        "hold_seconds": 2.0,
        "joints": {
            "thumb_root": 95,
            "thumb_swing": 110,
            "thumb_rotation": 60,
            "index_root": 85,
            "middle_root": 85,
            "ring_root": 235,
            "pinky_root": 235,
            "index_swing": 80,
            "ring_swing": 255,
            "pinky_swing": 255,
        },
    },
    {
        "name": "wide_bottle_01",
        "speed": 70,
        "hold_seconds": 2.0,
        "joints": {
            "thumb_root": 170,
            "thumb_swing": 70,
            "thumb_rotation": 95,
            "index_root": 175,
            "middle_root": 175,
            "ring_root": 190,
            "pinky_root": 190,
            "index_swing": 145,
            "ring_swing": 230,
            "pinky_swing": 230,
        },
    },
    {
        "name": "wide_bottle_02",
        "speed": 80,
        "hold_seconds": 2.0,
        "joints": {
            "thumb_root": 155,
            "thumb_swing": 75,
            "thumb_rotation": 95,
            "index_root": 160,
            "middle_root": 160,
            "ring_root": 180,
            "pinky_root": 180,
            "index_swing": 135,
            "ring_swing": 225,
            "pinky_swing": 225,
        },
    },
    {
        "name": "narrow_bottle_01",
        "speed": 70,
        "hold_seconds": 2.0,
        "joints": {
            "thumb_root": 95,
            "thumb_swing": 80,
            "thumb_rotation": 75,
            "index_root": 90,
            "middle_root": 90,
            "ring_root": 110,
            "pinky_root": 110,
            "index_swing": 85,
            "ring_swing": 185,
            "pinky_swing": 185,
        },
    },
    {
        "name": "narrow_bottle_02",
        "speed": 80,
        "hold_seconds": 2.0,
        "joints": {
            "thumb_root": 80,
            "thumb_swing": 90,
            "thumb_rotation": 70,
            "index_root": 75,
            "middle_root": 75,
            "ring_root": 95,
            "pinky_root": 95,
            "index_swing": 80,
            "ring_swing": 180,
            "pinky_swing": 180,
        },
    },
    {
        "name": "strong_clamp_01",
        "speed": 100,
        "hold_seconds": 2.5,
        "joints": {
            "thumb_root": 65,
            "thumb_swing": 75,
            "thumb_rotation": 80,
            "index_root": 70,
            "middle_root": 70,
            "ring_root": 85,
            "pinky_root": 85,
            "index_swing": 70,
            "ring_swing": 170,
            "pinky_swing": 170,
        },
    },
    {
        "name": "strong_clamp_02",
        "speed": 110,
        "hold_seconds": 2.5,
        "joints": {
            "thumb_root": 55,
            "thumb_swing": 75,
            "thumb_rotation": 80,
            "index_root": 60,
            "middle_root": 60,
            "ring_root": 75,
            "pinky_root": 75,
            "index_swing": 65,
            "ring_swing": 165,
            "pinky_swing": 165,
        },
    },
]


def trial_pose(trial: BottleGripTrial) -> list[int]:
    return build_pose(trial["joints"])


def append_result(
    csv_path: Path,
    trial_number: int,
    trial: BottleGripTrial,
    success: int,
) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = csv_path.exists()
    pose = trial_pose(trial)

    fieldnames = [
        "timestamp",
        "trial_number",
        "trial_name",
        "success",
        "speed",
        "hold_seconds",
        *L10_JOINTS,
    ]

    with csv_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "trial_number": trial_number,
                "trial_name": trial["name"],
                "success": success,
                "speed": trial["speed"],
                "hold_seconds": trial["hold_seconds"],
                **dict(zip(L10_JOINTS, pose, strict=True)),
            }
        )


def ask_success() -> int:
    while True:
        value = input("Result? Type 1=success, 0=fail, q=quit: ").strip().lower()
        if value in {"0", "1"}:
            return int(value)
        if value == "q":
            raise KeyboardInterrupt
        print("Please type only 1, 0, or q.")


def main() -> None:
    hand = SdkController(
        HandConfig(
            hand_type="left",
            hand_joint="L10",
            can="PCAN_USBBUS1",
            sdk_path=SDK_PATH,
        )
    )

    open_palm = build_pose({})
    print(f"Results will be saved to: {RESULTS_PATH}")
    print("Put the bottle in the test position. Press Ctrl+C or type q to stop.")

    try:
        for trial_number, trial in enumerate(BOTTLE_GRIP_TRIALS, start=1):
            pose = trial_pose(trial)
            print()
            print(f"Trial {trial_number}/{len(BOTTLE_GRIP_TRIALS)}: {trial['name']}")
            print(f"speed={trial['speed']}, hold_seconds={trial['hold_seconds']}")
            print(f"pose={pose}")
            input("Press Enter to open the hand and start this trial...")

            hand.set_speed([DEFAULT_SPEED] * 10)
            hand.move_pose(open_palm)
            time.sleep(OPEN_SECONDS)

            hand.set_speed([trial["speed"]] * 10)
            hand.move_pose(pose)
            time.sleep(trial["hold_seconds"])

            success = ask_success()
            append_result(RESULTS_PATH, trial_number, trial, success)
            print(f"Saved trial {trial_number} with success={success}.")

            hand.set_speed([DEFAULT_SPEED] * 10)
            hand.move_pose(open_palm)
            time.sleep(REST_SECONDS)
    except KeyboardInterrupt:
        print()
        print("Stopped. Existing saved rows are kept.")


if __name__ == "__main__":
    main()
