"""OpenAI Responses API integration for structured SceneSpec generation."""

from __future__ import annotations

from typing import Protocol

from text2mujoco.errors import LLMConfigurationError, SceneValidationError
from text2mujoco.schemas import SceneSpec
from text2mujoco.settings import Settings
from text2mujoco.validation import validate_scene

SYSTEM_PROMPT = """You create physically plausible MuJoCo push-world SceneSpec objects.
Use SI units. Respect every numeric range in the Pydantic schema. Keep the box and target
inside the arena, separated by a meaningful distance. Translate natural-language terms:
"heavy" means higher box_mass, "light" means lower box_mass, "slippery" means lower
floor_friction, and "rough" means higher floor_friction. Never return Python code, XML,
markdown, or free text outside the SceneSpec structured output."""


class ResponsesClient(Protocol):
    """Small protocol for OpenAI or fake test clients."""

    def parse(self, **kwargs: object) -> object:
        """Parse a structured response."""


class OpenAIClientProtocol(Protocol):
    """OpenAI client subset used by the generator."""

    responses: ResponsesClient


class OpenAISceneGenerator:
    """Generate validated SceneSpec objects through OpenAI structured outputs."""

    def __init__(self, *, settings: Settings, client: OpenAIClientProtocol | None = None) -> None:
        self.settings = settings
        self.client = client

    def _client(self) -> OpenAIClientProtocol:
        if self.client is not None:
            return self.client
        if not self.settings.openai_api_key:
            raise LLMConfigurationError(
                "OPENAI_API_KEY is not set. Set it only as an environment variable, "
                "or use baseline/run/validate without the LLM."
            )
        from openai import OpenAI

        self.client = OpenAI(api_key=self.settings.openai_api_key)
        return self.client

    def generate(self, prompt: str) -> SceneSpec:
        """Generate, semantically validate, and retry a SceneSpec."""

        if self.client is None and not self.settings.openai_api_key:
            raise LLMConfigurationError(
                "OPENAI_API_KEY is not set. The generate command needs an API key; "
                "baseline and run commands do not."
            )

        feedback = ""
        last_error: SceneValidationError | None = None
        for _attempt in range(3):
            user_content = (
                prompt if not feedback else f"{prompt}\n\nValidation feedback: {feedback}"
            )
            response = self._client().responses.parse(
                model=self.settings.openai_model,
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                text_format=SceneSpec,
            )
            parsed = getattr(response, "output_parsed", None)
            spec = parsed if isinstance(parsed, SceneSpec) else SceneSpec.model_validate(parsed)
            try:
                validate_scene(spec, include_mujoco=False)
            except SceneValidationError as exc:
                last_error = exc
                feedback = "; ".join(exc.issues)
                continue
            return spec

        details = "; ".join(last_error.issues) if last_error else "unknown validation failure"
        raise SceneValidationError([f"LLM SceneSpec failed validation after 3 attempts: {details}"])
