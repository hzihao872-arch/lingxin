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

# Official open-palm example for L10, used as a safe base for experiments.
OPEN_PALM_POSE = [255, 70, 255, 255, 255, 255, 255, 255, 255, 255]


def build_pose(overrides: dict[str, int], base_pose: list[int] | None = None) -> list[int]:
    pose = list(base_pose or OPEN_PALM_POSE)
    if len(pose) != len(L10_JOINTS):
        raise ValueError("L10 base pose must contain 10 values")

    index_by_name = {name: index for index, name in enumerate(L10_JOINTS)}
    for joint, value in overrides.items():
        if joint not in index_by_name:
            raise ValueError(f"Unknown L10 joint: {joint}")
        if value < 0 or value > 255:
            raise ValueError(f"L10 joint value must be 0..255: {joint}={value}")
        pose[index_by_name[joint]] = value

    return pose


def parse_joint_assignments(assignments: list[str]) -> dict[str, int]:
    parsed: dict[str, int] = {}
    for assignment in assignments:
        if "=" not in assignment:
            raise ValueError(f"Expected joint=value assignment: {assignment}")
        joint, raw_value = assignment.split("=", 1)
        parsed[joint.strip()] = int(raw_value.strip())
    return parsed
