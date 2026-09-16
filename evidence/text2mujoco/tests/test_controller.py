from __future__ import annotations

import numpy as np

from text2mujoco.controller import ControllerState, PushController, normalize, saturate
from text2mujoco.schemas import baseline_scene


def test_normalize_returns_unit_direction() -> None:
    vector = normalize(np.array([3.0, 4.0]))

    assert np.allclose(vector, np.array([0.6, 0.8]))


def test_saturate_clamps_to_actuator_range() -> None:
    spec = baseline_scene()
    action = saturate(np.array([9.0, -9.0]), spec)

    assert action[0] == spec.arena_half_size
    assert action[1] == -spec.arena_half_size


def test_controller_initial_action_moves_to_behind_point() -> None:
    spec = baseline_scene()
    controller = PushController(spec)
    observation = {
        "pusher_position": [-0.6, 0.0],
        "pusher_velocity": [0.0, 0.0],
        "box_position": [spec.box_position.x, spec.box_position.y],
        "box_velocity": [0.0, 0.0],
        "target_position": [spec.target_position.x, spec.target_position.y],
        "box_to_target": [0.0, 0.0],
        "pusher_to_box": [0.0, 0.0],
    }

    action = controller.compute_action(observation, simulation_time=0.0)

    assert controller.state in {ControllerState.APPROACH, ControllerState.ALIGN}
    assert action[0] < spec.box_position.x


def test_success_hold_time_requires_continuous_hold() -> None:
    spec = baseline_scene()
    controller = PushController(spec)

    assert controller.update_success_hold(True, dt=spec.success_hold_time / 2) is False
    assert controller.update_success_hold(False, dt=0.01) is False
    assert controller.update_success_hold(True, dt=spec.success_hold_time) is True
