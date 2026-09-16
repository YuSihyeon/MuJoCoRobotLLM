from __future__ import annotations

import pytest

from text2mujoco.errors import SceneValidationError
from text2mujoco.schemas import baseline_scene
from text2mujoco.validation import compute_pusher_start, validate_scene


def test_validation_rejects_box_and_target_too_close() -> None:
    spec = baseline_scene().model_copy(update={"target_position": [0.14, 0.0]})

    with pytest.raises(SceneValidationError, match="box and target"):
        validate_scene(spec, include_mujoco=False)


def test_validation_rejects_box_outside_arena() -> None:
    spec = baseline_scene().model_copy(update={"box_position": [1.25, 0.0]})

    with pytest.raises(SceneValidationError, match="box must fit"):
        validate_scene(spec, include_mujoco=False)


def test_pusher_behind_point_is_inside_arena_and_not_overlapping_box() -> None:
    spec = baseline_scene()
    start = compute_pusher_start(spec)

    assert -spec.arena_half_size < start.x < spec.arena_half_size
    assert -spec.arena_half_size < start.y < spec.arena_half_size
    assert abs(start.x - spec.box_position.x) > spec.box_size.x / 2


def test_validation_reports_multiple_errors() -> None:
    spec = baseline_scene().model_copy(
        update={
            "box_position": [1.25, 0.0],
            "target_position": [1.25, 0.0],
        }
    )

    with pytest.raises(SceneValidationError) as exc_info:
        validate_scene(spec, include_mujoco=False)

    assert len(exc_info.value.issues) >= 2
