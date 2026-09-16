"""MuJoCo compilation, named access, and push simulation runtime."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import mujoco
import numpy as np

from text2mujoco.controller import PushController
from text2mujoco.errors import MJCFBuildError, SimulationStabilityError
from text2mujoco.metrics import RunMode, SimulationMetrics, SimulationResult, save_run_artifacts
from text2mujoco.mjcf_builder import MJCFBuilder, ModelNames
from text2mujoco.schemas import SceneSpec
from text2mujoco.validation import compute_pusher_start, validate_scene


@dataclass(frozen=True)
class ModelHandles:
    """Resolved named MuJoCo addresses for joints, actuators, and bodies."""

    pusher_x_qpos: int
    pusher_y_qpos: int
    pusher_x_dof: int
    pusher_y_dof: int
    box_qpos: int
    box_dof: int
    move_x_actuator: int
    move_y_actuator: int
    pusher_body: int
    box_body: int
    target_body: int


def compile_model(xml: str) -> tuple[mujoco.MjModel, mujoco.MjData]:
    """Compile MJCF XML and return MuJoCo model/data."""

    try:
        model = mujoco.MjModel.from_xml_string(xml)
    except Exception as exc:  # noqa: BLE001 - MuJoCo raises several exception types
        raise MJCFBuildError(f"MuJoCo could not compile generated MJCF: {exc}") from exc
    data = mujoco.MjData(model)
    return model, data


def _id(model: mujoco.MjModel, object_type: mujoco.mjtObj, name: str) -> int:
    object_id = int(mujoco.mj_name2id(model, object_type, name))
    if object_id < 0:
        raise MJCFBuildError(f"required MuJoCo name is missing: {name}")
    return object_id


def resolve_handles(model: mujoco.MjModel) -> ModelHandles:
    """Resolve named joints, actuators, and bodies without magic qpos indices."""

    pusher_x_joint = _id(model, mujoco.mjtObj.mjOBJ_JOINT, ModelNames.PUSHER_X)
    pusher_y_joint = _id(model, mujoco.mjtObj.mjOBJ_JOINT, ModelNames.PUSHER_Y)
    box_joint = _id(model, mujoco.mjtObj.mjOBJ_JOINT, ModelNames.BOX_FREE)
    return ModelHandles(
        pusher_x_qpos=int(model.jnt_qposadr[pusher_x_joint]),
        pusher_y_qpos=int(model.jnt_qposadr[pusher_y_joint]),
        pusher_x_dof=int(model.jnt_dofadr[pusher_x_joint]),
        pusher_y_dof=int(model.jnt_dofadr[pusher_y_joint]),
        box_qpos=int(model.jnt_qposadr[box_joint]),
        box_dof=int(model.jnt_dofadr[box_joint]),
        move_x_actuator=_id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, ModelNames.MOVE_X),
        move_y_actuator=_id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, ModelNames.MOVE_Y),
        pusher_body=_id(model, mujoco.mjtObj.mjOBJ_BODY, ModelNames.PUSHER),
        box_body=_id(model, mujoco.mjtObj.mjOBJ_BODY, ModelNames.BOX),
        target_body=_id(model, mujoco.mjtObj.mjOBJ_BODY, ModelNames.TARGET),
    )


def initialize_state(
    model: mujoco.MjModel, data: mujoco.MjData, spec: SceneSpec, handles: ModelHandles
) -> None:
    """Set deterministic pusher and box initial state using named addresses."""

    pusher_start = compute_pusher_start(spec)
    data.qpos[handles.pusher_x_qpos] = pusher_start.x
    data.qpos[handles.pusher_y_qpos] = pusher_start.y
    data.qvel[handles.pusher_x_dof] = 0.0
    data.qvel[handles.pusher_y_dof] = 0.0

    data.qpos[handles.box_qpos : handles.box_qpos + 7] = np.array(
        [spec.box_position.x, spec.box_position.y, spec.box_size.z / 2.0, 1.0, 0.0, 0.0, 0.0]
    )
    data.qvel[handles.box_dof : handles.box_dof + 6] = 0.0
    data.ctrl[handles.move_x_actuator] = pusher_start.x
    data.ctrl[handles.move_y_actuator] = pusher_start.y
    mujoco.mj_forward(model, data)
    _assert_finite(data)


def _assert_finite(data: mujoco.MjData) -> None:
    if not (
        np.all(np.isfinite(data.qpos))
        and np.all(np.isfinite(data.qvel))
        and np.all(np.isfinite(data.qacc))
    ):
        raise SimulationStabilityError("MuJoCo state contains NaN or Inf")


def step_finite(model: mujoco.MjModel, data: mujoco.MjData, *, steps: int) -> None:
    """Step MuJoCo and raise if qpos/qvel/qacc becomes non-finite."""

    for _ in range(steps):
        mujoco.mj_step(model, data)
        _assert_finite(data)


def body_xy(data: mujoco.MjData, body_id: int) -> np.ndarray:
    """Return world XY position for a body."""

    return np.array(data.xpos[body_id, :2], dtype=float)


def make_observation(
    data: mujoco.MjData, handles: ModelHandles, spec: SceneSpec
) -> dict[str, list[float]]:
    """Build a small RL-friendly observation dictionary."""

    pusher_position = body_xy(data, handles.pusher_body)
    box_position = body_xy(data, handles.box_body)
    target_position = spec.target_position.array
    pusher_velocity = np.array(
        [data.qvel[handles.pusher_x_dof], data.qvel[handles.pusher_y_dof]], dtype=float
    )
    box_velocity = np.array(data.qvel[handles.box_dof : handles.box_dof + 2], dtype=float)
    return {
        "pusher_position": pusher_position.tolist(),
        "pusher_velocity": pusher_velocity.tolist(),
        "box_position": box_position.tolist(),
        "box_velocity": box_velocity.tolist(),
        "target_position": target_position.tolist(),
        "box_to_target": (target_position - box_position).tolist(),
        "pusher_to_box": (box_position - pusher_position).tolist(),
    }


def _distance(data: mujoco.MjData, handles: ModelHandles, spec: SceneSpec) -> float:
    return float(np.linalg.norm(spec.target_position.array - body_xy(data, handles.box_body)))


def _outside_arena(position: np.ndarray, spec: SceneSpec, margin: float = 0.0) -> bool:
    limit = spec.arena_half_size + margin
    return bool(np.any(np.abs(position) > limit))


def run_push_simulation(
    spec: SceneSpec,
    *,
    artifact_dir: Path,
    mode: RunMode = "headless",
    prompt: str | None = None,
    model_name: str | None = None,
) -> SimulationResult:
    """Run a complete push simulation and save artifacts."""

    if mode not in {"headless", "viewer"}:
        msg = f"unsupported run mode: {mode}"
        raise ValueError(msg)

    log_lines = ["spec generated", "spec validated"]
    validate_scene(spec, include_mujoco=False)
    scene_xml = MJCFBuilder().build(spec)
    log_lines.append("MJCF built")
    model, data = compile_model(scene_xml)
    handles = resolve_handles(model)
    initialize_state(model, data, spec, handles)
    log_lines.append("model compiled")

    if mode == "viewer":
        return _run_viewer(
            spec=spec,
            artifact_dir=artifact_dir,
            prompt=prompt,
            model_name=model_name,
            scene_xml=scene_xml,
            model=model,
            data=data,
            handles=handles,
            log_lines=log_lines,
        )
    return _run_headless(
        spec=spec,
        artifact_dir=artifact_dir,
        prompt=prompt,
        model_name=model_name,
        scene_xml=scene_xml,
        model=model,
        data=data,
        handles=handles,
        log_lines=log_lines,
    )


def _run_headless(
    *,
    spec: SceneSpec,
    artifact_dir: Path,
    prompt: str | None,
    model_name: str | None,
    scene_xml: str,
    model: mujoco.MjModel,
    data: mujoco.MjData,
    handles: ModelHandles,
    log_lines: list[str],
) -> SimulationResult:
    controller = PushController(spec)
    log_lines.append("simulation started")
    return _simulate_loop(
        spec=spec,
        artifact_dir=artifact_dir,
        prompt=prompt,
        model_name=model_name,
        scene_xml=scene_xml,
        model=model,
        data=data,
        handles=handles,
        controller=controller,
        log_lines=log_lines,
        viewer=None,
    )


def _run_viewer(
    *,
    spec: SceneSpec,
    artifact_dir: Path,
    prompt: str | None,
    model_name: str | None,
    scene_xml: str,
    model: mujoco.MjModel,
    data: mujoco.MjData,
    handles: ModelHandles,
    log_lines: list[str],
) -> SimulationResult:
    try:
        import mujoco.viewer
    except Exception as exc:  # noqa: BLE001 - optional GUI dependency path
        raise SimulationStabilityError(f"MuJoCo viewer is not available: {exc}") from exc

    controller = PushController(spec)
    log_lines.append("simulation started")
    with mujoco.viewer.launch_passive(model, data) as viewer:
        viewer.cam.type = mujoco.mjtCamera.mjCAMERA_FREE
        viewer.cam.distance = spec.arena_half_size * 2.4
        viewer.cam.azimuth = 90
        viewer.cam.elevation = -55
        return _simulate_loop(
            spec=spec,
            artifact_dir=artifact_dir,
            prompt=prompt,
            model_name=model_name,
            scene_xml=scene_xml,
            model=model,
            data=data,
            handles=handles,
            controller=controller,
            log_lines=log_lines,
            viewer=viewer,
        )


def _simulate_loop(
    *,
    spec: SceneSpec,
    artifact_dir: Path,
    prompt: str | None,
    model_name: str | None,
    scene_xml: str,
    model: mujoco.MjModel,
    data: mujoco.MjData,
    handles: ModelHandles,
    controller: PushController,
    log_lines: list[str],
    viewer: object | None,
) -> SimulationResult:
    start_wall = time.perf_counter()
    control_decimation = max(1, round(1.0 / (spec.controller.control_hz * spec.timestep)))
    max_steps = max(1, int(spec.simulation_duration / spec.timestep))
    minimum_distance = _distance(data, handles, spec)
    final_distance = minimum_distance
    maximum_speed = 0.0
    control_steps = 0
    terminated = False
    truncated = False
    success = False
    reason = "time_limit"
    last_state = controller.state

    for step_index in range(max_steps):
        if step_index % control_decimation == 0:
            observation = make_observation(data, handles, spec)
            action = controller.compute_action(observation, data.time)
            data.ctrl[handles.move_x_actuator] = float(action[0])
            data.ctrl[handles.move_y_actuator] = float(action[1])
            control_steps += 1
            if controller.state != last_state:
                log_lines.append(f"controller state changed: {controller.state.value}")
                last_state = controller.state

        mujoco.mj_step(model, data)
        _assert_finite(data)

        box_position = body_xy(data, handles.box_body)
        pusher_position = body_xy(data, handles.pusher_body)
        box_speed = float(np.linalg.norm(data.qvel[handles.box_dof : handles.box_dof + 2]))
        pusher_speed = float(
            np.linalg.norm([data.qvel[handles.pusher_x_dof], data.qvel[handles.pusher_y_dof]])
        )
        maximum_speed = max(maximum_speed, box_speed, pusher_speed)
        final_distance = _distance(data, handles, spec)
        minimum_distance = min(minimum_distance, final_distance)

        if viewer is not None:
            if not viewer.is_running():
                reason = "viewer_closed"
                terminated = True
                break
            viewer.sync()
            elapsed = time.perf_counter() - start_wall
            if data.time > elapsed:
                time.sleep(min(data.time - elapsed, 0.01))

        if _outside_arena(box_position, spec, margin=0.05):
            reason = "box_outside_arena"
            terminated = True
            break
        if _outside_arena(pusher_position, spec, margin=0.05):
            reason = "pusher_outside_arena"
            terminated = True
            break
        if maximum_speed > spec.controller.maximum_speed:
            reason = "unstable_speed"
            terminated = True
            break

        inside_target = final_distance <= spec.target_radius
        if controller.update_success_hold(inside_target, spec.timestep):
            success = True
            terminated = True
            reason = "success"
            log_lines.append("success")
            break

    physics_steps = int(data.time / spec.timestep)
    if not terminated:
        truncated = True
        reason = "time_limit"
        log_lines.append("failure: time_limit")

    metrics = SimulationMetrics(
        success=success,
        terminated=terminated,
        truncated=truncated,
        termination_reason=reason,
        simulation_time=float(data.time),
        wall_clock_time=float(time.perf_counter() - start_wall),
        final_box_target_distance=float(final_distance),
        minimum_box_target_distance=float(minimum_distance),
        control_steps=control_steps,
        physics_steps=physics_steps,
        maximum_speed=float(maximum_speed),
        stability_status="stable",
    )
    log_lines.append("artifacts saved")
    artifacts = save_run_artifacts(
        artifact_dir=artifact_dir,
        spec=spec,
        scene_xml=scene_xml,
        metrics=metrics,
        mode="viewer" if viewer is not None else "headless",
        prompt=prompt,
        model_name=model_name,
        log_lines=log_lines,
    )
    return SimulationResult(metrics=metrics, artifacts=artifacts, scene_xml=scene_xml)
