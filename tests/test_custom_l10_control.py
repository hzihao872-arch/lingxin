from examples.custom_l10_control import LOOP_COUNT, NUMBER_GESTURES, gesture_sequence


def test_gesture_sequence_repeats_one_to_five_ten_times():
    sequence = list(gesture_sequence())

    assert len(sequence) == LOOP_COUNT * len(NUMBER_GESTURES)
    assert [name for name, _pose in sequence[:5]] == ["1", "2", "3", "4", "5"]
    assert [name for name, _pose in sequence[-5:]] == ["1", "2", "3", "4", "5"]


def test_all_number_gestures_are_l10_poses():
    assert set(NUMBER_GESTURES) == {"1", "2", "3", "4", "5"}
    assert all(len(pose) == 10 for pose in NUMBER_GESTURES.values())
