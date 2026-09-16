from __future__ import annotations

import xml.etree.ElementTree as ET

from text2mujoco.mjcf_builder import MJCFBuilder
from text2mujoco.schemas import baseline_scene


def test_same_spec_builds_same_mjcf() -> None:
    spec = baseline_scene()
    builder = MJCFBuilder()

    assert builder.build(spec) == builder.build(spec)


def test_mjcf_xml_parses_and_contains_named_contract() -> None:
    xml = MJCFBuilder().build(baseline_scene())
    root = ET.fromstring(xml)

    assert root.tag == "mujoco"
    assert root.find(".//joint[@name='pusher_x']") is not None
    assert root.find(".//joint[@name='pusher_y']") is not None
    assert root.find(".//actuator/position[@name='move_x']") is not None
    assert root.find(".//actuator/position[@name='move_y']") is not None
    assert root.find(".//body[@name='box']") is not None
    assert root.find(".//body[@name='target']") is not None
