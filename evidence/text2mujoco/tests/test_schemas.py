from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from text2mujoco.schemas import SceneSpec, baseline_scene


def test_scene_spec_accepts_valid_baseline() -> None:
    spec = baseline_scene()

    assert isinstance(spec, SceneSpec)
    assert spec.schema_version == "1.0"
    assert spec.box_mass > 0
    assert spec.target_radius > 0


def test_scene_spec_rejects_numeric_range_violation() -> None:
    payload = baseline_scene().model_dump()
    payload["box_mass"] = 5.0

    with pytest.raises(ValidationError):
        SceneSpec.model_validate(payload)


def test_scene_spec_rejects_extra_fields() -> None:
    payload = baseline_scene().model_dump()
    payload["unsafe_xml"] = "<mujoco/>"

    with pytest.raises(ValidationError):
        SceneSpec.model_validate(payload)


def test_scene_spec_rejects_nan_and_inf() -> None:
    payload = baseline_scene().model_dump()
    payload["floor_friction"] = math.inf

    with pytest.raises(ValidationError):
        SceneSpec.model_validate(payload)

    payload = baseline_scene().model_dump()
    payload["box_position"] = [math.nan, 0.0]

    with pytest.raises(ValidationError):
        SceneSpec.model_validate(payload)
