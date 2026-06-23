from examples.l10_snap_finger import (
    LOOP_COUNT,
    SNAP_CYCLE,
    SNAP_POSE,
    snap_sequence,
)


def test_snap_cycle_has_expected_phases():
    assert [step["name"] for step in SNAP_CYCLE] == [
        "open",
        "prepare",
        "preload",
        "snap",
        "settle",
    ]


def test_snap_sequence_repeats_full_cycle():
    sequence = snap_sequence()
    assert len(sequence) == LOOP_COUNT * len(SNAP_CYCLE)
    assert sequence[0]["name"] == "open"
    assert sequence[3]["name"] == "snap"
    assert sequence[-1]["name"] == "settle"


def test_snap_pose_extends_middle_finger():
    assert len(SNAP_POSE) == 10
    assert SNAP_POSE[3] == 255
