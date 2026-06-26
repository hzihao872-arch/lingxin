from l10_hand_control.hand_tracking import (
    PoseSmoother,
    fist_landmarks,
    forward_thumb_landmarks,
    landmarks_to_pose,
    open_palm_landmarks,
    palm_facing_partial_curl_landmarks,
)
from l10_hand_control.l10_pose import L10_JOINTS


def test_landmarks_to_pose_returns_ten_values():
    pose = landmarks_to_pose(open_palm_landmarks())
    assert len(pose) == len(L10_JOINTS)
    assert all(0 <= value <= 255 for value in pose)


def test_teleop_open_palm_pose_uses_calibrated_thumb():
    from l10_hand_control.hand_tracking import teleop_open_palm_pose

    pose = teleop_open_palm_pose()
    assert pose[L10_JOINTS.index("thumb_swing")] == 255
    assert pose[L10_JOINTS.index("thumb_rotation")] == 55


def test_open_palm_thumb_matches_safe_open_pose():
    pose = landmarks_to_pose(open_palm_landmarks())
    thumb_root_index = L10_JOINTS.index("thumb_root")
    thumb_swing_index = L10_JOINTS.index("thumb_swing")
    thumb_rotation_index = L10_JOINTS.index("thumb_rotation")

    assert pose[thumb_swing_index] >= 250
    assert 50 <= pose[thumb_rotation_index] <= 60
    assert pose[thumb_root_index] >= 250


def test_forward_thumb_lowers_swing_from_open_pose():
    open_pose = landmarks_to_pose(open_palm_landmarks())
    forward_pose = landmarks_to_pose(forward_thumb_landmarks())
    swing_index = L10_JOINTS.index("thumb_swing")

    assert open_pose[swing_index] >= 250
    assert forward_pose[swing_index] <= open_pose[swing_index] - 80


def test_palm_facing_partial_curl_lowers_finger_roots():
    open_pose = landmarks_to_pose(open_palm_landmarks())
    curled_pose = landmarks_to_pose(palm_facing_partial_curl_landmarks())
    fist_pose = landmarks_to_pose(fist_landmarks())

    for finger in ("index_root", "middle_root", "ring_root", "pinky_root"):
        finger_index = L10_JOINTS.index(finger)
        assert curled_pose[finger_index] < open_pose[finger_index] - 20
        assert fist_pose[finger_index] < open_pose[finger_index]


def test_partial_thumb_bend_changes_root_before_fist():
    from l10_hand_control.hand_tracking import THUMB_IP, THUMB_TIP

    open_pose = landmarks_to_pose(open_palm_landmarks())
    bent_landmarks = list(open_palm_landmarks())
    bent_landmarks[THUMB_TIP] = (0.40, 0.54, 0.01)
    bent_landmarks[THUMB_IP] = (0.38, 0.58, 0.00)
    bent_pose = landmarks_to_pose(bent_landmarks)
    fist_pose = landmarks_to_pose(fist_landmarks())
    root_index = L10_JOINTS.index("thumb_root")

    assert bent_pose[root_index] < open_pose[root_index]
    assert fist_pose[root_index] < bent_pose[root_index]


def test_open_palm_pose_is_more_open_than_fist():
    open_pose = landmarks_to_pose(open_palm_landmarks())
    fist_pose = landmarks_to_pose(fist_landmarks())

    for finger in ("index_root", "middle_root", "ring_root", "pinky_root"):
        finger_index = L10_JOINTS.index(finger)
        assert open_pose[finger_index] > fist_pose[finger_index]


def test_noisy_extended_fingers_stay_open():
    import random

    random.seed(1)
    landmarks = list(open_palm_landmarks())
    for index in range(21):
        x, y, z = landmarks[index]
        landmarks[index] = (x, y, z + random.uniform(-0.02, 0.03))

    pose = landmarks_to_pose(landmarks)
    for finger in ("index_root", "middle_root", "ring_root", "pinky_root"):
        assert pose[L10_JOINTS.index(finger)] >= 250


def test_pose_smoother_holds_open_fingers_steady():
    smoother = PoseSmoother(alpha=0.35, finger_alpha=0.10)
    open_pose = [255, 255, 255, 255, 255, 255, 120, 120, 120, 55]
    noisy_pose = [255, 255, 230, 240, 235, 228, 120, 120, 120, 55]
    smoother.update(open_pose)
    stabilized = smoother.update(noisy_pose)
    for finger in ("index_root", "middle_root", "ring_root", "pinky_root"):
        assert stabilized[L10_JOINTS.index(finger)] >= 250


def test_pose_smoother_blends_values():
    smoother = PoseSmoother(alpha=0.5)
    first = smoother.update([0] * 10)
    second = smoother.update([100] * 10)
    assert first == [0] * 10
    assert second == [50] * 10


def test_pose_smoother_reset_clears_state():
    smoother = PoseSmoother(alpha=0.5)
    smoother.update([10] * 10)
    smoother.reset()
    assert smoother.update([20] * 10) == [20] * 10


def test_pose_smoother_delta_limit_caps_per_joint_change():
    smoother = PoseSmoother(alpha=1.0, max_joint_delta=5.0, close_ratio=1.0)
    # alpha=1.0 means EMA fully follows the new pose, but the delta cap should
    # prevent any joint from jumping more than 5 in one frame.
    smoother.update([0] * 10)
    out = smoother.update([100] * 10)
    for value in out:
        assert value <= 5


def test_pose_smoother_close_ratio_slows_closing_more_than_opening():
    # Opening: value increases. Closing: value decreases.
    open_smoother = PoseSmoother(alpha=1.0, max_joint_delta=10.0, close_ratio=0.5)
    open_smoother.update([100] * 10)
    opened = open_smoother.update([200] * 10)
    # Opening direction cap = 10 -> can move +10.
    assert opened[0] == 110

    close_smoother = PoseSmoother(alpha=1.0, max_joint_delta=10.0, close_ratio=0.5)
    close_smoother.update([200] * 10)
    closed = close_smoother.update([100] * 10)
    # Closing direction cap = 10 * 0.5 = 5 -> can only move -5.
    assert closed[0] == 195


def test_thumb_pinch_amount_is_zero_on_open_hand():
    from l10_hand_control.hand_tracking import _thumb_pinch_amount

    assert _thumb_pinch_amount(open_palm_landmarks()) == 0.0


def test_thumb_pinch_amount_grows_when_thumb_sweeps_forward():
    from l10_hand_control.hand_tracking import _thumb_pinch_amount

    open_amt = _thumb_pinch_amount(open_palm_landmarks())
    forward_amt = _thumb_pinch_amount(forward_thumb_landmarks())
    assert forward_amt > open_amt
    assert 0.0 < forward_amt <= 1.0


def test_thumb_swing_reaches_pinch_target_on_full_pinch():
    # A fully pinched thumb (tip touching index root area) should pull thumb_swing
    # down toward THUMB_SWING_PINCH, not stay near the open value.
    from l10_hand_control.hand_tracking import (
        THUMB_SWING_PINCH,
        THUMB_TIP,
        THUMB_IP,
        THUMB_MCP,
        THUMB_CMC,
    )

    pinch = list(open_palm_landmarks())
    # Pinch the thumb tip toward the index finger root.
    pinch[THUMB_CMC] = (0.45, 0.70, 0.0)
    pinch[THUMB_MCP] = (0.45, 0.62, 0.0)
    pinch[THUMB_IP] = (0.46, 0.58, 0.0)
    pinch[THUMB_TIP] = (0.47, 0.55, 0.0)
    pose = landmarks_to_pose(pinch)
    swing_index = L10_JOINTS.index("thumb_swing")
    assert pose[swing_index] <= THUMB_SWING_PINCH + 5


def test_spread_to_swing_amplifies_with_sensitivity():
    from l10_hand_control.hand_tracking import _spread_to_swing

    # A mid spread (0.35 rad, halfway between closed 0.15 and open 0.55) maps to
    # the midpoint of [120,255] at sensitivity 1.0. Sensitivity>1 should push it
    # further from the midpoint (toward open here, since 0.35 > mid 0.35... use a
    # spread above mid to see the open-direction amplification).
    base = _spread_to_swing(0.45, sensitivity=1.0)
    amplified = _spread_to_swing(0.45, sensitivity=1.5)
    assert amplified > base  # amplification opens the swing more, not clamps to 255


def test_move_pose_smoothed_interpolates_in_steps():
    from l10_hand_control.l10_pose import move_pose_smoothed

    class FakeController:
        def __init__(self):
            self.calls = []

        def move_pose(self, pose):
            self.calls.append(list(pose))

    fake = FakeController()
    src = [0] * 10
    dst = [100] * 10
    final = move_pose_smoothed(fake, dst, src=src, steps=5, hz=1000.0)
    assert final == [100] * 10
    # 5 steps -> 5 move_pose calls, each strictly increasing toward dst.
    assert len(fake.calls) == 5
    assert fake.calls[0][0] < fake.calls[-1][0]
    assert fake.calls[-1] == [100] * 10


def test_move_pose_smoothed_clamps_out_of_range_dst():
    from l10_hand_control.l10_pose import move_pose_smoothed

    class FakeController:
        def __init__(self):
            self.calls = []

        def move_pose(self, pose):
            self.calls.append(list(pose))

    fake = FakeController()
    final = move_pose_smoothed(fake, [300] * 10, src=[0] * 10, steps=2, hz=1000.0)
    assert all(v == 255 for v in final)
    assert all(v <= 255 for v in fake.calls[-1])
