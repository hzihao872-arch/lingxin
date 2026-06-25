from l10_hand_control.l10_state import normalize_l10_pose


def test_normalize_l10_pose_from_list():
    assert normalize_l10_pose([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]) == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]


def test_normalize_l10_pose_from_dict_pose_key():
    assert normalize_l10_pose({"pose": [255] * 10}) == [255] * 10
