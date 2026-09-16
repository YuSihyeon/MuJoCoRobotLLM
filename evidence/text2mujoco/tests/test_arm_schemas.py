from __future__ import annotations

import pytest
from pydantic import ValidationError

from text2mujoco.arm_schemas import ArmSceneSpec, baseline_arm_scene


def test_arm_scene_spec_accepts_valid_baseline() -> None:
    spec = baseline_arm_scene()

    assert isinstance(spec, ArmSceneSpec)
    assert spec.object_position.z > spec.table_height
    assert spec.target_radius > 0
    assert spec.robot.upper_arm_length > 0


def test_arm_scene_spec_rejects_unreachable_target() -> None:
    payload = baseline_arm_scene().model_dump()
    payload["target_position"] = {"x": 2.0, "y": 0.0, "z": payload["table_height"]}

    with pytest.raises(ValidationError):
        ArmSceneSpec.model_validate(payload)


def test_arm_scene_spec_rejects_extra_fields() -> None:
    payload = baseline_arm_scene().model_dump()
    payload["raw_xml"] = "<mujoco/>"

    with pytest.raises(ValidationError):
        ArmSceneSpec.model_validate(payload)
