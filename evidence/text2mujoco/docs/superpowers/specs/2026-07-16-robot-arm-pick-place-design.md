# Robot Arm Pick-and-Place Design

## Goal

Extend Text-to-MuJoCo Push World with a visible robot-arm manipulation demo: a simple 4-DOF arm with a two-finger gripper picks up a small cube, carries it to a target area, places it down, and retreats.

## Chosen Approach

Use a custom, deterministic tabletop robot instead of importing a full industrial arm. The first version uses base yaw, shoulder pitch, elbow pitch, wrist pitch, and symmetric gripper fingers. A scripted inverse-kinematics controller computes stable joint targets for a sequence of waypoints.

This is more realistic than an XYZ gantry and more achievable than a full 6-DOF industrial arm. It should visibly look like a robot arm while keeping the initial implementation testable and tunable.

## Scope

The existing pusher pipeline remains intact. Robot-arm functionality is added in separate modules:

- `arm_schemas.py`: strict `ArmSceneSpec`, cube/object parameters, target, table, arm limits, gripper settings.
- `arm_mjcf_builder.py`: deterministic MJCF builder for tabletop, target marker, cube, 4-DOF arm, and two-finger gripper.
- `arm_controller.py`: pick-and-place state machine and planar IK helper.
- `arm_simulation.py`: MuJoCo compile, named lookup, reset, run loop, metrics, and artifact saving.
- `arm_demo_viewer.py`: slow looping viewer demo for user inspection.
- CLI additions in `cli.py`: `arm-baseline --headless` and `arm-baseline --viewer`.
- Launchers: `open_robot_arm_demo.cmd` and `open_robot_arm_demo.ps1`.

## Robot Model

The robot is mounted on the table near one edge. The arm has:

- `base_yaw`: horizontal rotation toward the object/target.
- `shoulder`: vertical planar lift joint.
- `elbow`: vertical planar reach joint.
- `wrist`: keeps the gripper approximately downward.
- `left_finger` and `right_finger`: symmetric slide joints or hinge joints for grasping.

The cube starts on the table, sized for reliable gripper contact. The target is a non-colliding visual marker on the table. All units are SI.

## Controller State Machine

The scripted controller runs these states:

1. `RESET`
2. `APPROACH_ABOVE_OBJECT`
3. `DESCEND_TO_GRASP`
4. `CLOSE_GRIPPER`
5. `LIFT_OBJECT`
6. `MOVE_ABOVE_TARGET`
7. `DESCEND_TO_PLACE`
8. `OPEN_GRIPPER`
9. `RETREAT`
10. `SUCCESS`
11. `FAILED`

The controller never calls the LLM inside the physics loop. It uses deterministic waypoints and bounded joint targets. Success means the cube is within the target radius, resting near table height, and the simulation state remains finite.

## Grasp Strategy

The first version uses contact-based grasping with tuned friction, finger force limits, and a small cube. To reduce first-version brittleness, the gripper descends vertically, closes for a short hold time, lifts slowly, then carries the object. If contact grasp is unstable in verification, the implementation may add a clearly documented optional weld-equality assist during the closed-gripper carry phase, but the preferred first attempt is physical contact only.

## Validation

Validation checks include:

- All numeric values are finite.
- Object and target fit on the table.
- Object and target are reachable by the arm.
- Object is not already at the target.
- Arm joint ranges can reach all scripted waypoints.
- MJCF compiles in MuJoCo.
- Headless smoke steps remain finite.
- Baseline pick-place moves the cube toward the target and records metrics.

## Tests

Add offline tests for:

- `ArmSceneSpec` valid baseline and range rejection.
- Reachability validation.
- Deterministic arm MJCF generation and XML parsing.
- MuJoCo compile and named lookup.
- IK target generation within joint limits.
- Controller state progression.
- Headless smoke simulation with finite qpos/qvel/qacc.
- Baseline arm run artifact saving.

No real OpenAI API calls are added to the default tests.

## User Experience

The user can run:

```powershell
python -m text2mujoco arm-baseline --headless
python -m text2mujoco arm-baseline --viewer
.\open_robot_arm_demo.cmd
```

The demo viewer runs slowly and loops so the user can see the arm approach, grasp, lift, move, place, and retreat.

## Known Risks

Grasp stability is the hardest part. Contact-only grasps can be sensitive to friction, solver settings, finger geometry, and actuator strength. The first version prioritizes a stable, understandable demo over industrial realism.
