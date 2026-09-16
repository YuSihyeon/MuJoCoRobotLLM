from __future__ import annotations

import json

import mujoco
import numpy as np

from text2mujoco.arm_mjcf_builder import ArmMJCFBuilder
from text2mujoco.arm_schemas import baseline_arm_scene
from text2mujoco.arm_simulation import (
    compile_arm_model,
    initialize_arm_state,
    resolve_arm_handles,
    run_arm_simulation,
)


def test_arm_model_compiles_and_named_lookup_works() -> None:
    spec = baseline_arm_scene()
    model, data = compile_arm_model(ArmMJCFBuilder().build(spec))
    handles = resolve_arm_handles(model)

    mujoco.mj_forward(model, data)

    assert handles.base_yaw_qpos >= 0
    assert handles.shoulder_actuator >= 0
    assert handles.cube_body >= 0
    assert np.all(np.isfinite(data.qpos))


def test_arm_initial_controller_waypoint_matches_physical_gripper_pose() -> None:
    spec = baseline_arm_scene()
    model, data = compile_arm_model(ArmMJCFBuilder().build(spec))
    handles = resolve_arm_handles(model)

    initialize_arm_state(model, data, spec, handles)

    desired = np.array([spec.object_position.x, spec.object_position.y, spec.table_height + 0.32])
    actual = np.array(data.xpos[handles.gripper_body], dtype=float)
    assert np.linalg.norm(actual - desired) < 0.04


def test_arm_headless_run_moves_cube_to_target_and_saves_artifacts(tmp_path) -> None:
    spec = baseline_arm_scene()

    result = run_arm_simulation(spec, artifact_dir=tmp_path, mode="headless")

    assert result.metrics.success is True
    assert result.metrics.termination_reason == "success"
    assert result.metrics.final_object_target_distance <= spec.target_radius
    assert result.metrics.assisted_grasp is False
    assert result.metrics.constraint_grasp is False
    assert result.metrics.maximum_object_height >= spec.table_height + spec.object_size.z + 0.08
    assert (
        result.metrics.release_object_bottom_height
        >= spec.table_height + spec.controller.release_drop_height * 0.5
    )
    assert result.metrics.minimum_object_bottom_height >= spec.table_height - 0.004
    assert result.artifacts.scene_xml_path.exists()
    assert result.artifacts.metrics_path.exists()
    metrics = json.loads(result.artifacts.metrics_path.read_text(encoding="utf-8"))
    assert metrics["success"] is True
    assert metrics["assisted_grasp"] is False
    assert metrics["constraint_grasp"] is False


def test_arm_contact_only_grasp_succeeds_without_constraint_or_pose_teleport(tmp_path) -> None:
    spec = baseline_arm_scene()

    result = run_arm_simulation(
        spec,
        artifact_dir=tmp_path,
        mode="headless",
        assisted_grasp=False,
        constraint_grasp=False,
    )

    assert result.metrics.success is True
    assert result.metrics.final_object_target_distance <= spec.target_radius
    assert result.metrics.assisted_grasp is False
    assert result.metrics.constraint_grasp is False
    assert result.metrics.maximum_object_height >= spec.table_height + spec.object_size.z + 0.08
    assert (
        result.metrics.release_object_bottom_height
        >= spec.table_height + spec.controller.release_drop_height * 0.5
    )
    assert result.metrics.minimum_object_bottom_height >= spec.table_height - 0.004
