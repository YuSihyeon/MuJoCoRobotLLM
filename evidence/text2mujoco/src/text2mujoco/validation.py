"""Semantic and physical validation for SceneSpec objects."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from text2mujoco.errors import MJCFBuildError, SceneValidationError, SimulationStabilityError
from text2mujoco.schemas import SceneSpec, Vec2


@dataclass(frozen=True)
class ValidationReport:
    """Summary of successful semantic validation."""

    issues: list[str]
    pusher_start: Vec2


def normalize_xy(vector: np.ndarray) -> np.ndarray:
    """Normalize a 2D vector, raising for near-zero length."""

    norm = float(np.linalg.norm(vector))
    if norm < 1e-9:
        msg = "box and target positions must be separated"
        raise SceneValidationError([msg])
    return vector / norm


def _coerce_spec(spec: SceneSpec) -> SceneSpec:
    payload = {field_name: getattr(spec, field_name) for field_name in SceneSpec.model_fields}
    return SceneSpec.model_validate(payload)


def box_support_radius(spec: SceneSpec, direction: np.ndarray) -> float:
    """Return AABB support distance from box center along a unit direction."""

    half_x = spec.box_size.x / 2.0
    half_y = spec.box_size.y / 2.0
    return float(abs(direction[0]) * half_x + abs(direction[1]) * half_y)


def compute_pusher_start(spec: SceneSpec) -> Vec2:
    """Compute a safe point behind the box, opposite the target direction."""

    spec = _coerce_spec(spec)
    direction = normalize_xy(spec.target_position.array - spec.box_position.array)
    offset = (
        box_support_radius(spec, direction)
        + spec.controller.pusher_radius
        + spec.controller.pusher_clearance
    )
    start = spec.box_position.array - direction * offset
    return Vec2(x=float(start[0]), y=float(start[1]))


def _within_arena(point: Vec2, spec: SceneSpec, margin: float = 0.0) -> bool:
    limit = spec.arena_half_size - margin
    return -limit <= point.x <= limit and -limit <= point.y <= limit


def validate_scene(spec: SceneSpec, *, include_mujoco: bool = True) -> ValidationReport:
    """Validate spatial relationships, physical plausibility, and optional MuJoCo stability."""

    spec = _coerce_spec(spec)
    issues: list[str] = []
    half = spec.arena_half_size
    half_box_x = spec.box_size.x / 2.0
    half_box_y = spec.box_size.y / 2.0

    if abs(spec.box_position.x) + half_box_x > half or abs(spec.box_position.y) + half_box_y > half:
        issues.append("box must fit completely inside the arena")

    if (
        abs(spec.target_position.x) + spec.target_radius > half
        or abs(spec.target_position.y) + spec.target_radius > half
    ):
        issues.append("target region must fit completely inside the arena")

    box_target_distance = spec.box_position.distance_to(spec.target_position)
    minimum_meaningful_distance = spec.target_radius + max(spec.box_size.x, spec.box_size.y)
    if box_target_distance <= spec.target_radius:
        issues.append("box and target begin in a success state")
    if box_target_distance < minimum_meaningful_distance:
        issues.append("box and target are too close for a meaningful push task")

    try:
        pusher_start = compute_pusher_start(spec)
    except SceneValidationError as exc:
        issues.extend(exc.issues)
        pusher_start = Vec2(x=0.0, y=0.0)

    if not _within_arena(pusher_start, spec, margin=spec.controller.pusher_radius):
        issues.append("pusher start position must be inside the arena")

    pusher_box_distance = pusher_start.distance_to(spec.box_position)
    if pusher_box_distance <= spec.controller.pusher_radius + min(half_box_x, half_box_y) * 0.75:
        issues.append("pusher start position must not overlap the box")

    if box_target_distance > 0.0:
        direction = normalize_xy(spec.target_position.array - spec.box_position.array)
        final_pusher = spec.target_position.array + direction * (
            box_support_radius(spec, direction) + spec.controller.pusher_radius
        )
        final_point = Vec2(x=float(final_pusher[0]), y=float(final_pusher[1]))
        if not _within_arena(final_point, spec, margin=spec.controller.pusher_radius):
            issues.append("pusher expected final position must stay inside actuator range")

        start_vector = spec.box_position.array - pusher_start.array
        if float(np.dot(start_vector, direction)) <= 0.0:
            issues.append("pusher must start behind the box, opposite the target")

    required_force = spec.box_mass * 9.81 * spec.floor_friction * 1.15
    if spec.controller.max_force < required_force:
        issues.append("controller max force is too low for box mass and floor friction")

    if issues:
        raise SceneValidationError(issues)

    if include_mujoco:
        try:
            from text2mujoco.mjcf_builder import MJCFBuilder
            from text2mujoco.simulation import compile_model, step_finite

            model, data = compile_model(MJCFBuilder().build(spec))
            step_finite(model, data, steps=20)
        except (MJCFBuildError, SimulationStabilityError) as exc:
            raise SceneValidationError([str(exc)]) from exc

    return ValidationReport(issues=[], pusher_start=pusher_start)
