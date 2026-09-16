"""Strict Pydantic scene schema for the push-world generator."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Self

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "1.0"


def _ensure_finite(value: float, field_name: str) -> float:
    if not math.isfinite(value):
        msg = f"{field_name} must be finite"
        raise ValueError(msg)
    return float(value)


class Vec2(BaseModel):
    """Two-dimensional SI coordinate in meters."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    x: float = Field(ge=-1.6, le=1.6, description="X coordinate in meters.")
    y: float = Field(ge=-1.6, le=1.6, description="Y coordinate in meters.")

    @model_validator(mode="before")
    @classmethod
    def parse_sequence(cls, value: Any) -> Any:
        if isinstance(value, cls):
            return value
        if isinstance(value, (list, tuple)):
            if len(value) != 2:
                msg = "Vec2 requires exactly two values"
                raise ValueError(msg)
            return {"x": value[0], "y": value[1]}
        return value

    @field_validator("x", "y")
    @classmethod
    def finite(cls, value: float) -> float:
        return _ensure_finite(value, "Vec2 coordinate")

    @property
    def array(self) -> np.ndarray:
        """Return the vector as a NumPy array."""

        return np.array([self.x, self.y], dtype=float)

    def distance_to(self, other: Vec2) -> float:
        """Euclidean distance to another 2D point."""

        return float(np.linalg.norm(self.array - other.array))


class Vec3(BaseModel):
    """Three-dimensional size vector in meters."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    x: float = Field(ge=0.05, le=0.2, description="Full X dimension in meters.")
    y: float = Field(ge=0.05, le=0.2, description="Full Y dimension in meters.")
    z: float = Field(ge=0.05, le=0.2, description="Full Z dimension in meters.")

    @model_validator(mode="before")
    @classmethod
    def parse_sequence(cls, value: Any) -> Any:
        if isinstance(value, cls):
            return value
        if isinstance(value, (list, tuple)):
            if len(value) != 3:
                msg = "Vec3 requires exactly three values"
                raise ValueError(msg)
            return {"x": value[0], "y": value[1], "z": value[2]}
        return value

    @field_validator("x", "y", "z")
    @classmethod
    def finite(cls, value: float) -> float:
        return _ensure_finite(value, "Vec3 dimension")

    @property
    def array(self) -> np.ndarray:
        """Return the vector as a NumPy array."""

        return np.array([self.x, self.y, self.z], dtype=float)


class RgbColor(BaseModel):
    """RGBA color with normalized channels."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    r: float = Field(ge=0.0, le=1.0)
    g: float = Field(ge=0.0, le=1.0)
    b: float = Field(ge=0.0, le=1.0)
    a: float = Field(default=1.0, ge=0.0, le=1.0)

    @model_validator(mode="before")
    @classmethod
    def parse_sequence(cls, value: Any) -> Any:
        if isinstance(value, cls):
            return value
        if isinstance(value, (list, tuple)):
            if len(value) not in {3, 4}:
                msg = "RgbColor requires three or four values"
                raise ValueError(msg)
            keys = ("r", "g", "b", "a")
            return dict(zip(keys, value, strict=False))
        return value

    @field_validator("r", "g", "b", "a")
    @classmethod
    def finite(cls, value: float) -> float:
        return _ensure_finite(value, "color channel")

    def rgba_string(self) -> str:
        """Return MuJoCo-compatible RGBA text."""

        return f"{self.r:.4g} {self.g:.4g} {self.b:.4g} {self.a:.4g}"


class ControllerConfig(BaseModel):
    """Rule-based controller and actuator settings."""

    model_config = ConfigDict(extra="forbid")

    pusher_radius: float = Field(default=0.045, ge=0.025, le=0.08)
    pusher_height: float = Field(default=0.12, ge=0.06, le=0.2)
    pusher_clearance: float = Field(default=0.025, ge=0.005, le=0.08)
    control_hz: float = Field(default=60.0, ge=10.0, le=240.0)
    max_force: float = Field(default=12.0, ge=5.0, le=250.0)
    approach_tolerance: float = Field(default=0.035, ge=0.005, le=0.08)
    push_target_overshoot: float = Field(default=0.07, ge=0.02, le=0.2)
    maximum_speed: float = Field(default=8.0, ge=0.5, le=10.0)

    @field_validator(
        "pusher_radius",
        "pusher_height",
        "pusher_clearance",
        "control_hz",
        "max_force",
        "approach_tolerance",
        "push_target_overshoot",
        "maximum_speed",
    )
    @classmethod
    def finite(cls, value: float) -> float:
        return _ensure_finite(value, "controller parameter")


class SceneSpec(BaseModel):
    """Validated data contract produced by the LLM and consumed by the MJCF builder."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    schema_version: str = Field(default=SCHEMA_VERSION, description="SceneSpec schema version.")
    seed: int = Field(default=7, ge=0, le=2_147_483_647)
    task_description: str = Field(min_length=1, max_length=500)
    arena_half_size: float = Field(default=1.2, ge=0.9, le=1.5)
    box_position: Vec2
    box_size: Vec3
    box_mass: float = Field(default=0.4, ge=0.1, le=2.0)
    target_position: Vec2
    target_radius: float = Field(default=0.16, ge=0.1, le=0.25)
    floor_friction: float = Field(default=0.35, ge=0.2, le=1.5)
    simulation_duration: float = Field(default=8.0, ge=0.02, le=20.0)
    success_hold_time: float = Field(default=0.12, ge=0.02, le=2.0)
    timestep: float = Field(default=0.002, ge=0.001, le=0.01)
    box_color: RgbColor = Field(default_factory=lambda: RgbColor(r=0.86, g=0.08, b=0.06))
    target_color: RgbColor = Field(default_factory=lambda: RgbColor(r=0.1, g=0.65, b=0.18, a=0.45))
    pusher_color: RgbColor = Field(default_factory=lambda: RgbColor(r=0.1, g=0.2, b=0.9))
    controller: ControllerConfig = Field(default_factory=ControllerConfig)

    @field_validator("schema_version")
    @classmethod
    def version_is_supported(cls, value: str) -> str:
        if value != SCHEMA_VERSION:
            msg = f"schema_version must be {SCHEMA_VERSION}"
            raise ValueError(msg)
        return value

    @field_validator(
        "arena_half_size",
        "box_mass",
        "target_radius",
        "floor_friction",
        "simulation_duration",
        "success_hold_time",
        "timestep",
    )
    @classmethod
    def finite(cls, value: float) -> float:
        return _ensure_finite(value, "SceneSpec numeric value")

    def to_json_file(self, path: Path) -> None:
        """Write the spec as UTF-8 JSON."""

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def from_json_file(cls, path: Path) -> Self:
        """Load a SceneSpec from UTF-8 JSON."""

        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls.model_validate(payload)


def baseline_scene() -> SceneSpec:
    """Return a deterministic baseline scene that does not require the OpenAI API."""

    return SceneSpec(
        schema_version=SCHEMA_VERSION,
        seed=7,
        task_description="Push the red box to the green target on a slightly slippery floor.",
        arena_half_size=1.2,
        box_position=Vec2(x=0.0, y=0.0),
        box_size=Vec3(x=0.12, y=0.12, z=0.1),
        box_mass=0.35,
        target_position=Vec2(x=0.55, y=0.0),
        target_radius=0.16,
        floor_friction=0.28,
        simulation_duration=8.0,
        success_hold_time=0.12,
        timestep=0.002,
        box_color=RgbColor(r=0.86, g=0.08, b=0.06, a=1.0),
        target_color=RgbColor(r=0.1, g=0.7, b=0.18, a=0.5),
        pusher_color=RgbColor(r=0.1, g=0.22, b=0.9, a=1.0),
        controller=ControllerConfig(),
    )


def load_scene_spec(path: Path) -> SceneSpec:
    """Load and validate a SceneSpec JSON file."""

    return SceneSpec.from_json_file(path)
