from __future__ import annotations

import pytest

from text2mujoco.errors import LLMConfigurationError
from text2mujoco.llm_client import OpenAISceneGenerator
from text2mujoco.schemas import baseline_scene
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
        assert kwargs["text_format"].__name__ == "SceneSpec"
        return FakeResponse(self.parsed)


class FakeClient:
    def __init__(self, parsed: object) -> None:
        self.responses = FakeResponses(parsed)


def test_missing_api_key_has_clear_error() -> None:
    settings = Settings(openai_api_key=None, openai_model="gpt-5.6")
    generator = OpenAISceneGenerator(settings=settings)

    with pytest.raises(LLMConfigurationError, match="OPENAI_API_KEY"):
        generator.generate("상자를 목표로 밀어줘")


def test_fake_client_generates_scene_without_network() -> None:
    settings = Settings(openai_api_key=None, openai_model="gpt-5.6")
    fake_client = FakeClient(baseline_scene())
    generator = OpenAISceneGenerator(settings=settings, client=fake_client)

    spec = generator.generate("상자를 목표로 밀어줘")

    assert spec.schema_version == "1.0"
    assert fake_client.responses.calls == 1
