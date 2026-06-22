from examples.handshake_on_pressure import (
    has_finger_pressure,
    has_palm_pressure,
    has_pressure,
    flatten_numbers,
)


def test_flatten_numbers_reads_nested_force_data():
    assert flatten_numbers([[0, -1], [2.5, [3]], "x"]) == [0.0, -1.0, 2.5, 3.0]


def test_has_pressure_ignores_missing_sensor_sentinel_values():
    assert not has_pressure([[-1, -1], [-1]], threshold=5)


def test_has_pressure_detects_force_above_threshold():
    assert has_pressure([[0, 3], [9]], threshold=5)


def test_has_palm_pressure_does_not_use_finger_touch_values():
    assert not has_palm_pressure([99, 99, 99, 99, 99, 0], threshold=5)


def test_has_finger_pressure_uses_first_five_touch_values():
    assert has_finger_pressure([0, 0, 8, 0, 0, 0], threshold=5)
