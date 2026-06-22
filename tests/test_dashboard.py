from l10_hand_control.config import HandConfig
from l10_hand_control.dashboard import DashboardController


class FakeResponse:
    def __init__(self, payload, ok=True, status_code=200):
        self._payload = payload
        self.ok = ok
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self):
        self.calls = []

    def get(self, url, timeout):
        self.calls.append(("GET", url, None, timeout))
        return FakeResponse({"status": "ok", "data": [{"interface": "can1"}]})

    def post(self, url, json, timeout):
        self.calls.append(("POST", url, json, timeout))
        return FakeResponse({"status": "ok", "data": json})


def test_execute_gesture_posts_dashboard_exec_payload():
    session = FakeSession()
    controller = DashboardController(HandConfig(), session=session)

    controller.execute_gesture("握拳_Fist")

    method, url, payload, timeout = session.calls[-1]
    assert method == "POST"
    assert url == "http://127.0.0.1:7080/api/hand/exec"
    assert timeout == 5.0
    assert payload == {
        "mode": "gesture",
        "name": "握拳_Fist",
        "targets": [
            {
                "model": "L10",
                "variant": "ball_joint",
                "interface": "can1",
                "hand": "left",
            }
        ],
    }


def test_speed_posts_dashboard_speed_payload():
    session = FakeSession()
    controller = DashboardController(HandConfig(), session=session)

    controller.set_speed(120)

    assert session.calls[-1][2] == {
        "speed": 120,
        "targets": [
            {
                "model": "L10",
                "variant": "ball_joint",
                "interface": "can1",
                "hand": "left",
            }
        ],
    }
