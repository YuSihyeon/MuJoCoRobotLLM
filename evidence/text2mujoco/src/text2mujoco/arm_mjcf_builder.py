"""Deterministic MJCF builder for the robot-arm pick-and-place demo."""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET

from text2mujoco.arm_schemas import ArmObjectShape, ArmSceneSpec, ArmSize3
from text2mujoco.errors import MJCFBuildError
from text2mujoco.mjcf_builder import GENERATOR_VERSION


class ArmModelNames:
    """Named MuJoCo contract for the robot arm."""

    BASE_YAW = "base_yaw"
    SHOULDER = "shoulder"
    ELBOW = "elbow"
    WRIST = "wrist"
    LEFT_FINGER = "left_finger"
    RIGHT_FINGER = "right_finger"
    MOVE_BASE_YAW = "move_base_yaw"
    MOVE_SHOULDER = "move_shoulder"
    MOVE_ELBOW = "move_elbow"
    MOVE_WRIST = "move_wrist"
    MOVE_LEFT_FINGER = "move_left_finger"
    MOVE_RIGHT_FINGER = "move_right_finger"
    CUBE = "cube"
    CUBE_FREE = "cube_free"
    TARGET = "arm_target"
    GRIPPER = "gripper_palm"


def _fmt(value: float) -> str:
    return f"{value:.8g}"


def _v(*values: float) -> str:
    return " ".join(_fmt(value) for value in values)


def _visual(attrs: dict[str, str]) -> dict[str, str]:
    """Mark decorative robot geometry as non-colliding."""

    return attrs | {"contype": "0", "conaffinity": "0"}


def _geom_size(shape: ArmObjectShape, size: ArmSize3) -> str:
    """Return MuJoCo geom size text for a bounded object shape."""

    if shape == "box":
        return _v(size.x / 2.0, size.y / 2.0, size.z / 2.0)
    if shape == "cylinder":
        return _v(max(size.x, size.y) / 2.0, size.z / 2.0)
    return _v(max(size.x, size.y, size.z) / 2.0)


class ArmMJCFBuilder:
    """Build MJCF for a simple tabletop robot arm and gripper."""

    def build(self, spec: ArmSceneSpec) -> str:
        """Return deterministic robot-arm MJCF XML."""

        try:
            spec_hash = hashlib.sha256(
                spec.model_dump_json(round_trip=True).encode("utf-8")
            ).hexdigest()[:12]
            root = ET.Element("mujoco", {"model": f"text2mujoco_arm_pick_place_{spec_hash}"})
            root.append(
                ET.Comment(
                    f"generator={GENERATOR_VERSION}; arm_schema={spec.schema_version}; "
                    f"seed={spec.seed}; run_id={spec_hash}; contact_only_grasp=true"
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
                    "iterations": "100",
                    "ls_iterations": "50",
                },
            )
            self._add_defaults(root, spec)
            self._add_assets(root, spec)
            self._add_worldbody(root, spec)
            self._add_actuators(root, spec)
            ET.indent(root, space="  ")
            return ET.tostring(root, encoding="unicode")
        except Exception as exc:  # noqa: BLE001 - wrapped as project error
            raise MJCFBuildError(f"failed to build robot-arm MJCF: {exc}") from exc

    def _add_defaults(self, root: ET.Element, spec: ArmSceneSpec) -> None:
        default = ET.SubElement(root, "default")
        ET.SubElement(
            default,
            "geom",
            {
                "condim": "4",
                "friction": _v(spec.floor_friction, 0.02, 0.001),
                "solref": "0.003 1",
                "solimp": "0.95 0.99 0.0005",
            },
        )
        ET.SubElement(default, "joint", {"damping": "2.2", "armature": "0.015"})

    def _add_assets(self, root: ET.Element, spec: ArmSceneSpec) -> None:
        asset = ET.SubElement(root, "asset")
        ET.SubElement(asset, "material", {"name": "table_mat", "rgba": "0.48 0.52 0.5 1"})
        ET.SubElement(asset, "material", {"name": "base_mat", "rgba": "0.18 0.2 0.24 1"})
        ET.SubElement(asset, "material", {"name": "joint_mat", "rgba": "0.06 0.08 0.11 1"})
        ET.SubElement(asset, "material", {"name": "arm_mat", "rgba": spec.arm_color.rgba_string()})
        ET.SubElement(
            asset, "material", {"name": "cube_mat", "rgba": spec.object_color.rgba_string()}
        )
        ET.SubElement(
            asset, "material", {"name": "target_mat", "rgba": spec.target_color.rgba_string()}
        )
        ET.SubElement(asset, "material", {"name": "finger_mat", "rgba": "0.08 0.1 0.12 1"})

    def _add_worldbody(self, root: ET.Element, spec: ArmSceneSpec) -> None:
        world = ET.SubElement(root, "worldbody")
        ET.SubElement(
            world, "light", {"name": "arm_key_light", "pos": "0 -1.8 2.5", "dir": "0 1 -1"}
        )
        ET.SubElement(
            world,
            "camera",
            {
                "name": "arm_overview",
                "pos": "0 -1.45 0.95",
                "xyaxes": "1 0 0 0 0.55 0.83",
            },
        )
        ET.SubElement(
            world,
            "geom",
            {
                "name": "table",
                "type": "box",
                "pos": _v(0, 0, spec.table_height / 2.0),
                "size": _v(
                    spec.table_size.x / 2.0, spec.table_size.y / 2.0, spec.table_height / 2.0
                ),
                "material": "table_mat",
            },
        )
        self._add_static_props(world, spec)
        self._add_target(world, spec)
        self._add_cube(world, spec)
        self._add_robot(world, spec)

    def _add_static_props(self, world: ET.Element, spec: ArmSceneSpec) -> None:
        for prop in spec.static_props:
            body_name = f"prop_{prop.name}"
            prop_body = ET.SubElement(
                world,
                "body",
                {
                    "name": body_name,
                    "pos": _v(prop.position.x, prop.position.y, prop.position.z),
                },
            )
            geom_attrs = {
                "name": f"{body_name}_geom",
                "type": prop.shape,
                "size": _geom_size(prop.shape, prop.size),
                "rgba": prop.color.rgba_string(),
                "friction": _v(spec.floor_friction, 0.02, 0.001),
            }
            if not prop.collision:
                geom_attrs |= {"contype": "0", "conaffinity": "0"}
            ET.SubElement(prop_body, "geom", geom_attrs)

    def _add_target(self, world: ET.Element, spec: ArmSceneSpec) -> None:
        target = ET.SubElement(
            world,
            "body",
            {
                "name": ArmModelNames.TARGET,
                "pos": _v(
                    spec.target_position.x, spec.target_position.y, spec.table_height + 0.004
                ),
            },
        )
        ET.SubElement(
            target,
            "geom",
            {
                "name": "arm_target_visual",
                "type": "cylinder",
                "size": _v(spec.target_radius, 0.004),
                "material": "target_mat",
                "contype": "0",
                "conaffinity": "0",
            },
        )

    def _add_cube(self, world: ET.Element, spec: ArmSceneSpec) -> None:
        cube = ET.SubElement(
            world,
            "body",
            {
                "name": ArmModelNames.CUBE,
                "pos": _v(spec.object_position.x, spec.object_position.y, spec.object_position.z),
            },
        )
        ET.SubElement(cube, "freejoint", {"name": ArmModelNames.CUBE_FREE})
        ET.SubElement(
            cube,
            "geom",
            {
                "name": "cube_collision",
                "type": spec.object_shape,
                "size": _geom_size(spec.object_shape, spec.object_size),
                "mass": _fmt(spec.object_mass),
                "material": "cube_mat",
                "friction": _v(spec.floor_friction, 0.02, 0.001),
                "solref": "0.002 1",
                "solimp": "0.96 0.995 0.0005",
            },
        )

    def _add_robot(self, world: ET.Element, spec: ArmSceneSpec) -> None:
        robot = spec.robot
        base = ET.SubElement(
            world,
            "body",
            {
                "name": "arm_base",
                "pos": _v(robot.base_position.x, robot.base_position.y, robot.base_position.z),
            },
        )
        ET.SubElement(
            base,
            "geom",
            _visual(
                {
                "name": "base_pedestal",
                "type": "cylinder",
                "pos": "0 0 -0.035",
                "size": "0.09 0.035",
                "material": "base_mat",
                }
            ),
        )
        ET.SubElement(
            base,
            "joint",
            {"name": ArmModelNames.BASE_YAW, "type": "hinge", "axis": "0 0 1", "range": "-2.7 2.7"},
        )
        ET.SubElement(
            base,
            "geom",
            _visual(
                {
                "name": "base_turntable",
                "type": "cylinder",
                "pos": "0 0 0.035",
                "size": "0.07 0.035",
                "material": "joint_mat",
                }
            ),
        )
        ET.SubElement(
            base,
            "geom",
            _visual(
                {
                "name": "base_column",
                "type": "cylinder",
                "pos": _v(0, 0, robot.shoulder_height / 2.0),
                "size": _v(0.045, robot.shoulder_height / 2.0),
                "material": "base_mat",
                }
            ),
        )
        shoulder = ET.SubElement(
            base, "body", {"name": "shoulder_link", "pos": _v(0, 0, robot.shoulder_height)}
        )
        ET.SubElement(
            shoulder,
            "geom",
            _visual(
                {
                    "name": "shoulder_hub",
                    "type": "sphere",
                    "size": "0.055",
                    "material": "joint_mat",
                }
            ),
        )
        ET.SubElement(
            shoulder,
            "joint",
            {"name": ArmModelNames.SHOULDER, "type": "hinge", "axis": "0 1 0", "range": "-1.4 1.6"},
        )
        ET.SubElement(
            shoulder,
            "geom",
            _visual(
                {
                "name": "upper_arm_link",
                "type": "capsule",
                "fromto": _v(0.035, 0, 0, robot.upper_arm_length - 0.035, 0, 0),
                "size": "0.03",
                "material": "arm_mat",
                }
            ),
        )
        ET.SubElement(
            shoulder,
            "geom",
            _visual(
                {
                "name": "upper_arm_side_plate",
                "type": "box",
                "pos": _v(robot.upper_arm_length / 2.0, 0.034, 0),
                "size": _v(robot.upper_arm_length / 2.6, 0.006, 0.024),
                "material": "arm_mat",
                }
            ),
        )
        elbow = ET.SubElement(
            shoulder, "body", {"name": "elbow_link", "pos": _v(robot.upper_arm_length, 0, 0)}
        )
        ET.SubElement(
            elbow,
            "geom",
            _visual(
                {
                    "name": "elbow_hub",
                    "type": "sphere",
                    "size": "0.048",
                    "material": "joint_mat",
                }
            ),
        )
        ET.SubElement(
            elbow,
            "joint",
            {"name": ArmModelNames.ELBOW, "type": "hinge", "axis": "0 1 0", "range": "-2.5 0.2"},
        )
        ET.SubElement(
            elbow,
            "geom",
            _visual(
                {
                "name": "forearm_link",
                "type": "capsule",
                "fromto": _v(0.032, 0, 0, robot.forearm_length - 0.032, 0, 0),
                "size": "0.026",
                "material": "arm_mat",
                }
            ),
        )
        ET.SubElement(
            elbow,
            "geom",
            _visual(
                {
                "name": "forearm_side_plate",
                "type": "box",
                "pos": _v(robot.forearm_length / 2.0, -0.03, 0),
                "size": _v(robot.forearm_length / 2.6, 0.005, 0.021),
                "material": "arm_mat",
                }
            ),
        )
        wrist = ET.SubElement(
            elbow, "body", {"name": "wrist_link", "pos": _v(robot.forearm_length, 0, 0)}
        )
        ET.SubElement(
            wrist,
            "geom",
            _visual(
                {
                    "name": "wrist_hub",
                    "type": "sphere",
                    "size": "0.04",
                    "material": "joint_mat",
                }
            ),
        )
        ET.SubElement(
            wrist,
            "joint",
            {"name": ArmModelNames.WRIST, "type": "hinge", "axis": "0 1 0", "range": "-1.8 1.8"},
        )
        ET.SubElement(
            wrist,
            "geom",
            _visual(
                {
                "name": "wrist_short_link",
                "type": "capsule",
                "fromto": _v(0.01, 0, 0, robot.wrist_length, 0, 0),
                "size": "0.018",
                "material": "arm_mat",
                }
            ),
        )
        gripper = ET.SubElement(
            wrist, "body", {"name": ArmModelNames.GRIPPER, "pos": _v(robot.wrist_length, 0, 0)}
        )
        ET.SubElement(
            gripper,
            "geom",
            _visual(
                {
                "name": "gripper_palm_geom",
                "type": "box",
                "size": "0.038 0.05 0.02",
                "material": "joint_mat",
                }
            ),
        )
        self._add_finger(gripper, ArmModelNames.LEFT_FINGER, "left_finger_geom", 1, spec)
        self._add_finger(gripper, ArmModelNames.RIGHT_FINGER, "right_finger_geom", -1, spec)

    def _add_finger(
        self, gripper: ET.Element, joint_name: str, geom_name: str, side: int, spec: ArmSceneSpec
    ) -> None:
        finger = ET.SubElement(
            gripper, "body", {"name": f"{joint_name}_body", "pos": _v(0, 0, -0.03)}
        )
        ET.SubElement(
            finger,
            "joint",
            {
                "name": joint_name,
                "type": "slide",
                "axis": _v(0, side, 0),
                "range": _v(
                    spec.robot.gripper_closed_width / 2.0, spec.robot.gripper_open_width / 2.0
                ),
            },
        )
        ET.SubElement(
            finger,
            "geom",
            {
                "name": geom_name,
                "type": "box",
                "pos": _v(0, 0, -0.035),
                "size": "0.014 0.01 0.04",
                "material": "finger_mat",
            }
            | {"contype": "0", "conaffinity": "0"},
        )
        ET.SubElement(
            finger,
            "geom",
            {
                "name": "left_finger_pad" if side > 0 else "right_finger_pad",
                "type": "box",
                "pos": _v(0, side * 0.0225, -0.035),
                "size": "0.018 0.008 0.035",
                "material": "joint_mat",
                "friction": _v(5.0, 0.2, 0.02),
                "solref": "0.002 1",
                "solimp": "0.96 0.995 0.0005",
            },
        )

    def _add_actuators(self, root: ET.Element, spec: ArmSceneSpec) -> None:
        actuator = ET.SubElement(root, "actuator")
        joint_specs = [
            (ArmModelNames.MOVE_BASE_YAW, ArmModelNames.BASE_YAW, "-2.7 2.7", "180", "25"),
            (ArmModelNames.MOVE_SHOULDER, ArmModelNames.SHOULDER, "-1.4 1.6", "220", "35"),
            (ArmModelNames.MOVE_ELBOW, ArmModelNames.ELBOW, "-2.5 0.2", "190", "30"),
            (ArmModelNames.MOVE_WRIST, ArmModelNames.WRIST, "-1.8 1.8", "120", "18"),
            (
                ArmModelNames.MOVE_LEFT_FINGER,
                ArmModelNames.LEFT_FINGER,
                _v(spec.robot.gripper_closed_width / 2.0, spec.robot.gripper_open_width / 2.0),
                "160",
                "10",
            ),
            (
                ArmModelNames.MOVE_RIGHT_FINGER,
                ArmModelNames.RIGHT_FINGER,
                _v(spec.robot.gripper_closed_width / 2.0, spec.robot.gripper_open_width / 2.0),
                "160",
                "10",
            ),
        ]
        for name, joint, ctrlrange, kp, kv in joint_specs:
            ET.SubElement(
                actuator,
                "position",
                {
                    "name": name,
                    "joint": joint,
                    "kp": kp,
                    "kv": kv,
                    "ctrllimited": "true",
                    "ctrlrange": ctrlrange,
                    "forcelimited": "true",
                    "forcerange": _v(-spec.robot.max_force, spec.robot.max_force),
                },
            )
