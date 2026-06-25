from pathlib import Path

import pytest

from l10_hand_control.mediapipe_hands import DEFAULT_MODEL_PATH, ensure_hand_landmarker_model


def test_ensure_hand_landmarker_model_uses_existing_file(tmp_path: Path):
  model_path = tmp_path / "hand_landmarker.task"
  model_path.write_bytes(b"fake-model")
  assert ensure_hand_landmarker_model(model_path) == model_path


def test_default_model_path_is_under_data_models():
  assert DEFAULT_MODEL_PATH.name == "hand_landmarker.task"
  assert DEFAULT_MODEL_PATH.parent.name == "models"
