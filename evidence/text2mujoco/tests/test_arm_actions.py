from __future__ import annotations

from text2mujoco.arm_actions import (
    ArmActionSpec,
    OpenAIArmActionGenerator,
    apply_action_to_scene,
    generate_arm_action,
    parse_arm_action_locally,
)
from text2mujoco.settings import Settings


class FakeResponse:
    def __init__(self, parsed: object) -> None:
        self.output_parsed = parsed


class FakeResponses:
    def __init__(self, parsed: object) -> None:
        self.parsed = parsed
        self.calls = 0

    def parse(self, **kwargs: object) -> FakeResponse:
        self.calls += 1
        assert kwargs["text_format"].__name__ == "ArmActionSpec"
        return FakeResponse(self.parsed)


class FakeClient:
    def __init__(self, parsed: object) -> None:
        self.responses = FakeResponses(parsed)


def test_local_parser_extracts_safe_physics_intent_from_korean_prompt() -> None:
    action = parse_arm_action_locally(
        "빨간 상자를 오른쪽 뒤로 천천히 옮기고 조금 위에서 떨어뜨려. 상자는 더 무겁게."
    )

    assert action.speed == "slow"
    assert action.drop_height == 0.035
    assert action.object_mass == 0.2
    assert action.target_x > 0.22
    assert action.target_y > 0.18


def test_action_applies_to_valid_contact_only_arm_scene() -> None:
    action = ArmActionSpec(
        instruction_summary="Move slowly and drop from above.",
        speed="slow",
        target_x=0.28,
        target_y=0.2,
        drop_height=0.05,
        object_mass=0.18,
        floor_friction=1.2,
    )

    spec = apply_action_to_scene(action)

    assert 0.22 <= spec.target_position.x <= 0.28
    assert 0.18 <= spec.target_position.y <= 0.2
    assert spec.controller.release_drop_height == 0.05
    assert spec.controller.state_hold_time > 0.7
    assert spec.object_mass == 0.18
    assert spec.floor_friction == 1.2


def test_fake_llm_client_generates_arm_action_without_network() -> None:
    parsed = ArmActionSpec(
        instruction_summary="Careful pick and place.",
        speed="careful",
        target_x=0.18,
        target_y=0.2,
        drop_height=0.04,
    )
    fake_client = FakeClient(parsed)
    settings = Settings(openai_api_key=None, openai_model="gpt-5.6")

    action = OpenAIArmActionGenerator(settings=settings, client=fake_client).generate(
        "carefully move the cube"
    )

    assert action.speed == "careful"
    assert action.drop_height == 0.04
    assert fake_client.responses.calls == 1


def test_generate_arm_action_falls_back_to_local_parser_without_api_key() -> None:
    settings = Settings(openai_api_key=None, openai_model="gpt-5.6")

    action, source = generate_arm_action("move it slowly", settings=settings)

    assert source == "local"
    assert action.speed == "slow"
