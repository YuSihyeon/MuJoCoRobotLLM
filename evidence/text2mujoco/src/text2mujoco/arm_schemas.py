"""Strict scene schema for the robot-arm pick-and-place demo."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Literal, Self

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from text2mujoco.schemas import RgbColor, Vec3

ARM_SCHEMA_VERSION = "1.0"
ArmObjectShape = Literal["box", "cylinder", "sphere"]


def _finite(value: float, field_name: str) -> float:
    if not math.isfinite(value):
        msg = f"{field_name} must be finite"
        raise ValueError(msg)
    return float(value)


class ArmPosition(BaseModel):
    """3D SI position for tabletop manipulation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    x: float = Field(ge=-1.5, le=1.5)
    y: float = Field(ge=-1.5, le=1.5)
    z: float = Field(ge=0.0, le=1.2)

    @model_validator(mode="before")
    @classmethod
    def parse_sequence(cls, value: Any) -> Any:
        if isinstance(value, cls):
            return value
        if isinstance(value, (list, tuple)):
            if len(value) != 3:
                msg = "ArmPosition requires exactly three values"
                raise ValueError(msg)
            return {"x": value[0], "y": value[1], "z": value[2]}
        return value

    @field_validator("x", "y", "z")
    @classmethod
    def finite(cls, value: float) -> float:
        return _finite(value, "ArmPosition coordinate")

    @property
    def array(self) -> np.ndarray:
        """Return as NumPy XYZ array."""

        return np.array([self.x, self.y, self.z], dtype=float)

    def distance_xy_to(self, other: ArmPosition) -> float:
        """XY distance to another position."""

        return float(np.linalg.norm(self.array[:2] - other.array[:2]))


class ArmSize3(BaseModel):
    """3D size for table-scale objects."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    x: float = Field(ge=0.05, le=2.0)
    y: float = Field(ge=0.05, le=2.0)
    z: float = Field(ge=0.02, le=0.5)

    @model_validator(mode="before")
    @classmethod
    def parse_sequence(cls, value: Any) -> Any:
        if isinstance(value, cls):
            return value
        if isinstance(value, (list, tuple)):
            if len(value) != 3:
                msg = "ArmSize3 requires exactly three values"
                raise ValueError(msg)
            return {"x": value[0], "y": value[1], "z": value[2]}
        return value

    @field_validator("x", "y", "z")
    @classmethod
    def finite(cls, value: float) -> float:
        return _finite(value, "ArmSize3 dimension")


class RobotArmConfig(BaseModel):
    """Simple 4-DOF arm and two-finger gripper dimensions/settings."""

    model_config = ConfigDict(extra="forbid")

    base_position: ArmPosition = Field(default_factory=lambda: ArmPosition(x=-0.35, y=0.0, z=0.08))
    shoulder_height: float = Field(default=0.18, ge=0.08, le=0.4)
    upper_arm_length: float = Field(default=0.34, ge=0.2, le=0.6)
    forearm_length: float = Field(default=0.30, ge=0.2, le=0.6)
    wrist_length: float = Field(default=0.08, ge=0.03, le=0.16)
    gripper_open_width: float = Field(default=0.11, ge=0.06, le=0.18)
    gripper_closed_width: float = Field(default=0.035, ge=0.015, le=0.06)
    max_joint_speed: float = Field(default=2.2, ge=0.3, le=6.0)
    max_force: float = Field(default=140.0, ge=10.0, le=250.0)

    @field_validator(
        "shoulder_height",
        "upper_arm_length",
        "forearm_length",
        "wrist_length",
        "gripper_open_width",
        "gripper_closed_width",
        "max_joint_speed",
        "max_force",
    )
    @classmethod
    def finite(cls, value: float) -> float:
        return _finite(value, "robot arm parameter")


class ArmControllerConfig(BaseModel):
    """Timing and waypoint settings for scripted pick-and-place."""

    model_config = ConfigDict(extra="forbid")

    approach_height: float = Field(default=0.32, ge=0.12, le=0.45)
    grasp_height_offset: float = Field(default=0.035, ge=0.015, le=0.08)
    lift_height: float = Field(default=0.42, ge=0.2, le=0.55)
    release_drop_height: float = Field(default=0.035, ge=0.01, le=0.08)
    state_hold_time: float = Field(default=0.7, ge=0.04, le=2.0)
    gripper_close_time: float = Field(default=0.7, ge=0.08, le=2.0)
    place_settle_time: float = Field(default=0.55, ge=0.05, le=2.0)

    @field_validator(
        "approach_height",
        "grasp_height_offset",
        "lift_height",
        "release_drop_height",
        "state_hold_time",
        "gripper_close_time",
        "place_settle_time",
    )
    @classmethod
    def finite(cls, value: float) -> float:
        return _finite(value, "arm controller parameter")


class ArmStaticProp(BaseModel):
    """Validated static object rendered into the tabletop scene."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=48, pattern=r"^[A-Za-z0-9_]+$")
    shape: ArmObjectShape = "box"
    position: ArmPosition
    size: ArmSize3
    color: RgbColor = Field(default_factory=lambda: RgbColor(r=0.42, g=0.44, b=0.48))
    collision: bool = True


class ArmSceneSpec(BaseModel):
    """Validated scene contract for the robot arm demo."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    schema_version: str = Field(default=ARM_SCHEMA_VERSION)
    seed: int = Field(default=11, ge=0, le=2_147_483_647)
    task_description: str = Field(min_length=1, max_length=500)
    table_size: ArmSize3 = Field(default_factory=lambda: ArmSize3(x=0.9, y=0.7, z=0.08))
    table_height: float = Field(default=0.08, ge=0.04, le=0.2)
    object_position: ArmPosition = Field(
        default_factory=lambda: ArmPosition(x=0.18, y=-0.12, z=0.13)
    )
    object_shape: ArmObjectShape = "box"
    object_size: Vec3 = Field(default_factory=lambda: Vec3(x=0.07, y=0.07, z=0.07))
    object_mass: float = Field(default=0.12, ge=0.03, le=1.0)
    target_position: ArmPosition = Field(
        default_factory=lambda: ArmPosition(x=0.22, y=0.18, z=0.08)
    )
    target_radius: float = Field(default=0.08, ge=0.04, le=0.18)
    floor_friction: float = Field(default=0.8, ge=0.2, le=1.5)
    timestep: float = Field(default=0.002, ge=0.001, le=0.01)
    simulation_duration: float = Field(default=8.0, ge=2.0, le=30.0)
    robot: RobotArmConfig = Field(default_factory=RobotArmConfig)
    controller: ArmControllerConfig = Field(default_factory=ArmControllerConfig)
    static_props: tuple[ArmStaticProp, ...] = Field(default_factory=tuple)
    object_color: RgbColor = Field(default_factory=lambda: RgbColor(r=0.88, g=0.18, b=0.12))
    target_color: RgbColor = Field(default_factory=lambda: RgbColor(r=0.1, g=0.68, b=0.24, a=0.45))
    arm_color: RgbColor = Field(default_factory=lambda: RgbColor(r=0.18, g=0.28, b=0.78))

    @field_validator("schema_version")
    @classmethod
    def version_is_supported(cls, value: str) -> str:
        if value != ARM_SCHEMA_VERSION:
            msg = f"schema_version must be {ARM_SCHEMA_VERSION}"
            raise ValueError(msg)
        return value

    @field_validator(
        "table_height",
        "object_mass",
        "target_radius",
        "floor_friction",
        "timestep",
        "simulation_duration",
    )
    @classmethod
    def finite(cls, value: float) -> float:
        return _finite(value, "ArmSceneSpec numeric value")

    @model_validator(mode="after")
    def semantic_ranges(self) -> Self:
        """Reject unreachable or physically awkward first-version scenes."""

        table_half_x = self.table_size.x / 2.0
        table_half_y = self.table_size.y / 2.0
        margin = max(self.object_size.x, self.object_size.y) / 2.0
        for label, point, extra in [
            ("object", self.object_position, margin),
            ("target", self.target_position, self.target_radius),
        ]:
            if abs(point.x) + extra > table_half_x or abs(point.y) + extra > table_half_y:
                msg = f"{label} must fit on the table"
                raise ValueError(msg)
        if self.object_position.distance_xy_to(self.target_position) <= self.target_radius:
            msg = "object and target must not start in a success state"
            raise ValueError(msg)
        for prop in self.static_props:
            if (
                abs(prop.position.x) + prop.size.x / 2.0 > table_half_x
                or abs(prop.position.y) + prop.size.y / 2.0 > table_half_y
            ):
                msg = f"static prop {prop.name} must fit on the table"
                raise ValueError(msg)

        max_reach = (
            self.robot.upper_arm_length + self.robot.forearm_length + self.robot.wrist_length
        )
        for label, point in [("object", self.object_position), ("target", self.target_position)]:
            horizontal = float(np.linalg.norm(point.array[:2] - self.robot.base_position.array[:2]))
            vertical = abs((point.z + self.controller.approach_height) - self.robot.shoulder_height)
            if math.hypot(horizontal, vertical) > max_reach * 0.95:
                msg = f"{label} is outside the robot arm reachable workspace"
                raise ValueError(msg)
        return self

    def to_json_file(self, path: Path) -> None:
        """Write the arm scene as UTF-8 JSON."""

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def from_json_file(cls, path: Path) -> Self:
        """Load an ArmSceneSpec from UTF-8 JSON."""

        return cls.model_validate(json.loads(path.read_text(encoding="utf-8")))


def baseline_arm_scene() -> ArmSceneSpec:
    """Return a deterministic robot-arm pick-and-place scene."""

    return ArmSceneSpec(
        task_description=(
            "Pick up the red cube with a simple robot arm and place it on the green target."
        ),
    )


def load_arm_scene_spec(path: Path) -> ArmSceneSpec:
    """Load a robot-arm scene spec from JSON."""

    return ArmSceneSpec.from_json_file(path)
