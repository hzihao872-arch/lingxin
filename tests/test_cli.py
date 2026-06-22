from l10_hand_control import cli
from l10_hand_control.errors import ControlError


class FakeController:
    def __init__(self):
        self.calls = []

    def list_devices(self):
        self.calls.append(("list_devices", None))
        return [{"interface": "can1", "model": "L10"}]

    def execute_gesture(self, name):
        self.calls.append(("execute_gesture", name))
        return {"status": "ok"}

    def set_speed(self, speed):
        self.calls.append(("set_speed", speed))
        return {"status": "ok"}

    def move_pose(self, pose):
        self.calls.append(("move_pose", pose))
        return {"status": "ok"}

    def get_state(self):
        self.calls.append(("get_state", None))
        return [1] * 10


def test_cli_dispatches_gesture_to_controller(capsys):
    fake = FakeController()

    exit_code = cli.main(
        ["--backend", "dashboard", "gesture", "握拳_Fist"],
        controller_factory=lambda _backend, _config: fake,
    )

    assert exit_code == 0
    assert fake.calls == [("execute_gesture", "握拳_Fist")]
    assert "ok" in capsys.readouterr().out


def test_cli_dispatches_pose_values_to_controller():
    fake = FakeController()

    exit_code = cli.main(
        ["--backend", "sdk", "pose", "80,80,80,80,80,80,80,80,80,80"],
        controller_factory=lambda _backend, _config: fake,
    )

    assert exit_code == 0
    assert fake.calls == [("move_pose", [80] * 10)]


def test_cli_dispatches_named_joint_overrides_to_pose():
    fake = FakeController()

    exit_code = cli.main(
        ["--backend", "sdk", "joint", "index_root=0", "thumb_rotation=30"],
        controller_factory=lambda _backend, _config: fake,
    )

    assert exit_code == 0
    assert fake.calls == [
        ("move_pose", [255, 70, 0, 255, 255, 255, 255, 255, 255, 30])
    ]


def test_cli_reports_control_error_without_stacktrace(capsys):
    def failing_factory(_backend, _config):
        raise ControlError("dashboard is not reachable")

    exit_code = cli.main(
        ["--backend", "dashboard", "list-devices"],
        controller_factory=failing_factory,
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "dashboard is not reachable" in captured.err
    assert "Traceback" not in captured.err


def test_cli_doctor_prints_config_without_controller(capsys):
    def failing_factory(_backend, _config):
        raise AssertionError("doctor should not create a controller")

    exit_code = cli.main(
        ["--backend", "dashboard", "doctor"],
        controller_factory=failing_factory,
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"hand_joint": "L10"' in captured.out
    assert '"can": "PCAN_USBBUS1"' in captured.out
