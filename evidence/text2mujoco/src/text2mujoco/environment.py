"""Small RL-friendly environment wrapper around the MuJoCo push world."""

from __future__ import annotations

from dataclasses import dataclass

import mujoco
import numpy as np

from text2mujoco.mjcf_builder import MJCFBuilder
from text2mujoco.schemas import SceneSpec
from text2mujoco.simulation import (
    ModelHandles,
    body_xy,
    compile_model,
    initialize_state,
    make_observation,
    resolve_handles,
)


@dataclass
class StepResult:
    """Gymnasium-shaped step result without requiring Gymnasium."""

    observation: dict[str, list[float]]
    reward: float
    terminated: bool
    truncated: bool
    info: dict[str, object]


class PushEnvironment:
    """MuJoCo environment with reset, step, observation, reward, and termination hooks."""

    def __init__(self, spec: SceneSpec) -> None:
        self.spec = spec
        self.model, self.data = compile_model(MJCFBuilder().build(spec))
        self.handles: ModelHandles = resolve_handles(self.model)
        self.previous_distance = 0.0

    def reset(self, seed: int | None = None) -> dict[str, list[float]]:
        """Reset MuJoCo state and return an observation."""

        if seed is not None:
            np.random.seed(seed)
        initialize_state(self.model, self.data, self.spec, self.handles)
        self.previous_distance = self._distance()
        return self.get_observation()

    def step(self, action: np.ndarray) -> StepResult:
        """Apply an XY actuator target and step one physics tick."""

        clipped = np.clip(action, -self.spec.arena_half_size, self.spec.arena_half_size)
        self.data.ctrl[self.handles.move_x_actuator] = float(clipped[0])
        self.data.ctrl[self.handles.move_y_actuator] = float(clipped[1])
        mujoco.mj_step(self.model, self.data)
        observation = self.get_observation()
        reward = self.compute_reward(action=clipped)
        terminated, truncated, reason = self.check_termination()
        return StepResult(
            observation=observation,
            reward=reward,
            terminated=terminated,
            truncated=truncated,
            info={"termination_reason": reason},
        )

    def get_observation(self) -> dict[str, list[float]]:
        """Return the current observation."""

        return make_observation(self.data, self.handles, self.spec)

    def compute_reward(self, *, action: np.ndarray) -> float:
        """Reward progress toward target while mildly penalizing large actions."""

        distance = self._distance()
        progress = self.previous_distance - distance
        self.previous_distance = distance
        action_penalty = 0.002 * float(np.linalg.norm(action))
        success_bonus = 1.0 if distance <= self.spec.target_radius else 0.0
        return progress - action_penalty + success_bonus

    def check_termination(self) -> tuple[bool, bool, str]:
        """Return terminated, truncated, and a reason string."""

        if self._distance() <= self.spec.target_radius:
            return True, False, "success"
        if self.data.time >= self.spec.simulation_duration:
            return False, True, "time_limit"
        box_position = body_xy(self.data, self.handles.box_body)
        if np.any(np.abs(box_position) > self.spec.arena_half_size + 0.05):
            return True, False, "box_outside_arena"
        return False, False, "running"

    def close(self) -> None:
        """Release environment resources."""

    def _distance(self) -> float:
        box_position = body_xy(self.data, self.handles.box_body)
        return float(np.linalg.norm(self.spec.target_position.array - box_position))
