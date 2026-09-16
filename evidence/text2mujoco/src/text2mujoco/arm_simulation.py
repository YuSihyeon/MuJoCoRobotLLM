"""MuJoCo runtime for the robot-arm pick-and-place demo."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import mujoco
import numpy as np

from text2mujoco.arm_controller import ArmCommand, ArmPickPlaceController, ArmState
from text2mujoco.arm_mjcf_builder import ArmMJCFBuilder, ArmModelNames
from text2mujoco.arm_schemas import ArmSceneSpec
from text2mujoco.errors import MJCFBuildError, SimulationStabilityError

ArmRunMode = Literal["headless", "viewer"]


@dataclass(frozen=True)
class ArmModelHandles:
    """Resolved MuJoCo addresses for the robot arm model."""

    base_yaw_qpos: int
    shoulder_qpos: int
    elbow_qpos: int
    wrist_qpos: int
    left_finger_qpos: int
    right_finger_qpos: int
    cube_qpos: int
    base_yaw_actuator: int
    shoulder_actuator: int
    elbow_actuator: int
    wrist_actuator: int
    left_finger_actuator: int
    right_finger_actuator: int
    cube_body: int
    gripper_body: int


@dataclass(frozen=True)
class ArmSimulationMetrics:
    """Outcome metrics for one arm run."""

    success: bool
    terminated: bool
    truncated: bool
    termination_reason: str
    simulation_time: float
    wall_clock_time: float
    final_object_target_distance: float
    minimum_object_target_distance: float
    maximum_object_height: float
    release_object_height: float
    release_object_bottom_height: float
    minimum_object_bottom_height: float
    physics_steps: int
    controller_state: str
    assisted_grasp: bool
    constraint_grasp: bool
    stability_status: str


@dataclass(frozen=True)
class ArmRunArtifacts:
    """Files written for one arm run."""

    run_id: str
    run_dir: Path
    scene_spec_path: Path
    scene_xml_path: Path
    metrics_path: Path
    manifest_path: Path
    log_path: Path


@dataclass(frozen=True)
class ArmSimulationResult:
    """Arm simulation result and saved artifacts."""

    metrics: ArmSimulationMetrics
    artifacts: ArmRunArtifacts
    scene_xml: str


def compile_arm_model(xml: str) -> tuple[mujoco.MjModel, mujoco.MjData]:
    """Compile robot-arm MJCF XML."""

    try:
        model = mujoco.MjModel.from_xml_string(xml)
    except Exception as exc:  # noqa: BLE001 - MuJoCo raises multiple exception types
        raise MJCFBuildError(f"MuJoCo could not compile robot-arm MJCF: {exc}") from exc
    return model, mujoco.MjData(model)


def _id(model: mujoco.MjModel, object_type: mujoco.mjtObj, name: str) -> int:
    object_id = int(mujoco.mj_name2id(model, object_type, name))
    if object_id < 0:
        raise MJCFBuildError(f"required MuJoCo robot-arm name is missing: {name}")
    return object_id


def _joint_qpos(model: mujoco.MjModel, name: str) -> int:
    joint_id = _id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
    return int(model.jnt_qposadr[joint_id])


def resolve_arm_handles(model: mujoco.MjModel) -> ArmModelHandles:
    """Resolve robot-arm named handles without magic indices."""

    return ArmModelHandles(
        base_yaw_qpos=_joint_qpos(model, ArmModelNames.BASE_YAW),
        shoulder_qpos=_joint_qpos(model, ArmModelNames.SHOULDER),
        elbow_qpos=_joint_qpos(model, ArmModelNames.ELBOW),
        wrist_qpos=_joint_qpos(model, ArmModelNames.WRIST),
        left_finger_qpos=_joint_qpos(model, ArmModelNames.LEFT_FINGER),
        right_finger_qpos=_joint_qpos(model, ArmModelNames.RIGHT_FINGER),
        cube_qpos=_joint_qpos(model, ArmModelNames.CUBE_FREE),
        base_yaw_actuator=_id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, ArmModelNames.MOVE_BASE_YAW),
        shoulder_actuator=_id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, ArmModelNames.MOVE_SHOULDER),
        elbow_actuator=_id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, ArmModelNames.MOVE_ELBOW),
        wrist_actuator=_id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, ArmModelNames.MOVE_WRIST),
        left_finger_actuator=_id(
            model, mujoco.mjtObj.mjOBJ_ACTUATOR, ArmModelNames.MOVE_LEFT_FINGER
        ),
        right_finger_actuator=_id(
            model, mujoco.mjtObj.mjOBJ_ACTUATOR, ArmModelNames.MOVE_RIGHT_FINGER
        ),
        cube_body=_id(model, mujoco.mjtObj.mjOBJ_BODY, ArmModelNames.CUBE),
        gripper_body=_id(model, mujoco.mjtObj.mjOBJ_BODY, ArmModelNames.GRIPPER),
    )


def _cube_center_on_table(spec: ArmSceneSpec, *, at_target: bool) -> np.ndarray:
    point = spec.target_position if at_target else spec.object_position
    return np.array([point.x, point.y, spec.table_height + spec.object_size.z / 2.0], dtype=float)


def set_cube_pose(
    data: mujoco.MjData,
    handles: ArmModelHandles,
    center: np.ndarray,
    *,
    clear_velocity: bool = True,
) -> None:
    """Set the free cube pose deterministically."""

    data.qpos[handles.cube_qpos : handles.cube_qpos + 7] = np.array(
        [center[0], center[1], center[2], 1.0, 0.0, 0.0, 0.0],
        dtype=float,
    )
    if clear_velocity:
        # Free joint velocity occupies six DoFs at the matching joint dof address.
        data.qvel[:] *= 0.0


def _assert_finite(data: mujoco.MjData) -> None:
    if not (
        np.all(np.isfinite(data.qpos))
        and np.all(np.isfinite(data.qvel))
        and np.all(np.isfinite(data.qacc))
    ):
        raise SimulationStabilityError("robot-arm MuJoCo state contains NaN or Inf")


def apply_command(data: mujoco.MjData, handles: ArmModelHandles, command: ArmCommand) -> None:
    """Write controller targets into named actuators."""

    targets = command.targets
    data.ctrl[handles.base_yaw_actuator] = targets.base_yaw
    data.ctrl[handles.shoulder_actuator] = targets.shoulder
    data.ctrl[handles.elbow_actuator] = targets.elbow
    data.ctrl[handles.wrist_actuator] = targets.wrist
    data.ctrl[handles.left_finger_actuator] = targets.left_finger
    data.ctrl[handles.right_finger_actuator] = targets.right_finger


def initialize_arm_state(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    spec: ArmSceneSpec,
    handles: ArmModelHandles,
) -> None:
    """Initialize cube and joints for a deterministic run."""

    controller = ArmPickPlaceController(spec)
    command = controller.compute(dt=0.0)
    data.qpos[handles.base_yaw_qpos] = command.targets.base_yaw
    data.qpos[handles.shoulder_qpos] = command.targets.shoulder
    data.qpos[handles.elbow_qpos] = command.targets.elbow
    data.qpos[handles.wrist_qpos] = command.targets.wrist
    data.qpos[handles.left_finger_qpos] = command.targets.left_finger
    data.qpos[handles.right_finger_qpos] = command.targets.right_finger
    apply_command(data, handles, command)
    set_cube_pose(data, handles, _cube_center_on_table(spec, at_target=False))
    mujoco.mj_forward(model, data)
    _assert_finite(data)


def object_target_distance(
    data: mujoco.MjData, handles: ArmModelHandles, spec: ArmSceneSpec
) -> float:
    """XY distance between cube center and target center."""

    cube_xy = np.array(data.xpos[handles.cube_body, :2], dtype=float)
    return float(np.linalg.norm(cube_xy - spec.target_position.array[:2]))


def assisted_cube_center(spec: ArmSceneSpec, command: ArmCommand) -> np.ndarray:
    """Return where the cube should be during assisted grasp/carry."""

    if command.place_assist_active:
        return _cube_center_on_table(spec, at_target=True)
    gripper = command.gripper_position.copy()
    gripper[2] = max(spec.table_height + spec.object_size.z / 2.0, gripper[2] - spec.object_size.z)
    return gripper


def run_arm_simulation(
    spec: ArmSceneSpec,
    *,
    artifact_dir: Path,
    mode: ArmRunMode = "headless",
    assisted_grasp: bool = False,
    constraint_grasp: bool = False,
) -> ArmSimulationResult:
    """Run a complete robot-arm pick-and-place simulation."""

    if assisted_grasp or constraint_grasp:
        msg = "robot-arm demo now uses contact-only physics; grasp assist options are disabled"
        raise SimulationStabilityError(msg)

    scene_xml = ArmMJCFBuilder().build(spec)
    model, data = compile_arm_model(scene_xml)
    handles = resolve_arm_handles(model)
    initialize_arm_state(model, data, spec, handles)

    controller = ArmPickPlaceController(spec)
    log_lines = [
        "arm spec generated",
        "arm MJCF built",
        "arm model compiled",
        f"assisted grasp: {assisted_grasp}",
        f"constraint grasp: {constraint_grasp}",
        "contact-only grasp: True",
        "arm simulation started",
    ]
    if mode == "viewer":
        try:
            import mujoco.viewer
        except Exception as exc:  # noqa: BLE001
            raise SimulationStabilityError(f"MuJoCo viewer is not available: {exc}") from exc
        with mujoco.viewer.launch_passive(model, data) as viewer:
            viewer.cam.type = mujoco.mjtCamera.mjCAMERA_FREE
            viewer.cam.distance = 1.2
            viewer.cam.azimuth = 120
            viewer.cam.elevation = -35
            return _run_loop(
                spec=spec,
                artifact_dir=artifact_dir,
                scene_xml=scene_xml,
                model=model,
                data=data,
                handles=handles,
                controller=controller,
                assisted_grasp=assisted_grasp,
                constraint_grasp=constraint_grasp,
                log_lines=log_lines,
                viewer=viewer,
                realtime=True,
            )
    return _run_loop(
        spec=spec,
        artifact_dir=artifact_dir,
        scene_xml=scene_xml,
        model=model,
        data=data,
        handles=handles,
        controller=controller,
        assisted_grasp=assisted_grasp,
        constraint_grasp=constraint_grasp,
        log_lines=log_lines,
        viewer=None,
        realtime=False,
    )


def _run_loop(
    *,
    spec: ArmSceneSpec,
    artifact_dir: Path,
    scene_xml: str,
    model: mujoco.MjModel,
    data: mujoco.MjData,
    handles: ArmModelHandles,
    controller: ArmPickPlaceController,
    assisted_grasp: bool,
    constraint_grasp: bool,
    log_lines: list[str],
    viewer: object | None,
    realtime: bool,
) -> ArmSimulationResult:
    start_wall = time.perf_counter()
    max_steps = int(spec.simulation_duration / spec.timestep)
    minimum_distance = object_target_distance(data, handles, spec)
    final_distance = minimum_distance
    maximum_object_height = float(data.xpos[handles.cube_body, 2])
    minimum_object_bottom_height = maximum_object_height - spec.object_size.z / 2.0
    release_object_height = maximum_object_height
    release_object_bottom_height = minimum_object_bottom_height
    command = controller.compute(dt=0.0)
    previous_state = command.state
    terminated = False
    truncated = False
    success = False
    reason = "time_limit"
    physics_steps = 0

    for _step_index in range(max_steps):
        physics_steps += 1
        command = controller.compute(dt=spec.timestep)
        if command.state != previous_state:
            log_lines.append(f"arm state changed: {command.state.value}")
            if command.state is ArmState.OPEN_GRIPPER:
                release_object_height = float(data.xpos[handles.cube_body, 2])
                release_object_bottom_height = release_object_height - spec.object_size.z / 2.0
                log_lines.append(
                    f"object release bottom height: {release_object_bottom_height:.5f}"
                )
            previous_state = command.state
        apply_command(data, handles, command)
        if assisted_grasp and (command.grasp_assist_active or command.place_assist_active):
            set_cube_pose(data, handles, assisted_cube_center(spec, command))
        mujoco.mj_step(model, data)
        if assisted_grasp and (command.grasp_assist_active or command.place_assist_active):
            set_cube_pose(data, handles, assisted_cube_center(spec, command))
            mujoco.mj_forward(model, data)
        _assert_finite(data)

        final_distance = object_target_distance(data, handles, spec)
        minimum_distance = min(minimum_distance, final_distance)
        cube_height = float(data.xpos[handles.cube_body, 2])
        cube_bottom = cube_height - spec.object_size.z / 2.0
        maximum_object_height = max(maximum_object_height, cube_height)
        minimum_object_bottom_height = min(minimum_object_bottom_height, cube_bottom)

        if viewer is not None:
            if not viewer.is_running():
                terminated = True
                reason = "viewer_closed"
                break
            viewer.sync()
            if realtime:
                time.sleep(max(spec.timestep, 0.001))

        object_was_lifted = maximum_object_height >= (
            spec.table_height + spec.object_size.z + 0.08
        )
        table_contact_was_physical = minimum_object_bottom_height >= spec.table_height - 0.004
        if (
            command.state is ArmState.SUCCESS
            and final_distance <= spec.target_radius
            and object_was_lifted
            and table_contact_was_physical
        ):
            success = True
            terminated = True
            reason = "success"
            log_lines.append("arm success")
            break

    if not terminated:
        truncated = True
        reason = "time_limit"
        log_lines.append("arm failure: time_limit")

    metrics = ArmSimulationMetrics(
        success=success,
        terminated=terminated,
        truncated=truncated,
        termination_reason=reason,
        simulation_time=float(data.time),
        wall_clock_time=float(time.perf_counter() - start_wall),
        final_object_target_distance=float(final_distance),
        minimum_object_target_distance=float(minimum_distance),
        maximum_object_height=float(maximum_object_height),
        release_object_height=float(release_object_height),
        release_object_bottom_height=float(release_object_bottom_height),
        minimum_object_bottom_height=float(minimum_object_bottom_height),
        physics_steps=physics_steps,
        controller_state=command.state.value,
        assisted_grasp=assisted_grasp,
        constraint_grasp=constraint_grasp,
        stability_status="stable",
    )
    artifacts = save_arm_artifacts(
        artifact_dir=artifact_dir,
        spec=spec,
        scene_xml=scene_xml,
        metrics=metrics,
        mode="viewer" if viewer is not None else "headless",
        log_lines=log_lines + ["arm artifacts saved"],
    )
    return ArmSimulationResult(metrics=metrics, artifacts=artifacts, scene_xml=scene_xml)


def _json_default(value: object) -> str:
    if isinstance(value, Path):
        return str(value)
    msg = f"Object of type {type(value).__name__} is not JSON serializable"
    raise TypeError(msg)


def save_arm_artifacts(
    *,
    artifact_dir: Path,
    spec: ArmSceneSpec,
    scene_xml: str,
    metrics: ArmSimulationMetrics,
    mode: ArmRunMode,
    log_lines: list[str],
) -> ArmRunArtifacts:
    """Write robot-arm scene, XML, metrics, manifest, and log."""

    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    digest = hashlib.sha256(spec.model_dump_json(round_trip=True).encode()).hexdigest()[:8]
    run_id = f"{stamp}_arm_{digest}"
    run_dir = artifact_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    scene_spec_path = run_dir / "scene_spec.json"
    scene_xml_path = run_dir / "scene.xml"
    metrics_path = run_dir / "metrics.json"
    manifest_path = run_dir / "manifest.json"
    log_path = run_dir / "run.log"

    spec.to_json_file(scene_spec_path)
    scene_xml_path.write_text(scene_xml, encoding="utf-8")
    metrics_path.write_text(
        json.dumps(asdict(metrics), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    manifest = {
        "run_id": run_id,
        "schema_version": spec.schema_version,
        "generator_version": "text2mujoco-arm-0.1.0",
        "mode": mode,
        "seed": spec.seed,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "assisted_grasp": metrics.assisted_grasp,
        "constraint_grasp": metrics.constraint_grasp,
        "files": {
            "scene_spec": scene_spec_path,
            "scene_xml": scene_xml_path,
            "metrics": metrics_path,
            "manifest": manifest_path,
            "run_log": log_path,
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )
    log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    return ArmRunArtifacts(
        run_id=run_id,
        run_dir=run_dir,
        scene_spec_path=scene_spec_path,
        scene_xml_path=scene_xml_path,
        metrics_path=metrics_path,
        manifest_path=manifest_path,
        log_path=log_path,
    )
