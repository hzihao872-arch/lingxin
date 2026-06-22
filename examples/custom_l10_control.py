"""Loop through number gestures 1, 2, 3, 4, 5 on a Linker Hand L10.

Close the official dashboard before running this SDK example.
Values are 0..255. Larger values usually mean more open, smaller values more bent.
"""

from __future__ import annotations

import time
from pathlib import Path

from l10_hand_control.config import HandConfig
from l10_hand_control.l10_pose import build_pose
from l10_hand_control.sdk_backend import SdkController


ROOT = Path(__file__).resolve().parents[1]
SDK_PATH = ROOT / "vendor" / "linkerhand-python-sdk"

# Basic Python syntax:
# - Variables store values, for example LOOP_COUNT = 10.
# - A dict stores key/value pairs, for example "1": build_pose(...).
# - A list stores ordered items, for example [60] * 10 means ten 60s.
# - A for loop repeats work, for example for round_index in range(10).
LOOP_COUNT = 10
POSE_DELAY_SECONDS = 1

# 1-4 use a curled thumb and then open the needed fingers.
# If a gesture looks wrong on the real hand, tune only these numbers first.
CURLED_THUMB = {
    "thumb_root": 80,
    "thumb_swing": 80,
    "thumb_rotation": 80,
}

NUMBER_GESTURES = {
    "1": build_pose({**CURLED_THUMB, "index_root": 255, "middle_root": 80, "ring_root": 80, "pinky_root": 80}),
    "2": build_pose({**CURLED_THUMB, "index_root": 255, "middle_root": 255, "ring_root": 80, "pinky_root": 80}),
    "3": build_pose({**CURLED_THUMB, "index_root": 255, "middle_root": 255, "ring_root": 255, "pinky_root": 80}),
    "4": build_pose({**CURLED_THUMB, "index_root": 255, "middle_root": 255, "ring_root": 255, "pinky_root": 255}),
    "5": build_pose({}),
}


def gesture_sequence() -> list[tuple[str, list[int]]]:
    """Build the full movement plan: 1,2,3,4,5 repeated ten times."""
    sequence = []
    for _round_index in range(LOOP_COUNT):
        for gesture_name, pose in NUMBER_GESTURES.items():
            sequence.append((gesture_name, pose))
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

    hand.set_speed([100] * 10)

    for step_index, (gesture_name, pose) in enumerate(gesture_sequence(), start=1):
        print(f"Step {step_index}: gesture {gesture_name}, pose={pose}")
        hand.move_pose(pose)
        time.sleep(POSE_DELAY_SECONDS)

    print("Current state:", hand.get_state())


if __name__ == "__main__":
    main()
