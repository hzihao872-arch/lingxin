"""L25 pressure-triggered handshake test.

This is separate from the L10 script because L25 uses 25 pose values, while L10
uses 10. Press Ctrl+C to stop; the script will try to reopen the hand.
"""

from __future__ import annotations

import sys
import time
from numbers import Number
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SDK_PATH = ROOT / "vendor" / "linkerhand-python-sdk"
sys.path.insert(0, str(SDK_PATH))

from LinkerHand.linker_hand_api import LinkerHandApi  # noqa: E402


CAN_CHANNEL = "PCAN_USBBUS1"
HAND_TYPE = "left"
THRESHOLD = 5
POLL_SECONDS = 0.15
GRIP_SECONDS = 1.2
COOLDOWN_SECONDS = 1.0

# Official L25 open-palm pose from LinkerHand/config/L25_positions.yaml.
OPEN_POSE_L25 = [
    96,
    255,
    255,
    255,
    255,
    150,
    114,
    151,
    189,
    255,
    180,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
    255,
]

# Gentle handshake-like pose. Lower values generally bend joints more.
# If too loose, reduce index/middle/ring/pinky middle/tip values gradually.
HANDSHAKE_POSE_L25 = [
    170,
    120,
    100,
    95,
    80,
    80,
    114,
    151,
    189,
    255,
    110,
    255,
    255,
    255,
    255,
    180,
    90,
    80,
    80,
    80,
    120,
    70,
    60,
    60,
    60,
]


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


def read_pressure(hand: Any) -> Any:
    touch_type = hand.get_touch_type()
    if touch_type == 2:
        return hand.get_matrix_touch()
    if touch_type == 1:
        return hand.get_force()
    if touch_type == -1:
        return [-1]
    return hand.get_touch()


def main() -> None:
    hand = LinkerHandApi(
        hand_joint="L25",
        hand_type=HAND_TYPE,
        can=CAN_CHANNEL,
    )

    hand.set_speed([80] * 25)
    hand.finger_move(OPEN_POSE_L25)

    print("L25 pressure-triggered handshake test.")
    print(f"CAN={CAN_CHANNEL}, hand_type={HAND_TYPE}, threshold={THRESHOLD}")
    print("Touch/press the sensor area to trigger. Press Ctrl+C to stop.")

    try:
        while True:
            pressure = read_pressure(hand)
            values = flatten_numbers(pressure)
            max_value = max(values) if values else None
            print(f"pressure max={max_value}, raw={pressure}")

            if has_pressure(pressure):
                print("Pressure detected. Closing L25 hand.")
                hand.set_speed([100] * 25)
                hand.finger_move(HANDSHAKE_POSE_L25)
                time.sleep(GRIP_SECONDS)
                hand.finger_move(OPEN_POSE_L25)
                time.sleep(COOLDOWN_SECONDS)
            else:
                time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        print()
        print("Stopped. Opening L25 hand.")
        hand.finger_move(OPEN_POSE_L25)


if __name__ == "__main__":
    main()
