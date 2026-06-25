from l10_hand_control.async_pose_sender import AsyncPoseSender


class FakeController:
    def __init__(self):
        self.calls = []

    def move_pose(self, pose):
        self.calls.append(list(pose))


def test_async_pose_sender_callback_errors_do_not_stop_worker():
    controller = FakeController()

    def bad_callback(_pose, _count):
        raise RuntimeError("callback failed")

    sender = AsyncPoseSender(controller, min_interval=0.01, on_sent=bad_callback)
    sender.start()
    sender.submit([3] * 10)
    sender.stop(timeout=1.0)
    assert controller.calls == [[3] * 10]

    controller = FakeController()
    sender = AsyncPoseSender(controller, min_interval=0.01)
    sender.start()
    sender.submit([1] * 10)
    sender.submit([2] * 10)
    sender.stop(timeout=1.0)
    assert controller.calls
    assert controller.calls[-1] == [2] * 10
