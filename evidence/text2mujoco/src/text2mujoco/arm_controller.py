"""Scripted IK controller for the robot-arm pick-and-place demo."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

import numpy as np

from text2mujoco.arm_schemas import ArmPosition, ArmSceneSpec


class ArmState(StrEnum):
    """Pick-and-place controller states."""

    RESET = "RESET"
    APPROACH_ABOVE_OBJECT = "APPROACH_ABOVE_OBJECT"
    DESCEND_TO_GRASP = "DESCEND_TO_GRASP"
    CLOSE_GRIPPER = "CLOSE_GRIPPER"
    LIFT_OBJECT = "LIFT_OBJECT"
    MOVE_ABOVE_TARGET = "MOVE_ABOVE_TARGET"
    DESCEND_TO_PLACE = "DESCEND_TO_PLACE"
    OPEN_GRIPPER = "OPEN_GRIPPER"
    RETREAT = "RETREAT"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ArmJointTargets:
    """Joint target command for base, arm, wrist, and fingers."""

    base_yaw: float
    shoulder: float
    elbow: float
    wrist: float
    left_finger: float
    right_finger: float

    @property
    def array(self) -> np.ndarray:
        """Return actuator target array."""

        return np.array(
            [
                self.base_yaw,
                self.shoulder,
                self.elbow,
                self.wrist,
                self.left_finger,
                self.right_finger,
            ],
            dtype=float,
        )


@dataclass(frozen=True)
class ArmCommand:
    """Controller output plus useful high-level state."""

    state: ArmState
    targets: ArmJointTargets
    gripper_position: np.ndarray
    grasp_assist_active: bool
    place_assist_active: bool


def solve_planar_ik(radius: float, z: float, upper: float, forearm: float) -> tuple[float, float]:
    """Solve 2-link planar IK in the radial/Z plane."""

    radius = max(float(radius), 1e-6)
    z = float(z)
    distance = min(max(math.hypot(radius, z), 1e-6), upper + forearm - 1e-5)
    cos_elbow = (distance**2 - upper**2 - forearm**2) / (2.0 * upper * forearm)
    cos_elbow = float(np.clip(cos_elbow, -1.0, 1.0))
    elbow_bend = math.acos(cos_elbow)
    shoulder_plane = math.atan2(z, radius) - math.atan2(
        forearm * math.sin(elbow_bend), upper + forearm * math.cos(elbow_bend)
    )
    return -shoulder_plane, -elbow_bend


class ArmPickPlaceController:
    """Waypoint-driven pick-and-place controller."""

    def __init__(self, spec: ArmSceneSpec) -> None:
        self.spec = spec
        self.state = ArmState.RESET
        self.elapsed = 0.0
        self._sequence = [
            ArmState.APPROACH_ABOVE_OBJECT,
            ArmState.DESCEND_TO_GRASP,
            ArmState.CLOSE_GRIPPER,
            ArmState.LIFT_OBJECT,
            ArmState.MOVE_ABOVE_TARGET,
            ArmState.DESCEND_TO_PLACE,
            ArmState.OPEN_GRIPPER,
            ArmState.RETREAT,
            ArmState.SUCCESS,
        ]

    def compute(self, *, dt: float) -> ArmCommand:
        """Advance the scripted state machine and return joint targets."""

        if self.state is ArmState.RESET:
            self.state = ArmState.APPROACH_ABOVE_OBJECT
            self.elapsed = 0.0
        else:
            self.elapsed += dt
            if self.elapsed >= self._state_duration(self.state):
                self._advance()

        waypoint = self._interpolated_waypoint_for_state(self.state)
        closed = self.state in {
            ArmState.CLOSE_GRIPPER,
            ArmState.LIFT_OBJECT,
            ArmState.MOVE_ABOVE_TARGET,
            ArmState.DESCEND_TO_PLACE,
        }
        return ArmCommand(
            state=self.state,
            targets=self._targets_for_waypoint(waypoint, closed=closed),
            gripper_position=waypoint.array,
            grasp_assist_active=self.state
            in {ArmState.LIFT_OBJECT, ArmState.MOVE_ABOVE_TARGET, ArmState.DESCEND_TO_PLACE},
            place_assist_active=self.state
            in {ArmState.OPEN_GRIPPER, ArmState.RETREAT, ArmState.SUCCESS},
        )

    def _advance(self) -> None:
        index = self._sequence.index(self.state)
        self.state = self._sequence[min(index + 1, len(self._sequence) - 1)]
        self.elapsed = 0.0

    def _state_duration(self, state: ArmState) -> float:
        if state is ArmState.CLOSE_GRIPPER:
            return self.spec.controller.gripper_close_time
        if state in {ArmState.OPEN_GRIPPER, ArmState.RETREAT}:
            return self.spec.controller.place_settle_time
        if state is ArmState.SUCCESS:
            return self.spec.simulation_duration
        return self.spec.controller.state_hold_time

    def _waypoint_for_state(self, state: ArmState) -> ArmPosition:
        spec = self.spec
        object_xy = spec.object_position
        target_xy = spec.target_position
        above_object = ArmPosition(
            x=object_xy.x,
            y=object_xy.y,
            z=spec.table_height + spec.controller.approach_height,
        )
        grasp = ArmPosition(
            x=object_xy.x,
            y=object_xy.y,
            z=spec.table_height + spec.object_size.z + spec.controller.grasp_height_offset,
        )
        lift_object = ArmPosition(x=object_xy.x, y=object_xy.y, z=spec.controller.lift_height)
        above_target = ArmPosition(x=target_xy.x, y=target_xy.y, z=spec.controller.lift_height)
        place = ArmPosition(
            x=target_xy.x,
            y=target_xy.y,
            z=(
                spec.table_height
                + spec.object_size.z
                + spec.controller.grasp_height_offset
                + spec.controller.release_drop_height
            ),
        )
        retreat = ArmPosition(x=target_xy.x - 0.08, y=target_xy.y, z=spec.controller.lift_height)
        mapping = {
            ArmState.APPROACH_ABOVE_OBJECT: above_object,
            ArmState.DESCEND_TO_GRASP: grasp,
            ArmState.CLOSE_GRIPPER: grasp,
            ArmState.LIFT_OBJECT: lift_object,
            ArmState.MOVE_ABOVE_TARGET: above_target,
            ArmState.DESCEND_TO_PLACE: place,
            ArmState.OPEN_GRIPPER: place,
            ArmState.RETREAT: retreat,
            ArmState.SUCCESS: retreat,
            ArmState.FAILED: retreat,
            ArmState.RESET: above_object,
        }
        return mapping[state]

    def _interpolated_waypoint_for_state(self, state: ArmState) -> ArmPosition:
        start, end = self._waypoint_endpoints_for_state(state)
        duration = max(self._state_duration(state), 1e-9)
        alpha = float(np.clip(self.elapsed / duration, 0.0, 1.0))
        eased = alpha * alpha * (3.0 - 2.0 * alpha)
        vector = start.array * (1.0 - eased) + end.array * eased
        return ArmPosition(x=float(vector[0]), y=float(vector[1]), z=float(vector[2]))

    def _waypoint_endpoints_for_state(self, state: ArmState) -> tuple[ArmPosition, ArmPosition]:
        if state is ArmState.DESCEND_TO_GRASP:
            return (
                self._waypoint_for_state(ArmState.APPROACH_ABOVE_OBJECT),
                self._waypoint_for_state(ArmState.DESCEND_TO_GRASP),
            )
        if state is ArmState.LIFT_OBJECT:
            return (
                self._waypoint_for_state(ArmState.DESCEND_TO_GRASP),
                self._waypoint_for_state(ArmState.LIFT_OBJECT),
            )
        if state is ArmState.MOVE_ABOVE_TARGET:
            return (
                self._waypoint_for_state(ArmState.LIFT_OBJECT),
                self._waypoint_for_state(ArmState.MOVE_ABOVE_TARGET),
            )
        if state is ArmState.DESCEND_TO_PLACE:
            return (
                self._waypoint_for_state(ArmState.MOVE_ABOVE_TARGET),
                self._waypoint_for_state(ArmState.DESCEND_TO_PLACE),
            )
        if state is ArmState.RETREAT:
            return (
                self._waypoint_for_state(ArmState.OPEN_GRIPPER),
                self._waypoint_for_state(ArmState.RETREAT),
            )
        waypoint = self._waypoint_for_state(state)
        return waypoint, waypoint

    def _targets_for_waypoint(self, waypoint: ArmPosition, *, closed: bool) -> ArmJointTargets:
        robot = self.spec.robot
        delta = waypoint.array - robot.base_position.array
        base_yaw = math.atan2(delta[1], delta[0])
        horizontal = float(np.linalg.norm(delta[:2])) - robot.wrist_length
        z = waypoint.z - (robot.base_position.z + robot.shoulder_height)
        shoulder, elbow = solve_planar_ik(
            radius=horizontal,
            z=z,
            upper=robot.upper_arm_length,
            forearm=robot.forearm_length,
        )
        wrist = float(np.clip(-(shoulder + elbow), -1.6, 1.6))
        width = robot.gripper_closed_width if closed else robot.gripper_open_width
        finger = width / 2.0
        return ArmJointTargets(
            base_yaw=float(np.clip(base_yaw, -2.7, 2.7)),
            shoulder=float(np.clip(shoulder, -1.4, 1.6)),
            elbow=float(np.clip(elbow, -2.5, 0.2)),
            wrist=wrist,
            left_finger=finger,
            right_finger=finger,
        )
