from __future__ import annotations

import json

import numpy as np

from text2mujoco.mjcf_builder import MJCFBuilder
from text2mujoco.schemas import baseline_scene
from text2mujoco.simulation import compile_model, resolve_handles, run_push_simulation, step_finite


def test_mujoco_model_compiles_and_named_lookup_works() -> None:
    model, data = compile_model(MJCFBuilder().build(baseline_scene()))
    handles = resolve_handles(model)

    assert model.nq > 0
    assert handles.pusher_x_qpos >= 0
    assert handles.move_x_actuator >= 0
    assert handles.box_body >= 0
    assert np.all(np.isfinite(data.qpos))


def test_headless_steps_remain_finite() -> None:
    model, data = compile_model(MJCFBuilder().build(baseline_scene()))

    step_finite(model, data, steps=50)

    assert np.all(np.isfinite(data.qpos))
    assert np.all(np.isfinite(data.qvel))
    assert np.all(np.isfinite(data.qacc))


def test_baseline_run_moves_box_toward_target_and_saves_artifacts(tmp_path) -> None:
    spec = baseline_scene()
    initial_distance = float(np.linalg.norm(spec.target_position.array - spec.box_position.array))

    result = run_push_simulation(spec, artifact_dir=tmp_path, mode="headless", prompt=None)

    assert result.metrics.final_box_target_distance < initial_distance
    assert result.metrics.physics_steps > 0
    assert result.metrics.stability_status == "stable"
    assert result.artifacts.scene_spec_path.exists()
    assert result.artifacts.scene_xml_path.exists()
    assert result.artifacts.metrics_path.exists()
    assert result.artifacts.manifest_path.exists()
    metrics = json.loads(result.artifacts.metrics_path.read_text(encoding="utf-8"))
    assert metrics["final_box_target_distance"] == result.metrics.final_box_target_distance


def test_timeout_is_reported_as_truncated(tmp_path) -> None:
    spec = baseline_scene().model_copy(update={"simulation_duration": 0.02})

    result = run_push_simulation(spec, artifact_dir=tmp_path, mode="headless", prompt=None)

    assert result.metrics.truncated is True
    assert result.metrics.termination_reason == "time_limit"
