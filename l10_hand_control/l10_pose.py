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


def smoothstep(t: float) -> float:
    """Cubic ease-in-out: slow start, fast middle, slow end. Maps [0,1] to [0,1]."""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def interpolate_pose(src: list[int], dst: list[int], t: float, ease=smoothstep) -> list[int]:
    """Per-joint eased interpolation between two 10-value poses."""
    if len(src) != len(L10_JOINTS) or len(dst) != len(L10_JOINTS):
        raise ValueError("poses must contain 10 values")
    e = ease(t)
    return [int(round(s + (d - s) * e)) for s, d in zip(src, dst, strict=True)]


def move_pose_smoothed(
    controller,
    dst: list[int],
    src: list[int] | None = None,
    steps: int = 12,
    hz: float = 50.0,
    ease=smoothstep,
) -> list[int]:
    """Move the hand from src to dst over `steps` frames at `hz`, easing each joint.

    ponytail: naive linear+ease interpolation per joint, no velocity profiling.
    Upgrade path: SDK-native interpolation or trapezoidal velocity profile per joint.
    Returns the final pose actually sent (clamped, 10 values).

    `controller` must expose `move_pose(pose)`. If `src` is None, the current
    smoother state or an open palm is used as the start; callers should pass an
    explicit src when known (e.g. the last sent pose) for a smooth transition.
    """
    if steps < 1:
        steps = 1
    start = list(src) if src is not None else list(OPEN_PALM_POSE)
    if len(start) != len(L10_JOINTS):
        raise ValueError("src pose must contain 10 values")
    end = clamp_pose(dst)
    interval = 1.0 / max(hz, 1.0)
    import time

    for i in range(1, steps + 1):
        pose = interpolate_pose(start, end, i / steps, ease=ease)
        try:
            controller.move_pose(pose)
        except Exception as exc:  # pragma: no cover - hardware I/O
            print(f"WARNING: move_pose failed during smooth move: {exc}", flush=True)
            break
        if i < steps:
            time.sleep(interval)
    return end
