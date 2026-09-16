# Robot Arm Pick-and-Place Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a visible 4-DOF robot-arm pick-and-place demo that grasps a cube, carries it to a target, places it down, and opens in MuJoCo.

**Architecture:** Keep the existing pusher pipeline unchanged. Add independent `arm_*` modules for schema, MJCF, scripted IK/controller, simulation, demo viewer, and launchers. Use a deterministic assisted-grasp phase after finger closure so the first version is visually reliable and testable.

**Tech Stack:** Python 3.12+, MuJoCo official Python package, NumPy, Pydantic v2, pytest, ruff.

## Global Constraints

- Do not break existing pusher commands or tests.
- Do not call OpenAI or the network in robot-arm tests.
- Use SI units and named MuJoCo lookup, not magic qpos/ctrl indices.
- Use `pathlib.Path` for filesystem work.
- Save artifacts under `artifacts/<run_id>/`.
- Provide a visible launch path for the user: `open_robot_arm_demo.cmd`.

---

### Task 1: Red Tests

**Files:**
- Create: `tests/test_arm_schemas.py`
- Create: `tests/test_arm_mjcf_builder.py`
- Create: `tests/test_arm_controller.py`
- Create: `tests/test_arm_simulation.py`

**Interfaces:**
- `arm_schemas.baseline_arm_scene() -> ArmSceneSpec`
- `arm_mjcf_builder.ArmMJCFBuilder().build(spec) -> str`
- `arm_controller.solve_planar_ik(...) -> ArmJointTargets`
- `arm_simulation.run_arm_simulation(...) -> ArmSimulationResult`

- [x] Write failing tests that describe schema validation, deterministic XML, MuJoCo compile, IK, controller phases, and artifact saving.
- [x] Run the tests and confirm failure is missing arm modules.

### Task 2: Schema And Validation

**Files:**
- Create: `src/text2mujoco/arm_schemas.py`

**Interfaces:**
- `ArmSceneSpec`
- `ArmControllerConfig`
- `baseline_arm_scene()`
- `load_arm_scene_spec(path: Path)`

- [x] Implement strict Pydantic fields for table, cube, target, robot base, link lengths, gripper, timestep, and duration.

### Task 3: MJCF Builder

**Files:**
- Create: `src/text2mujoco/arm_mjcf_builder.py`

**Interfaces:**
- `ArmModelNames`
- `ArmMJCFBuilder.build(spec: ArmSceneSpec) -> str`

- [x] Build tabletop, target marker, free cube, base-yaw/shoulder/elbow/wrist arm, and symmetric finger joints.

### Task 4: Controller

**Files:**
- Create: `src/text2mujoco/arm_controller.py`

**Interfaces:**
- `ArmState`
- `ArmJointTargets`
- `solve_planar_ik(radius: float, z: float, upper: float, forearm: float) -> tuple[float, float]`
- `ArmPickPlaceController.compute(...) -> ArmCommand`

- [x] Implement waypoint state machine and bounded joint targets.

### Task 5: Simulation And Demo

**Files:**
- Create: `src/text2mujoco/arm_simulation.py`
- Create: `src/text2mujoco/arm_demo_viewer.py`
- Modify: `src/text2mujoco/cli.py`
- Create: `open_robot_arm_demo.ps1`
- Create: `open_robot_arm_demo.cmd`

**Interfaces:**
- `run_arm_simulation(spec, artifact_dir, mode, assisted_grasp=False, constraint_grasp=True)`
- CLI: `python -m text2mujoco arm-baseline --headless|--viewer`
- Launcher: `.\open_robot_arm_demo.cmd`

- [x] Implement run loop, named lookup, assisted carry/place, metrics, artifacts, CLI, and visible demo launcher.

### Task 6: Verification

- [x] Run `python -m ruff format .`
- [x] Run `python -m ruff check .`
- [x] Run `python -m pytest -q`
- [x] Run `python -m text2mujoco arm-baseline --headless`
- [x] Open `open_robot_arm_demo.cmd`
- [x] Explain implementation clearly in Korean.
