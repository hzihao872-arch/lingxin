from l10_hand_control.l10_pose import L10_JOINTS, OPEN_PALM_POSE, build_pose


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


def test_build_pose_rejects_unknown_joint():
    try:
        build_pose({"bad_joint": 1})
    except ValueError as exc:
        assert "bad_joint" in str(exc)
    else:
        raise AssertionError("expected ValueError")
