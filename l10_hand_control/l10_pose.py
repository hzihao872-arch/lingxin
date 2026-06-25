from __future__ import annotations

L10_JOINTS = [
    "thumb_root",
    "thumb_swing",
    "index_root",
    "middle_root",
    "ring_root",
    "pinky_root",
    "index_swing",
    "ring_swing",
    "pinky_swing",
    "thumb_rotation",
]

# Protocol range for every joint command / feedback byte.
L10_PROTOCOL_MIN = 0
L10_PROTOCOL_MAX = 255

# Official open-palm example for L10 ball-joint hands.
# thumb_swing=70 is a recommended open pose, not a mechanical maximum.
# Source: vendor/.../example/L10/gesture/linker_hand_open_palm.py
OPEN_PALM_POSE = [255, 70, 255, 255, 255, 255, 255, 255, 255, 255]

# UI hints only — teach/read and manual motion can still reach 0..255.
L10_JOINT_HINTS: dict[str, str] = {
    "thumb_swing": "张开约 70，读数可达 255",
}


def get_joint_limits(variant: str = "ball_joint") -> dict[str, tuple[int, int]]:
    del variant  # reserved for future hardware-specific profiles
    return {joint: (L10_PROTOCOL_MIN, L10_PROTOCOL_MAX) for joint in L10_JOINTS}


def get_joint_hints() -> dict[str, str]:
    return dict(L10_JOINT_HINTS)


def clamp_joint_value(joint: str, value: int, variant: str = "ball_joint") -> int:
    del joint, variant
    return max(L10_PROTOCOL_MIN, min(L10_PROTOCOL_MAX, int(value)))


def clamp_pose(pose: list[int], variant: str = "ball_joint") -> list[int]:
    del variant
    if len(pose) != len(L10_JOINTS):
        raise ValueError("L10 pose must contain 10 values")
    return [clamp_joint_value(joint, value) for joint, value in zip(L10_JOINTS, pose, strict=True)]


def open_palm_pose(variant: str = "ball_joint") -> list[int]:
    del variant
    return list(OPEN_PALM_POSE)


def build_pose(
    overrides: dict[str, int],
    base_pose: list[int] | None = None,
    variant: str = "ball_joint",
) -> list[int]:
    del variant
    pose = list(base_pose or OPEN_PALM_POSE)
    if len(pose) != len(L10_JOINTS):
        raise ValueError("L10 base pose must contain 10 values")

    index_by_name = {name: index for index, name in enumerate(L10_JOINTS)}
    for joint, value in overrides.items():
        if joint not in index_by_name:
            raise ValueError(f"Unknown L10 joint: {joint}")
        pose[index_by_name[joint]] = clamp_joint_value(joint, value)

    return pose


def parse_joint_assignments(assignments: list[str]) -> dict[str, int]:
    parsed: dict[str, int] = {}
    for assignment in assignments:
        if "=" not in assignment:
            raise ValueError(f"Expected joint=value assignment: {assignment}")
        joint, raw_value = assignment.split("=", 1)
        parsed[joint.strip()] = int(raw_value.strip())
    return parsed
