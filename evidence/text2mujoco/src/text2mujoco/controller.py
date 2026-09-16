"""Deterministic rule-based pusher controller."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np

from text2mujoco.schemas import SceneSpec
from text2mujoco.validation import box_support_radius, compute_pusher_start

type Observation = dict[str, list[float]]


class ControllerState(StrEnum):
    """Controller state-machine states."""

    INITIALIZE = "INITIALIZE"
    APPROACH = "APPROACH"
    ALIGN = "ALIGN"
    PUSH = "PUSH"
    HOLD = "HOLD"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


def normalize(vector: np.ndarray) -> np.ndarray:
    """Return a unit vector, falling back to +X for near-zero input."""

    norm = float(np.linalg.norm(vector))
    if norm < 1e-9:
        return np.array([1.0, 0.0], dtype=float)
    return vector / norm


def saturate(action: np.ndarray, spec: SceneSpec) -> np.ndarray:
    """Clamp XY actuator targets to the configured slide-joint range."""

    return np.clip(action, -spec.arena_half_size, spec.arena_half_size)


@dataclass
class PushController:
    """State-machine controller that approaches, aligns, pushes, and holds success."""

    spec: SceneSpec
    state: ControllerState = ControllerState.INITIALIZE
    success_hold_elapsed: float = 0.0

    def compute_action(self, observation: Observation, simulation_time: float) -> np.ndarray:
        """Compute the next XY position-actuator target."""

        del simulation_time
        pusher = np.array(observation["pusher_position"], dtype=float)
        box = np.array(observation["box_position"], dtype=float)
        target = np.array(observation["target_position"], dtype=float)
        direction = normalize(target - box)
        behind = compute_pusher_start(self.spec).array
        support = box_support_radius(self.spec, direction)
        contact_ready = box - direction * (support + self.spec.controller.pusher_radius * 0.55)
        distance_to_target = float(np.linalg.norm(target - box))

        if self.state is ControllerState.INITIALIZE:
            self.state = ControllerState.APPROACH

        if distance_to_target <= self.spec.target_radius:
            self.state = ControllerState.HOLD
            hold_action = box - direction * (support + self.spec.controller.pusher_radius * 0.55)
            return saturate(hold_action, self.spec)

        if self.state is ControllerState.APPROACH:
            if float(np.linalg.norm(pusher - behind)) > self.spec.controller.approach_tolerance:
                return saturate(behind, self.spec)
            self.state = ControllerState.ALIGN

        if self.state is ControllerState.ALIGN:
            if (
                float(np.linalg.norm(pusher - contact_ready))
                > self.spec.controller.approach_tolerance
            ):
                return saturate(contact_ready, self.spec)
            self.state = ControllerState.PUSH

        push_goal = (
            target
            - direction * (support + self.spec.controller.pusher_radius * 0.55)
            + direction * self.spec.controller.push_target_overshoot
        )
        return saturate(push_goal, self.spec)

    def update_success_hold(self, inside_target: bool, dt: float) -> bool:
        """Return True after the target condition is held continuously long enough."""

        if inside_target:
            self.success_hold_elapsed += dt
        else:
            self.success_hold_elapsed = 0.0
            if self.state is ControllerState.HOLD:
                self.state = ControllerState.PUSH

        if self.success_hold_elapsed >= self.spec.success_hold_time:
            self.state = ControllerState.SUCCESS
            return True
        return False
