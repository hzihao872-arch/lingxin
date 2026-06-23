from examples.l10_finger_ripple import (
    FINGER_NAMES,
    dominant_finger,
    pose_with_curled,
    ripple_order,
    ripple_steps,
)


def test_ripple_order_spreads_from_middle_finger():
    assert ripple_order(2) == [2, 3, 1, 4, 0]


def test_ripple_order_spreads_from_thumb():
    assert ripple_order(0) == [0, 1, 2, 3, 4]


def test_ripple_order_spreads_from_pinky():
    assert ripple_order(4) == [4, 3, 2, 1, 0]


def test_ripple_steps_alternate_curl_and_extend():
    steps = ripple_steps(2, step_delay=0.1)
    assert len(steps) == len(FINGER_NAMES) * 2
    assert steps[0][0] == "curl_middle"
    assert steps[4][0] == "curl_thumb"
    assert steps[5][0] == "extend_thumb"
    assert steps[-1][0] == "extend_middle"


def test_pose_with_curled_produces_valid_l10_pose():
    pose = pose_with_curled({1, 3})
    assert len(pose) == 10
    assert pose[2] == 85
    assert pose[4] == 85
    assert pose[3] == 255


def test_dominant_finger_picks_highest_reading():
    assert dominant_finger([0, 2, 9, 1, 0, 0], threshold=5) == 2
    assert dominant_finger([0, 0, 0, 0, 0, 0], threshold=5) is None
