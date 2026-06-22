import requests

from l10_hand_control.config import HandConfig
from l10_hand_control.dashboard import DashboardController
from l10_hand_control.errors import ControlError


class BrokenSession:
    def get(self, *_args, **_kwargs):
        raise requests.ConnectionError("connection refused")


def test_dashboard_connection_error_is_actionable():
    controller = DashboardController(HandConfig(), session=BrokenSession())

    try:
        controller.list_devices()
    except ControlError as exc:
        message = str(exc)
        assert "dashboard" in message.lower()
        assert "127.0.0.1:7080" in message
    else:
        raise AssertionError("expected ControlError")
