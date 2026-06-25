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
