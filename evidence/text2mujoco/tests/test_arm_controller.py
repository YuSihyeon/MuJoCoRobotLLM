from __future__ import annotations

import math

from text2mujoco.arm_controller import ArmPickPlaceController, ArmState, solve_planar_ik
from text2mujoco.arm_schemas import baseline_arm_scene


def test_planar_ik_returns_reachable_joint_angles() -> None:
    spec = baseline_arm_scene()

    shoulder, elbow = solve_planar_ik(
        radius=0.32,
        z=0.22,
        upper=spec.robot.upper_arm_length,
        forearm=spec.robot.forearm_length,
    )

    assert math.isfinite(shoulder)
    assert math.isfinite(elbow)
    assert -2.8 < shoulder < 2.8
    assert -2.8 < elbow < 2.8


def test_arm_controller_progresses_through_pick_place_states() -> None:
    spec = baseline_arm_scene()
    controller = ArmPickPlaceController(spec)
    states = []

    max_steps = int(spec.simulation_duration / spec.timestep) + 10
    for _ in range(max_steps):
        command = controller.compute(dt=spec.timestep)
        states.append(command.state)
        if command.state is ArmState.SUCCESS:
            break

    assert ArmState.APPROACH_ABOVE_OBJECT in states
    assert ArmState.CLOSE_GRIPPER in states
    assert ArmState.MOVE_ABOVE_TARGET in states
    assert ArmState.OPEN_GRIPPER in states
    assert states[-1] is ArmState.SUCCESS


def test_arm_controller_opens_gripper_slightly_above_target() -> None:
    spec = baseline_arm_scene()
    controller = ArmPickPlaceController(spec)
    command = controller.compute(dt=0.0)

    for _ in range(int(spec.simulation_duration / spec.timestep) + 10):
        command = controller.compute(dt=spec.timestep)
        if command.state is ArmState.OPEN_GRIPPER:
            break

    target_surface_grasp_z = (
        spec.table_height + spec.object_size.z + spec.controller.grasp_height_offset
    )
    expected_release_z = target_surface_grasp_z + spec.controller.release_drop_height

    assert command.state is ArmState.OPEN_GRIPPER
    assert command.gripper_position[2] == expected_release_z
