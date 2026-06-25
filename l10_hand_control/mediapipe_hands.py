"""MediaPipe Tasks hand tracking helpers for camera teleop."""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

HAND_LANDMARKER_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
DEFAULT_MODEL_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "models" / "hand_landmarker.task"
)


@dataclass(frozen=True)
class DetectedHand:
    landmarks: list[tuple[float, float, float]]
    handedness: str


def ensure_hand_landmarker_model(model_path: Path | None = None) -> Path:
    path = Path(model_path or DEFAULT_MODEL_PATH)
    if path.exists():
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading hand landmarker model to {path} ...", flush=True)
    try:
        urllib.request.urlretrieve(HAND_LANDMARKER_URL, path)
    except urllib.error.URLError as exc:
        raise RuntimeError(
            "Failed to download the MediaPipe hand model. Check your network, or "
            f"manually download:\n  {HAND_LANDMARKER_URL}\n"
            f"and save it to:\n  {path}"
        ) from exc
    print("Model download complete.", flush=True)
    return path


class HandTracker:
    """Wrap MediaPipe HandLandmarker for synchronous webcam frames."""

    def __init__(
        self,
        model_path: Path | None = None,
        num_hands: int = 1,
        min_detection_confidence: float = 0.6,
        min_tracking_confidence: float = 0.5,
    ):
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions
        from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode

        self._mp = mp
        self._frame_index = 0
        resolved_model = ensure_hand_landmarker_model(model_path)
        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(resolved_model)),
            running_mode=RunningMode.VIDEO,
            num_hands=num_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self._landmarker = HandLandmarker.create_from_options(options)
        self._closed = False

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        landmarker = self._landmarker
        self._landmarker = None
        if landmarker is None:
            return
        try:
            landmarker.close()
        except OSError:
            pass

    def detect(self, rgb_frame) -> list[DetectedHand]:
        import numpy as np

        if self._closed:
            raise RuntimeError("HandTracker is closed")

        if not isinstance(rgb_frame, np.ndarray):
            raise TypeError("rgb_frame must be a numpy array")

        self._frame_index += 1
        timestamp_ms = int(time.monotonic() * 1000)
        mp_image = self._mp.Image(
            image_format=self._mp.ImageFormat.SRGB,
            data=np.ascontiguousarray(rgb_frame),
        )
        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)

        detected: list[DetectedHand] = []
        if not result.hand_landmarks:
            return detected

        handedness_groups = result.handedness or []
        for index, landmark_group in enumerate(result.hand_landmarks):
            landmarks = [(lm.x, lm.y, lm.z) for lm in landmark_group]
            label = "Unknown"
            if index < len(handedness_groups) and handedness_groups[index]:
                label = handedness_groups[index][0].category_name
            detected.append(DetectedHand(landmarks=landmarks, handedness=label))
        return detected


def draw_hand_landmarks(frame, hand_landmarks, cv2) -> None:
    from mediapipe.tasks.python.vision import HandLandmarksConnections, drawing_utils

    connections = HandLandmarksConnections.HAND_CONNECTIONS
    landmark_list = [
        drawing_utils.landmark_module.NormalizedLandmark(x=lm[0], y=lm[1], z=lm[2])
        for lm in hand_landmarks
    ]
    drawing_utils.draw_landmarks(
        frame,
        landmark_list,
        connections,
        drawing_utils.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
        drawing_utils.DrawingSpec(color=(0, 128, 255), thickness=2, circle_radius=2),
    )
