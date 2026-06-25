from pathlib import Path

from l10_hand_control.config import HandConfig
from l10_hand_control.sdk_backend import SdkController


class FakeHand:
    def __init__(self):
        self.calls = []

    def set_speed(self, speed):
        self.calls.append(("set_speed", speed))

    def finger_move(self, pose):
        self.calls.append(("finger_move", pose))

    def get_state(self):
        self.calls.append(("get_state", None))
        return [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    def get_torque(self):
        self.calls.append(("get_torque", None))
        return [100] * 10

    def set_torque(self, torque):
        self.calls.append(("set_torque", torque))


class FakeFactory:
    def __init__(self):
        self.created_with = None
        self.hand = FakeHand()

    def __call__(self, *, hand_joint, hand_type, can):
        self.created_with = {
            "hand_joint": hand_joint,
            "hand_type": hand_type,
            "can": can,
        }
        return self.hand


def test_sdk_backend_constructs_official_api_with_l10_left_config():
    factory = FakeFactory()
    config = HandConfig(sdk_path=Path("C:/sdk/linkerhand-python-sdk"))

    controller = SdkController(config, api_factory=factory)
    controller.set_speed([120] * 10)

    assert factory.created_with == {
        "hand_joint": "L10",
        "hand_type": "left",
        "can": "PCAN_USBBUS1",
    }
    assert factory.hand.calls == [("set_speed", [120] * 10)]


def test_sdk_backend_validates_l10_pose_length():
    controller = SdkController(HandConfig(), api_factory=FakeFactory())

    try:
        controller.move_pose([80] * 9)
    except ValueError as exc:
        assert "10" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_sdk_backend_moves_l10_pose():
    factory = FakeFactory()
    controller = SdkController(HandConfig(), api_factory=factory)

    controller.move_pose([80] * 10)

    assert factory.hand.calls == [("finger_move", [80] * 10)]


def test_sdk_backend_teach_mode_sets_and_restores_torque():
    factory = FakeFactory()
    controller = SdkController(HandConfig(), api_factory=factory)

    result = controller.enter_teach_mode()
    assert result["teach_active"] is True
    assert controller.teach_active is True
    assert factory.hand.calls[-1] == ("set_torque", [0] * 10)

    pose = controller.read_pose()
    assert pose == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    stop = controller.exit_teach_mode()
    assert stop["teach_active"] is False
    assert controller.teach_active is False
    assert factory.hand.calls[-1] == ("set_torque", [100] * 10)
