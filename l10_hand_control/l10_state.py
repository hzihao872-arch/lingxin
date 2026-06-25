from __future__ import annotations

from typing import Any


def normalize_l10_pose(state: Any) -> list[int]:
    """Convert SDK get_state() output into a 10-value L10 pose."""
    if state is None:
        raise ValueError("hand state is empty")

    if isinstance(state, dict):
        for key in ("pose", "position", "joint", "joints", "state"):
            if key in state:
                return normalize_l10_pose(state[key])
        raise ValueError(f"unsupported state dict keys: {sorted(state)}")

    if not isinstance(state, (list, tuple)):
        raise ValueError(f"unsupported state type: {type(state).__name__}")

    values = [int(round(float(value))) for value in state]
    if len(values) != 10:
        raise ValueError(f"L10 state must contain 10 values, got {len(values)}")

    for index, value in enumerate(values):
        if value < 0 or value > 255:
            raise ValueError(f"joint value out of range at index {index}: {value}")

    return values
