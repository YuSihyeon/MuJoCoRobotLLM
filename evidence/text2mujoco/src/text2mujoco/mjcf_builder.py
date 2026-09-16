"""Deterministic MJCF XML builder for validated push-world scenes."""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET

from text2mujoco.errors import MJCFBuildError
from text2mujoco.schemas import SceneSpec

GENERATOR_VERSION = "text2mujoco-0.1.0"


class ModelNames:
    """Named MJCF contract used by simulation and tests."""

    PUSHER = "pusher"
    PUSHER_X = "pusher_x"
    PUSHER_Y = "pusher_y"
    MOVE_X = "move_x"
    MOVE_Y = "move_y"
    BOX = "box"
    BOX_FREE = "box_free"
    TARGET = "target"


def _fmt(value: float) -> str:
    return f"{value:.8g}"


def _v(*values: float) -> str:
    return " ".join(_fmt(value) for value in values)


class MJCFBuilder:
    """Build safe MJCF from a validated SceneSpec without using LLM XML."""

    def build(self, spec: SceneSpec) -> str:
        """Return a deterministic MJCF XML string."""

        try:
            spec_hash = hashlib.sha256(
                spec.model_dump_json(round_trip=True).encode("utf-8")
            ).hexdigest()[:12]
            root = ET.Element("mujoco", {"model": f"text2mujoco_push_world_{spec_hash}"})
            root.append(
                ET.Comment(
                    f"generator={GENERATOR_VERSION}; schema={spec.schema_version}; "
                    f"seed={spec.seed}; "
                    f"run_id={spec_hash}"
                )
            )
            ET.SubElement(root, "compiler", {"angle": "radian", "coordinate": "local"})
            ET.SubElement(
                root,
                "option",
                {
                    "gravity": "0 0 -9.81",
                    "timestep": _fmt(spec.timestep),
                    "integrator": "implicitfast",
                    "cone": "elliptic",
                },
            )
            ET.SubElement(root, "size", {"njmax": "2000", "nconmax": "200"})
            self._add_defaults(root, spec)
            self._add_assets(root, spec)
            self._add_worldbody(root, spec)
            self._add_actuators(root, spec)
            ET.indent(root, space="  ")
            xml = ET.tostring(root, encoding="unicode")
        except Exception as exc:  # noqa: BLE001 - wrapped as project error
            raise MJCFBuildError(f"failed to build MJCF: {exc}") from exc
        return xml

    def _add_defaults(self, root: ET.Element, spec: SceneSpec) -> None:
        default = ET.SubElement(root, "default")
        ET.SubElement(
            default,
            "geom",
            {
                "condim": "3",
                "friction": _v(spec.floor_friction, 0.005, 0.0001),
                "solref": "0.012 1",
                "solimp": "0.9 0.95 0.001",
            },
        )
        ET.SubElement(default, "joint", {"damping": "3.0", "armature": "0.01"})

    def _add_assets(self, root: ET.Element, spec: SceneSpec) -> None:
        asset = ET.SubElement(root, "asset")
        ET.SubElement(asset, "material", {"name": "floor_mat", "rgba": "0.55 0.58 0.56 1"})
        ET.SubElement(asset, "material", {"name": "wall_mat", "rgba": "0.28 0.28 0.3 1"})
        ET.SubElement(asset, "material", {"name": "box_mat", "rgba": spec.box_color.rgba_string()})
        ET.SubElement(
            asset, "material", {"name": "target_mat", "rgba": spec.target_color.rgba_string()}
        )
        ET.SubElement(
            asset, "material", {"name": "pusher_mat", "rgba": spec.pusher_color.rgba_string()}
        )

    def _add_worldbody(self, root: ET.Element, spec: SceneSpec) -> None:
        world = ET.SubElement(root, "worldbody")
        ET.SubElement(world, "light", {"name": "key_light", "pos": "0 -2 3", "dir": "0 1 -1"})
        ET.SubElement(
            world,
            "camera",
            {
                "name": "overview",
                "pos": _v(0.0, -2.8, 2.1),
                "xyaxes": "1 0 0 0 0.62 0.78",
            },
        )
        ET.SubElement(
            world,
            "geom",
            {
                "name": "floor",
                "type": "plane",
                "size": _v(spec.arena_half_size, spec.arena_half_size, 0.02),
                "material": "floor_mat",
                "friction": _v(spec.floor_friction, 0.005, 0.0001),
            },
        )
        self._add_walls(world, spec)
        self._add_target(world, spec)
        self._add_pusher(world, spec)
        self._add_box(world, spec)

    def _add_walls(self, world: ET.Element, spec: SceneSpec) -> None:
        half = spec.arena_half_size
        thickness = 0.035
        wall_height = 0.12
        walls = [
            ("wall_north", 0.0, half + thickness, half + thickness, thickness),
            ("wall_south", 0.0, -half - thickness, half + thickness, thickness),
            ("wall_east", half + thickness, 0.0, thickness, half + thickness),
            ("wall_west", -half - thickness, 0.0, thickness, half + thickness),
        ]
        for name, x, y, sx, sy in walls:
            ET.SubElement(
                world,
                "geom",
                {
                    "name": name,
                    "type": "box",
                    "pos": _v(x, y, wall_height / 2.0),
                    "size": _v(sx, sy, wall_height / 2.0),
                    "material": "wall_mat",
                },
            )

    def _add_target(self, world: ET.Element, spec: SceneSpec) -> None:
        target = ET.SubElement(
            world,
            "body",
            {
                "name": ModelNames.TARGET,
                "pos": _v(spec.target_position.x, spec.target_position.y, 0.006),
            },
        )
        ET.SubElement(
            target,
            "geom",
            {
                "name": "target_visual",
                "type": "cylinder",
                "size": _v(spec.target_radius, 0.006),
                "material": "target_mat",
                "contype": "0",
                "conaffinity": "0",
            },
        )

    def _add_pusher(self, world: ET.Element, spec: SceneSpec) -> None:
        pusher_z = spec.controller.pusher_height / 2.0
        root_body = ET.SubElement(
            world, "body", {"name": "pusher_x_body", "pos": _v(0, 0, pusher_z)}
        )
        ET.SubElement(
            root_body,
            "inertial",
            {
                "pos": "0 0 0",
                "mass": "0.05",
                "diaginertia": "0.0001 0.0001 0.0001",
            },
        )
        ET.SubElement(
            root_body,
            "joint",
            {
                "name": ModelNames.PUSHER_X,
                "type": "slide",
                "axis": "1 0 0",
                "limited": "true",
                "range": _v(-spec.arena_half_size, spec.arena_half_size),
            },
        )
        pusher_body = ET.SubElement(root_body, "body", {"name": ModelNames.PUSHER, "pos": "0 0 0"})
        ET.SubElement(
            pusher_body,
            "joint",
            {
                "name": ModelNames.PUSHER_Y,
                "type": "slide",
                "axis": "0 1 0",
                "limited": "true",
                "range": _v(-spec.arena_half_size, spec.arena_half_size),
            },
        )
        ET.SubElement(
            pusher_body,
            "geom",
            {
                "name": "pusher_collision",
                "type": "cylinder",
                "size": _v(spec.controller.pusher_radius, spec.controller.pusher_height / 2.0),
                "mass": "1.0",
                "material": "pusher_mat",
                "friction": _v(spec.floor_friction, 0.005, 0.0001),
            },
        )

    def _add_box(self, world: ET.Element, spec: SceneSpec) -> None:
        box = ET.SubElement(
            world,
            "body",
            {
                "name": ModelNames.BOX,
                "pos": _v(spec.box_position.x, spec.box_position.y, spec.box_size.z / 2.0),
            },
        )
        ET.SubElement(box, "freejoint", {"name": ModelNames.BOX_FREE})
        ET.SubElement(
            box,
            "geom",
            {
                "name": "box_collision",
                "type": "box",
                "size": _v(spec.box_size.x / 2.0, spec.box_size.y / 2.0, spec.box_size.z / 2.0),
                "mass": _fmt(spec.box_mass),
                "material": "box_mat",
                "friction": _v(spec.floor_friction, 0.005, 0.0001),
            },
        )

    def _add_actuators(self, root: ET.Element, spec: SceneSpec) -> None:
        actuator = ET.SubElement(root, "actuator")
        common = {
            "kp": "650",
            "kv": "55",
            "ctrllimited": "true",
            "ctrlrange": _v(-spec.arena_half_size, spec.arena_half_size),
            "forcelimited": "true",
            "forcerange": _v(-spec.controller.max_force, spec.controller.max_force),
        }
        ET.SubElement(
            actuator,
            "position",
            {"name": ModelNames.MOVE_X, "joint": ModelNames.PUSHER_X, **common},
        )
        ET.SubElement(
            actuator,
            "position",
            {"name": ModelNames.MOVE_Y, "joint": ModelNames.PUSHER_Y, **common},
        )
