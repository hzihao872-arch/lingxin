"""Send L10 poses on a background thread so CAN I/O cannot freeze the camera loop."""

from __future__ import annotations

import queue
import threading
import time
from typing import Any, Callable


class AsyncPoseSender:
    """Queue the latest pose and send it to the hand without blocking the caller."""

    def __init__(self, controller: Any, min_interval: float, on_sent: Callable[[list[int], int], None] | None = None):
        self._controller = controller
        self._min_interval = max(min_interval, 0.001)
        self._on_sent = on_sent
        self._queue: queue.Queue[list[int]] = queue.Queue(maxsize=1)
        self._stop = threading.Event()
        self._sent_count = 0
        self._thread = threading.Thread(target=self._worker, name="l10-pose-sender", daemon=True)

    @property
    def sent_count(self) -> int:
        return self._sent_count

    def start(self) -> None:
        self._thread.start()

    def submit(self, pose: list[int]) -> None:
        payload = list(pose)
        while True:
            try:
                self._queue.put_nowait(payload)
                return
            except queue.Full:
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    return

    def _worker(self) -> None:
        last_send = 0.0
        while not self._stop.is_set():
            try:
                pose = self._queue.get(timeout=0.05)
            except queue.Empty:
                continue

            now = time.monotonic()
            wait_seconds = self._min_interval - (now - last_send)
            if wait_seconds > 0:
                time.sleep(wait_seconds)

            if self._stop.is_set():
                break

            try:
                self._controller.move_pose(pose)
            except Exception as exc:
                print(f"WARNING: move_pose failed: {exc}", flush=True)
            else:
                self._sent_count += 1
                if self._on_sent is not None:
                    try:
                        self._on_sent(pose, self._sent_count)
                    except Exception as exc:
                        print(f"WARNING: pose send callback failed: {exc}", flush=True)
            last_send = time.monotonic()

    def stop(self, timeout: float = 2.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and not self._queue.empty():
            time.sleep(0.005)
        self._stop.set()
        remaining = max(0.0, deadline - time.monotonic())
        self._thread.join(timeout=remaining)
