"""Map camera hand landmarks (e.g. MediaPipe) to L10 joint poses."""

from __future__ import annotations

import math
from typing import Sequence

from l10_hand_control.l10_pose import L10_JOINTS, OPEN_PALM_POSE, build_pose, smoothstep

# MediaPipe hand landmark indices.
WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20

Landmark = tuple[float, float, float]
Landmarks = Sequence[Landmark]

# User-calibrated open palm thumb pose on this L10:
# thumb_swing=255, thumb_rotation=55.
THUMB_TELEOP_REST = {
    "thumb_root": 255,
    "thumb_swing": 255,
    "thumb_rotation": 55,
}

THUMB_SWING_FORWARD = 55
THUMB_SWING_PINCH = 35
THUMB_ROTATION_FORWARD = 82
THUMB_ROTATION_PINCH = 105

# Thumb-index opposition angle (rad) at open vs pinch poses, used to gate the
# pinch blend for thumb_swing / thumb_rotation. opposition is large when the
# thumb is splayed out, small when the thumb touches the index (pinch).
# NOTE: _thumb_opposition_angle measures the wrist->thumb_mcp vs wrist->index_mcp
# spread, which is a small angle (~0.34 rad open) because the MCP joints sit close
# together on the palm. These bounds are tuned to that metric, not fingertip span.
THUMB_OPPOSITION_OPEN = 0.34
THUMB_OPPOSITION_PINCH = 0.10

_THUMB_ROOT_INDEX = L10_JOINTS.index("thumb_root")
_THUMB_SWING_INDEX = L10_JOINTS.index("thumb_swing")
_THUMB_ROTATION_INDEX = L10_JOINTS.index("thumb_rotation")
_FINGER_ROOT_INDICES = frozenset(
    L10_JOINTS.index(name)
    for name in ("index_root", "middle_root", "ring_root", "pinky_root")
)

# Curl below this is treated as a straight finger (filters MediaPipe jitter).
FINGER_CURL_DEADBAND = 0.22


def _apply_calibrated_thumb(
    pose: list[int],
    thumb_root: int,
    thumb_swing: int,
    thumb_rotation: int,
) -> list[int]:
    """Apply thumb values without ball-joint firmware clamping (swing may exceed 70)."""
    calibrated = list(pose)
    calibrated[_THUMB_ROOT_INDEX] = thumb_root
    calibrated[_THUMB_SWING_INDEX] = thumb_swing
    calibrated[_THUMB_ROTATION_INDEX] = thumb_rotation
    return calibrated


def teleop_open_palm_pose() -> list[int]:
    """Open-palm pose using hardware-calibrated thumb joints."""
    return _apply_calibrated_thumb(
        build_pose({}),
        THUMB_TELEOP_REST["thumb_root"],
        THUMB_TELEOP_REST["thumb_swing"],
        THUMB_TELEOP_REST["thumb_rotation"],
    )


def _vec(a: Landmark, b: Landmark) -> tuple[float, float, float]:
    return (b[0] - a[0], b[1] - a[1], b[2] - a[2])


def _length(v: tuple[float, float, float]) -> float:
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _angle(a: Landmark, b: Landmark, c: Landmark) -> float:
    """Return the angle at point b in radians."""
    ba = _vec(b, a)
    bc = _vec(b, c)
    mag_ba = _length(ba)
    mag_bc = _length(bc)
    if mag_ba * mag_bc < 1e-9:
        return math.pi
    cos_angle = max(-1.0, min(1.0, (ba[0] * bc[0] + ba[1] * bc[1] + ba[2] * bc[2]) / (mag_ba * mag_bc)))
    return math.acos(cos_angle)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _lerp(low: float, high: float, t: float) -> float:
    return low + (high - low) * _clamp(t, 0.0, 1.0)


def _curl_from_angles(mcp: Landmark, pip: Landmark, dip: Landmark, tip: Landmark) -> float:
    """Return 0 for straight finger, 1 for fully curled."""
    pip_angle = _angle(mcp, pip, dip)
    dip_angle = _angle(pip, dip, tip)
    avg_angle = (pip_angle + dip_angle) / 2.0
    open_angle = 2.8
    closed_angle = 1.3
    return _clamp((open_angle - avg_angle) / (open_angle - closed_angle), 0.0, 1.0)


def _curl_from_distance(mcp: Landmark, pip: Landmark, dip: Landmark, tip: Landmark) -> float:
    """Distance-based curl works better for webcam views than angles alone."""
    straight_len = (
        _length(_vec(mcp, pip))
        + _length(_vec(pip, dip))
        + _length(_vec(dip, tip))
    )
    actual_len = _length(_vec(mcp, tip))
    if straight_len < 1e-6:
        return 0.0
    ratio = actual_len / straight_len
    return _clamp(1.0 - (ratio - 0.35) / (0.95 - 0.35), 0.0, 1.0)


def _xy_length(a: Landmark, b: Landmark) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _curl_from_xy_distance(mcp: Landmark, pip: Landmark, dip: Landmark, tip: Landmark) -> float:
    """Image-plane finger shortening; reliable when the palm faces the camera."""
    straight_len = (
        _xy_length(mcp, pip)
        + _xy_length(pip, dip)
        + _xy_length(dip, tip)
    )
    actual_len = _xy_length(mcp, tip)
    if straight_len < 1e-6:
        return 0.0
    ratio = actual_len / straight_len
    return _clamp(1.0 - (ratio - 0.35) / (0.95 - 0.35), 0.0, 1.0)


def _curl_from_depth_chain(mcp: Landmark, pip: Landmark, dip: Landmark, tip: Landmark) -> float:
    """Depth variation along the finger chain when flexing toward/away from the camera."""
    xy_span = _xy_length(mcp, tip)
    if xy_span < 0.02:
        return 0.0

    dz_pip = pip[2] - mcp[2]
    dz_dip = dip[2] - pip[2]
    dz_tip = tip[2] - dip[2]
    same_sign = (
        (dz_pip <= 0.0 and dz_dip <= 0.0 and dz_tip <= 0.0)
        or (dz_pip >= 0.0 and dz_dip >= 0.0 and dz_tip >= 0.0)
    )
    if not same_sign:
        return 0.0

    z_bend = abs(dz_pip) + abs(dz_dip) + abs(dz_tip)
    return _clamp(z_bend / (xy_span * 0.55), 0.0, 1.0)


def _palm_facing_camera_amount(landmarks: Landmarks) -> float:
    """Return ~1 when the palm normal points toward the camera."""
    wrist = landmarks[WRIST]
    v1 = _vec(wrist, landmarks[INDEX_MCP])
    v2 = _vec(wrist, landmarks[PINKY_MCP])
    normal = (
        v1[1] * v2[2] - v1[2] * v2[1],
        v1[2] * v2[0] - v1[0] * v2[2],
        v1[0] * v2[1] - v1[1] * v2[0],
    )
    mag = _length(normal)
    if mag < 1e-9:
        return 0.0
    return _clamp(abs(normal[2]) / mag, 0.0, 1.0)


def _finger_extension_amount(
    mcp: Landmark,
    pip: Landmark,
    dip: Landmark,
    tip: Landmark,
) -> float:
    """1 when the finger looks straight in the primary 3-D metrics."""
    angle_open = 1.0 - _curl_from_angles(mcp, pip, dip, tip)
    distance_open = 1.0 - _curl_from_distance(mcp, pip, dip, tip)
    return _clamp((angle_open + distance_open) / 2.0, 0.0, 1.0)


def _gated_view_curl(xy_curl: float, depth_curl: float, *, palm_facing: float) -> float:
    """Suppress MediaPipe depth/XY noise, especially when the palm faces the camera."""
    xy_noise = 0.12
    depth_noise = 0.25
    gated_xy = 0.0
    gated_depth = 0.0
    if xy_curl > xy_noise:
        gated_xy = _clamp((xy_curl - xy_noise) / (1.0 - xy_noise), 0.0, 1.0)
    if depth_curl > depth_noise:
        gated_depth = _clamp((depth_curl - depth_noise) / (1.0 - depth_noise), 0.0, 1.0)
    view = max(gated_xy, gated_depth)
    if palm_facing < 0.35:
        return view * 0.35
    return view


def _finger_curl(
    mcp: Landmark,
    pip: Landmark,
    dip: Landmark,
    tip: Landmark,
    *,
    palm_facing: float = 0.0,
) -> float:
    angle_curl = _curl_from_angles(mcp, pip, dip, tip)
    distance_curl = _curl_from_distance(mcp, pip, dip, tip)
    xy_curl = _curl_from_xy_distance(mcp, pip, dip, tip)
    depth_curl = _curl_from_depth_chain(mcp, pip, dip, tip)
    view_curl = _gated_view_curl(xy_curl, depth_curl, palm_facing=palm_facing)

    if palm_facing >= 0.5:
        xy_open = 1.0 - xy_curl
        if xy_open > 0.68 and xy_curl < 0.12:
            return view_curl if view_curl >= 0.18 else 0.0
        return max(angle_curl, xy_curl, view_curl)

    core_curl = max(angle_curl, distance_curl)
    extension = _finger_extension_amount(mcp, pip, dip, tip)
    if extension > 0.55 and core_curl < 0.12 and view_curl < 0.25:
        return core_curl
    return max(core_curl, view_curl * 0.35)


def _curl_to_joint(curl: float, sensitivity: float = 1.0, ease: bool = True) -> int:
    # Static finger curl map stays linear in the deadband-normalized curl so
    # partial grips keep their resolution. The "soft" feel comes from the
    # per-joint velocity/acceleration limits in PoseSmoother (time-domain),
    # not from reshaping this input/output curve. `ease` is accepted for
    # API symmetry with the thumb path but does not reshape finger roots.
    del ease
    if curl <= FINGER_CURL_DEADBAND:
        return 255
    normalized = _clamp((curl - FINGER_CURL_DEADBAND) / (1.0 - FINGER_CURL_DEADBAND), 0.0, 1.0)
    scaled = _clamp((normalized ** 0.9) * min(sensitivity, 1.1), 0.0, 1.0)
    value = int(round(_lerp(255.0, 0.0, scaled)))
    if value >= 245:
        return 255
    return value


def _spread_angle(wrist: Landmark, mcp_a: Landmark, mcp_b: Landmark) -> float:
    va = _vec(wrist, mcp_a)
    vb = _vec(wrist, mcp_b)
    mag_a = _length(va)
    mag_b = _length(vb)
    if mag_a * mag_b < 1e-9:
        return 0.0
    cos_angle = max(-1.0, min(1.0, (va[0] * vb[0] + va[1] * vb[1] + va[2] * vb[2]) / (mag_a * mag_b)))
    return math.acos(cos_angle)


def _spread_to_swing(
    spread_rad: float,
    closed_rad: float = 0.15,
    open_rad: float = 0.55,
    sensitivity: float = 1.0,
) -> int:
    t = _clamp((spread_rad - closed_rad) / (open_rad - closed_rad), 0.0, 1.0)
    # Amplify deviation from the neutral (mid) spread, not deviation from 255.
    # sensitivity>1 makes the swing travel further from the mid point on both sides.
    if sensitivity != 1.0:
        mid = 0.5
        t = _clamp(mid + (t - mid) * sensitivity, 0.0, 1.0)
    return int(round(_lerp(120.0, 255.0, t)))


def _thumb_opposition_angle(landmarks: Landmarks) -> float:
    """Angle between index and thumb directions from the wrist (radians)."""
    wrist = landmarks[WRIST]
    return _spread_angle(wrist, landmarks[INDEX_MCP], landmarks[THUMB_MCP])


def _open_palm_amount(landmarks: Landmarks) -> float:
    """Return 1 when the four fingers are extended, 0 when curled into a fist."""
    finger_curls = [
        _finger_curl(
            landmarks[mcp],
            landmarks[pip],
            landmarks[dip],
            landmarks[tip],
        )
        for mcp, pip, dip, tip in (
            (INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP),
            (MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP),
            (RING_MCP, RING_PIP, RING_DIP, RING_TIP),
            (PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP),
        )
    ]
    return _clamp(1.0 - max(finger_curls), 0.0, 1.0)


def _blend_toward_open(value: int, open_target: int, open_amount: float, strength: float) -> int:
    if open_amount <= 0.0 or strength <= 0.0:
        return value
    weight = _clamp(open_amount * strength, 0.0, 1.0)
    return int(round(_lerp(float(value), float(open_target), weight)))


def _thumb_bend_amount(landmarks: Landmarks) -> float:
    """Thumb flexion tuned for partial bends, not only a full fist."""
    cmc = landmarks[THUMB_CMC]
    mcp = landmarks[THUMB_MCP]
    ip = landmarks[THUMB_IP]
    tip = landmarks[THUMB_TIP]

    mcp_angle = _angle(cmc, mcp, ip)
    ip_angle = _angle(mcp, ip, tip)
    cmc_angle = _angle(landmarks[WRIST], cmc, mcp)
    angle_curl = _clamp((2.85 - (mcp_angle + ip_angle) / 2.0) / (2.85 - 1.0), 0.0, 1.0)
    cmc_curl = _clamp((2.05 - cmc_angle) / (2.05 - 1.15), 0.0, 1.0)
    distance_curl = _finger_curl(cmc, mcp, ip, tip)
    return max(angle_curl, cmc_curl, distance_curl)


def _thumb_forward_sweep_amount(landmarks: Landmarks) -> float:
    """0 at calibrated open-aside pose, 1 when the thumb sweeps toward the fingers."""
    wrist = landmarks[WRIST]
    spread = _spread_angle(wrist, landmarks[MIDDLE_MCP], landmarks[THUMB_TIP])
    spread_sweep = _clamp((0.40 - spread) / (0.40 - 0.04), 0.0, 1.0)

    opposition_sweep = 0.0
    if spread < 0.34:
        opposition = _thumb_opposition_angle(landmarks)
        opposition_sweep = _clamp((0.36 - opposition) / (0.36 - 0.12), 0.0, 1.0)

    return _clamp(max(spread_sweep, opposition_sweep * 0.85) * 1.1, 0.0, 1.0)


def _thumb_root_value(landmarks: Landmarks, sensitivity: float, ease: bool = True) -> int:
    curl = _thumb_bend_amount(landmarks)
    # Amplify small bends so thumb_root moves before a full fist.
    scaled = _clamp((curl ** 0.65) * sensitivity * 2.2, 0.0, 1.0)
    if ease:
        # Ease the thumb flex so it starts gently (thumb opposes before it
        # folds), then accelerates -- matches the human thumb's opposition-then-
        # flexion sequence without fully suppressing an independent thumb bend.
        scaled = smoothstep(scaled)
    return int(round(_lerp(255.0, 0.0, scaled)))


def _thumb_pinch_amount(landmarks: Landmarks) -> float:
    """1 when the thumb is pinched against the index, 0 at the open pose.

    opposition angle is large (splayed) when open, small when pinching, so the
    pinch amount grows as opposition shrinks from THUMB_OPPOSITION_OPEN toward
    THUMB_OPPOSITION_PINCH.
    """
    opposition = _thumb_opposition_angle(landmarks)
    return _clamp(
        (THUMB_OPPOSITION_OPEN - opposition)
        / (THUMB_OPPOSITION_OPEN - THUMB_OPPOSITION_PINCH),
        0.0,
        1.0,
    )


def _thumb_swing_value(landmarks: Landmarks, hand_type: str = "left") -> int:
    """thumb_swing=255 is the calibrated open pose; forward thumb sweep lowers it."""
    del hand_type  # reserved for left/right asymmetry
    forward_sweep = _thumb_forward_sweep_amount(landmarks)
    pinch = _thumb_pinch_amount(landmarks)

    swing = int(round(_lerp(float(THUMB_TELEOP_REST["thumb_swing"]), float(THUMB_SWING_FORWARD), forward_sweep)))
    if pinch > 0.0:
        swing = int(round(_lerp(float(swing), float(THUMB_SWING_PINCH), pinch)))
    return swing


def _thumb_rotation_value(landmarks: Landmarks) -> int:
    forward_sweep = _thumb_forward_sweep_amount(landmarks)
    pinch = _thumb_pinch_amount(landmarks)

    rotation = int(
        round(
            _lerp(
                float(THUMB_TELEOP_REST["thumb_rotation"]),
                float(THUMB_ROTATION_FORWARD),
                forward_sweep,
            )
        )
    )
    if pinch > 0.0:
        rotation = int(round(_lerp(float(rotation), float(THUMB_ROTATION_PINCH), pinch)))
    return rotation


def landmarks_to_pose(
    landmarks: Landmarks,
    sensitivity: float = 1.2,
    hand_type: str = "left",
    ease: bool = True,
) -> list[int]:
    """Convert 21 hand landmarks to a 10-value L10 pose."""
    if len(landmarks) != 21:
        raise ValueError(f"Expected 21 landmarks, got {len(landmarks)}")
    if sensitivity <= 0:
        raise ValueError("sensitivity must be > 0")

    thumb_root = _thumb_root_value(landmarks, sensitivity, ease=ease)
    thumb_swing = _thumb_swing_value(landmarks, hand_type=hand_type)
    thumb_rotation = _thumb_rotation_value(landmarks)
    palm_facing = _palm_facing_camera_amount(landmarks)

    def finger_root(mcp: int, pip: int, dip: int, tip: int) -> int:
        return _curl_to_joint(
            _finger_curl(
                landmarks[mcp],
                landmarks[pip],
                landmarks[dip],
                landmarks[tip],
                palm_facing=palm_facing,
            ),
            sensitivity,
            ease=ease,
        )

    overrides = {
        "thumb_root": thumb_root,
        "thumb_swing": thumb_swing,
        "index_root": finger_root(INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP),
        "middle_root": finger_root(MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP),
        "ring_root": finger_root(RING_MCP, RING_PIP, RING_DIP, RING_TIP),
        "pinky_root": finger_root(PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP),
        "index_swing": _spread_to_swing(
            _spread_angle(landmarks[WRIST], landmarks[INDEX_MCP], landmarks[MIDDLE_MCP]),
            sensitivity=sensitivity,
        ),
        "ring_swing": _spread_to_swing(
            _spread_angle(landmarks[WRIST], landmarks[MIDDLE_MCP], landmarks[RING_MCP]),
            sensitivity=sensitivity,
        ),
        "pinky_swing": _spread_to_swing(
            _spread_angle(landmarks[WRIST], landmarks[RING_MCP], landmarks[PINKY_MCP]),
            sensitivity=sensitivity,
        ),
        "thumb_rotation": thumb_rotation,
    }
    pose = build_pose(overrides)
    return _apply_calibrated_thumb(pose, thumb_root, thumb_swing, thumb_rotation)


class PoseSmoother:
    """Exponential moving average over L10 pose vectors."""

    # Thumb joints benefit from faster tracking than the four fingers.
    _THUMB_INDICES = frozenset({_THUMB_ROOT_INDEX, _THUMB_SWING_INDEX, _THUMB_ROTATION_INDEX})
    _FINGER_OPEN_SNAP = 240
    _FINGER_OPEN_HOLD = 200
    _FINGER_MICRO_DEADBAND = 8

    def __init__(
        self,
        alpha: float = 0.35,
        thumb_alpha: float | None = None,
        finger_alpha: float | None = None,
        max_joint_delta: float = 0.0,
        close_ratio: float = 1.0,
    ):
        if alpha <= 0.0 or alpha > 1.0:
            raise ValueError("alpha must be in (0, 1]")
        if max_joint_delta < 0.0:
            raise ValueError("max_joint_delta must be >= 0")
        if not 0.0 < close_ratio <= 1.0:
            raise ValueError("close_ratio must be in (0, 1]")
        self.alpha = alpha
        self.thumb_alpha = alpha if thumb_alpha is None else min(1.0, thumb_alpha)
        self.finger_alpha = alpha if finger_alpha is None else min(1.0, finger_alpha)
        # Per-frame per-joint velocity cap (in joint-value units). 0 = disabled.
        # The closing direction (value decreasing) is scaled by close_ratio so a
        # grip closes slower than it opens, matching human hand pacing.
        self.max_joint_delta = max_joint_delta
        self.close_ratio = close_ratio
        self._state: list[int] | None = None

    def reset(self) -> None:
        self._state = None

    def _stabilize_finger_root(self, previous: int, current: int) -> int:
        if previous >= self._FINGER_OPEN_SNAP and current >= self._FINGER_OPEN_HOLD:
            return 255
        if abs(current - previous) < self._FINGER_MICRO_DEADBAND:
            return previous
        return current

    def _limit_delta(self, previous: int, blended: int) -> int:
        if self.max_joint_delta <= 0.0:
            return blended
        delta = blended - previous
        # Closing = value decreasing (L10: smaller = more curled/closed).
        if delta < 0:
            limit = self.max_joint_delta * self.close_ratio
        else:
            limit = self.max_joint_delta
        if abs(delta) > limit:
            delta = int(round(math.copysign(limit, delta)))
        return int(_clamp(previous + delta, 0.0, 255.0))

    def update(self, pose: list[int]) -> list[int]:
        if len(pose) != len(L10_JOINTS):
            raise ValueError("L10 pose must contain 10 values")
        if self._state is None:
            self._state = list(pose)
            return list(self._state)

        blended = []
        for index, (previous, current) in enumerate(zip(self._state, pose, strict=True)):
            if index in _FINGER_ROOT_INDICES:
                current = self._stabilize_finger_root(previous, current)
                joint_alpha = self.finger_alpha
            elif index in self._THUMB_INDICES:
                joint_alpha = self.thumb_alpha
            else:
                joint_alpha = self.alpha
            keep = 1.0 - joint_alpha
            value = int(round(joint_alpha * current + keep * previous))
            value = self._limit_delta(previous, value)
            blended.append(value)
        self._state = blended
        return list(self._state)


def palm_facing_partial_curl_landmarks() -> list[Landmark]:
    """Synthetic palm-facing camera with fingers flexing toward the lens."""
    landmarks = list(open_palm_landmarks())
    for mcp, pip, dip, tip in (
        (INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP),
        (MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP),
        (RING_MCP, RING_PIP, RING_DIP, RING_TIP),
        (PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP),
    ):
        mx, my, mz = landmarks[mcp]
        landmarks[pip] = (mx, my + (landmarks[pip][1] - my) * 0.92, mz - 0.018)
        landmarks[dip] = (mx, my + (landmarks[dip][1] - my) * 0.84, mz - 0.040)
        landmarks[tip] = (mx, my + (landmarks[tip][1] - my) * 0.78, mz - 0.065)
    return landmarks


def forward_thumb_landmarks() -> list[Landmark]:
    """Synthetic thumb swept forward while the other fingers stay open."""
    landmarks = list(open_palm_landmarks())
    landmarks[THUMB_TIP] = (0.48, 0.42, 0.01)
    landmarks[THUMB_IP] = (0.44, 0.52, 0.00)
    landmarks[THUMB_MCP] = (0.42, 0.60, -0.01)
    landmarks[THUMB_CMC] = (0.44, 0.68, -0.01)
    return landmarks


def open_palm_landmarks() -> list[Landmark]:
    """Synthetic straight-hand landmarks for tests and dry-run demos."""
    return [
        (0.50, 0.80, 0.00),  # wrist
        (0.42, 0.72, -0.01),
        (0.40, 0.64, -0.01),
        (0.38, 0.56, -0.01),
        (0.36, 0.48, -0.01),  # thumb
        (0.46, 0.62, 0.00),
        (0.46, 0.50, 0.00),
        (0.46, 0.40, 0.00),
        (0.46, 0.30, 0.00),  # index
        (0.50, 0.62, 0.00),
        (0.50, 0.50, 0.00),
        (0.50, 0.40, 0.00),
        (0.50, 0.30, 0.00),  # middle
        (0.54, 0.62, 0.00),
        (0.54, 0.50, 0.00),
        (0.54, 0.40, 0.00),
        (0.54, 0.30, 0.00),  # ring
        (0.58, 0.64, 0.00),
        (0.59, 0.52, 0.00),
        (0.60, 0.42, 0.00),
        (0.61, 0.32, 0.00),  # pinky
    ]


def fist_landmarks() -> list[Landmark]:
    """Synthetic closed-fist landmarks for tests."""
    palm_center = (0.50, 0.58, 0.00)
    curled = list(open_palm_landmarks())
    for tip in (THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP):
        x, y, z = curled[tip]
        curled[tip] = (
            palm_center[0] + (x - palm_center[0]) * 0.18,
            palm_center[1] + (y - palm_center[1]) * 0.18,
            z + 0.03,
        )
    for pip in (INDEX_PIP, MIDDLE_PIP, RING_PIP, PINKY_PIP):
        x, y, z = curled[pip]
        curled[pip] = (
            palm_center[0] + (x - palm_center[0]) * 0.48,
            palm_center[1] + (y - palm_center[1]) * 0.48,
            z + 0.01,
        )
    for dip in (INDEX_DIP, MIDDLE_DIP, RING_DIP, PINKY_DIP):
        x, y, z = curled[dip]
        curled[dip] = (
            palm_center[0] + (x - palm_center[0]) * 0.32,
            palm_center[1] + (y - palm_center[1]) * 0.32,
            z + 0.02,
        )
    return curled
