from examples.l25_handshake_on_pressure import (
    HANDSHAKE_POSE_L25,
    OPEN_POSE_L25,
    has_pressure,
)


def test_l25_poses_have_expected_length():
    assert len(OPEN_POSE_L25) == 25
    assert len(HANDSHAKE_POSE_L25) == 25


def test_l25_pressure_threshold_detection():
    assert has_pressure([0, 0, 6, 0, 0], threshold=5)
    assert not has_pressure([0, 0, 5, 0, 0], threshold=5)
