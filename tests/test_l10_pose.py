from l10_hand_control.l10_pose import (
    L10_JOINTS,
    OPEN_PALM_POSE,
    build_pose,
    clamp_pose,
    get_joint_limits,
    open_palm_pose,
)


def test_l10_joint_order_matches_official_readme():
    assert L10_JOINTS == [
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


def test_build_pose_starts_from_safe_open_palm_pose():
    assert build_pose({}) == OPEN_PALM_POSE


def test_build_pose_overrides_named_joints():
    pose = build_pose({"index_root": 0, "thumb_rotation": 30})

    assert pose == [255, 70, 0, 255, 255, 255, 255, 255, 255, 30]


def test_build_pose_allows_thumb_swing_above_open_palm_value():
    pose = build_pose({"thumb_swing": 200})
    assert pose[1] == 200


def test_clamp_pose_only_enforces_protocol_range():
    pose = clamp_pose([255, 300, -5, 255, 255, 255, 255, 255, 255, 255])
    assert pose == [255, 255, 0, 255, 255, 255, 255, 255, 255, 255]


def test_get_joint_limits_use_full_protocol_range():
    limits = get_joint_limits("ball_joint")
    assert limits["thumb_swing"] == (0, 255)
    assert limits["thumb_rotation"] == (0, 255)


def test_open_palm_pose_keeps_official_thumb_swing():
    assert open_palm_pose() == OPEN_PALM_POSE


def test_build_pose_rejects_unknown_joint():
    try:
        build_pose({"bad_joint": 1})
    except ValueError as exc:
        assert "bad_joint" in str(exc)
    else:
        raise AssertionError("expected ValueError")
