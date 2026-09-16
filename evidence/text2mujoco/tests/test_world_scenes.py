from __future__ import annotations

import pytest

from text2mujoco.settings import Settings
from text2mujoco.world_scenes import (
    WorldObjectSpec,
    WorldSceneSpec,
    WorldStaticPropSpec,
    WorldTaskSpec,
    generate_world_scene,
    parse_world_scene_locally,
    world_to_arm_scene,
)


class FakeResponse:
    def __init__(self, parsed: object) -> None:
        self.output_parsed = parsed


class FakeResponses:
    def __init__(self, parsed: object) -> None:
        self.parsed = parsed
        self.calls = 0

    def parse(self, **kwargs: object) -> FakeResponse:
        self.calls += 1
        assert kwargs["text_format"].__name__ == "WorldSceneSpec"
        return FakeResponse(self.parsed)


class FakeClient:
    def __init__(self, parsed: object) -> None:
        self.responses = FakeResponses(parsed)


def test_local_parser_builds_scene_from_korean_prompt() -> None:
    world = parse_world_scene_locally(
        "창고 안에서 파란 원통을 오른쪽 뒤로 천천히 옮기고 "
        "미끄러운 바닥에서 조금 위에서 떨어뜨려. 옆에는 낮은 선반을 둬."
    )

    assert world.environment_name == "warehouse"
    assert world.manipulated_object.shape == "cylinder"
    assert world.manipulated_object.color.b > world.manipulated_object.color.r
    assert world.task.kind == "pick_place"
    assert world.task.speed == "slow"
    assert world.task.drop_height == pytest.approx(0.035)
    assert world.floor_friction < 0.6
    assert any(prop.name == "shelf" for prop in world.static_props)


def test_world_to_arm_scene_maps_object_and_static_props() -> None:
    world = WorldSceneSpec(
        environment_name="warehouse",
        task=WorldTaskSpec(
            kind="pick_place",
            instruction_summary="Move a blue cylinder behind the target.",
            target_x=0.28,
            target_y=0.22,
            speed="careful",
            drop_height=0.055,
        ),
        manipulated_object=WorldObjectSpec(
            name="blue_cylinder",
            shape="cylinder",
            color=(0.05, 0.25, 0.9, 1.0),
            mass=0.18,
        ),
        static_props=(
            WorldStaticPropSpec(
                name="shelf",
                shape="box",
                position=(0.0, 0.28, 0.105),
                size=(0.22, 0.06, 0.05),
                color=(0.4, 0.42, 0.48, 1.0),
                collision=True,
            ),
        ),
        floor_friction=0.48,
    )

    arm = world_to_arm_scene(world)

    assert arm.task_description == "Move a blue cylinder behind the target."
    assert arm.object_shape == "cylinder"
    assert arm.object_color.b > arm.object_color.r
    assert arm.object_mass == pytest.approx(0.18)
    assert arm.floor_friction == pytest.approx(0.48)
    assert arm.target_position.x >= 0.22
    assert arm.target_position.y >= 0.18
    assert arm.controller.release_drop_height == pytest.approx(0.055)
    assert len(arm.static_props) == 1
    assert arm.static_props[0].name == "shelf"


def test_generate_world_scene_uses_llm_client_when_available() -> None:
    parsed = WorldSceneSpec(
        environment_name="lab",
        task=WorldTaskSpec(
            kind="pick_place",
            instruction_summary="Carefully move the red sphere.",
            speed="careful",
        ),
        manipulated_object=WorldObjectSpec(name="red_sphere", shape="sphere"),
    )
    fake_client = FakeClient(parsed)
    settings = Settings(openai_api_key=None, openai_model="gpt-5.6")

    world, source = generate_world_scene(
        "carefully move the red sphere", settings=settings, client=fake_client
    )

    assert source == "llm"
    assert world.manipulated_object.shape == "sphere"
    assert fake_client.responses.calls == 1


def test_generate_world_scene_labels_no_key_fallback_as_limited() -> None:
    settings = Settings(openai_api_key=None, openai_model="gpt-5.6")

    world, source = generate_world_scene("move a blue cylinder slowly", settings=settings)

    assert source == "local-limited"
    assert world.manipulated_object.shape == "cylinder"
    assert world.task.speed == "slow"
