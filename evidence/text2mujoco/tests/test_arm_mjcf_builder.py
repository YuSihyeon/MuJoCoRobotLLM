from __future__ import annotations

import xml.etree.ElementTree as ET

from text2mujoco.arm_mjcf_builder import ArmMJCFBuilder
from text2mujoco.arm_schemas import ArmPosition, ArmSize3, ArmStaticProp, baseline_arm_scene
from text2mujoco.schemas import RgbColor, Vec3


def test_arm_mjcf_is_deterministic_and_parseable() -> None:
    spec = baseline_arm_scene()
    builder = ArmMJCFBuilder()

    xml_a = builder.build(spec)
    xml_b = builder.build(spec)
    root = ET.fromstring(xml_a)

    assert xml_a == xml_b
    assert root.tag == "mujoco"
    assert root.find(".//joint[@name='base_yaw']") is not None
    assert root.find(".//joint[@name='shoulder']") is not None
    assert root.find(".//joint[@name='elbow']") is not None
    assert root.find(".//joint[@name='wrist']") is not None
    assert root.find(".//joint[@name='left_finger']") is not None
    assert root.find(".//joint[@name='right_finger']") is not None
    assert root.find(".//body[@name='cube']") is not None


def test_arm_mjcf_contains_recognizable_robot_arm_visual_parts() -> None:
    xml = ArmMJCFBuilder().build(baseline_arm_scene())
    root = ET.fromstring(xml)

    expected_geoms = [
        "base_pedestal",
        "base_turntable",
        "shoulder_hub",
        "upper_arm_link",
        "elbow_hub",
        "forearm_link",
        "wrist_hub",
        "gripper_palm_geom",
        "left_finger_pad",
        "right_finger_pad",
    ]

    for geom_name in expected_geoms:
        assert root.find(f".//geom[@name='{geom_name}']") is not None


def test_arm_mjcf_does_not_use_weld_constraint_for_grasping() -> None:
    xml = ArmMJCFBuilder().build(baseline_arm_scene())
    root = ET.fromstring(xml)

    weld = root.find(".//equality/weld[@name='grasp_weld']")

    assert weld is None


def test_arm_mjcf_renders_non_box_dynamic_object_shape() -> None:
    spec = baseline_arm_scene().model_copy(
        update={
            "object_shape": "cylinder",
            "object_size": Vec3(x=0.08, y=0.08, z=0.11),
        }
    )

    xml = ArmMJCFBuilder().build(spec)
    root = ET.fromstring(xml)
    object_geom = root.find(".//geom[@name='cube_collision']")

    assert object_geom is not None
    assert object_geom.attrib["type"] == "cylinder"
    assert object_geom.attrib["size"] == "0.04 0.055"


def test_arm_mjcf_renders_static_scene_props() -> None:
    spec = baseline_arm_scene().model_copy(
        update={
            "static_props": (
                ArmStaticProp(
                    name="shelf",
                    shape="box",
                    position=ArmPosition(x=0.0, y=0.28, z=0.105),
                    size=ArmSize3(x=0.22, y=0.06, z=0.05),
                    color=RgbColor(r=0.4, g=0.42, b=0.48),
                    collision=True,
                ),
            )
        }
    )

    xml = ArmMJCFBuilder().build(spec)
    root = ET.fromstring(xml)
    prop_body = root.find(".//body[@name='prop_shelf']")
    prop_geom = root.find(".//geom[@name='prop_shelf_geom']")

    assert prop_body is not None
    assert prop_geom is not None
    assert prop_geom.attrib["type"] == "box"
    assert prop_geom.attrib["rgba"] == "0.4 0.42 0.48 1"
