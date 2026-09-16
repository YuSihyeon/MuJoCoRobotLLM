"""Natural-language robot-arm action parsing."""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field
from pydantic_core import ValidationError

from text2mujoco.arm_schemas import ArmPosition, ArmSceneSpec, baseline_arm_scene
from text2mujoco.errors import LLMConfigurationError
from text2mujoco.settings import Settings

ArmSpeed = Literal["normal", "slow", "careful"]

ARM_ACTION_SYSTEM_PROMPT = """Convert the user's robot-arm request into an ArmActionSpec.
Return only structured output. Do not return Python, MuJoCo XML, code, markdown, or prose.
The simulation is contact-only: the cube must move through MuJoCo contact, friction, gravity,
and actuator motion. Keep target_x and target_y on the table. Prefer slow or careful motion
for requests about realistic, gentle, safe, or precise behavior."""


class ArmActionSpec(BaseModel):
    """Bounded high-level intent for a robot-arm pick-and-place run."""

    model_config = ConfigDict(extra="forbid")

    action: Literal["pick_place"] = "pick_place"
    instruction_summary: str = Field(default="Pick and place the red cube.", max_length=240)
    target_x: float = Field(default=0.22, ge=-0.34, le=0.34)
    target_y: float = Field(default=0.18, ge=-0.24, le=0.24)
    drop_height: float = Field(default=0.035, ge=0.01, le=0.08)
    speed: ArmSpeed = "normal"
    object_mass: float | None = Field(default=None, ge=0.03, le=0.4)
    floor_friction: float | None = Field(default=None, ge=0.4, le=1.5)


class ResponsesClient(Protocol):
    """Small protocol for OpenAI or fake test clients."""

    def parse(self, **kwargs: object) -> object:
        """Parse a structured response."""


class OpenAIClientProtocol(Protocol):
    """OpenAI client subset used by the arm action generator."""

    responses: ResponsesClient


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def parse_arm_action_locally(prompt: str) -> ArmActionSpec:
    """Parse common robot-arm instructions without an API key."""

    text = prompt.casefold()
    target_x = 0.22
    target_y = 0.18
    drop_height = 0.035
    speed: ArmSpeed = "normal"
    object_mass: float | None = None
    floor_friction: float | None = None

    if _contains_any(text, ("오른", "right")):
        target_x += 0.06
    if _contains_any(text, ("왼", "left")):
        target_x -= 0.06
    if _contains_any(text, ("뒤", "back", "rear")):
        target_y += 0.06
    if _contains_any(text, ("앞", "front", "forward")):
        target_y -= 0.06

    if _contains_any(text, ("조심", "careful", "precise", "정확")):
        speed = "careful"
    elif _contains_any(text, ("천천", "slow", "slowly")):
        speed = "slow"

    if _contains_any(text, ("높게", "더 높", "higher")):
        drop_height = 0.06
    elif _contains_any(text, ("낮게", "아주 조금", "lower")):
        drop_height = 0.02
    elif _contains_any(text, ("조금 위", "살짝", "떨어", "drop")):
        drop_height = 0.035

    if _contains_any(text, ("무겁", "heavy", "heavier")):
        object_mass = 0.2
    elif _contains_any(text, ("가볍", "light", "lighter")):
        object_mass = 0.08

    if _contains_any(text, ("미끄럽", "slippery")):
        floor_friction = 0.45
    elif _contains_any(text, ("거칠", "rough", "grippy", "마찰")):
        floor_friction = 1.2

    return ArmActionSpec(
        instruction_summary=prompt[:240] or "Pick and place the red cube.",
        target_x=target_x,
        target_y=target_y,
        drop_height=drop_height,
        speed=speed,
        object_mass=object_mass,
        floor_friction=floor_friction,
    )


def apply_action_to_scene(
    action: ArmActionSpec, base: ArmSceneSpec | None = None
) -> ArmSceneSpec:
    """Apply a bounded action intent to a validated arm scene."""

    source = base or baseline_arm_scene()
    controller_updates: dict[str, float] = {
        "release_drop_height": action.drop_height,
    }
    if action.speed == "slow":
        controller_updates |= {
            "state_hold_time": 0.95,
            "gripper_close_time": 0.85,
            "place_settle_time": 0.7,
        }
    elif action.speed == "careful":
        controller_updates |= {
            "state_hold_time": 1.1,
            "gripper_close_time": 0.95,
            "place_settle_time": 0.85,
        }

    updates: dict[str, object] = {
        "task_description": action.instruction_summary,
        "controller": source.controller.model_copy(update=controller_updates),
    }
    if action.object_mass is not None:
        updates["object_mass"] = action.object_mass
    if action.floor_friction is not None:
        updates["floor_friction"] = action.floor_friction

    fallback_x = source.target_position.x
    fallback_y = source.target_position.y
    delta_x = action.target_x - fallback_x
    delta_y = action.target_y - fallback_y
    last_error: ValidationError | None = None
    for scale in (1.0, 0.75, 0.5, 0.25, 0.0):
        candidate_updates = updates | {
            "target_position": ArmPosition(
                x=fallback_x + delta_x * scale,
                y=fallback_y + delta_y * scale,
                z=source.table_height,
            )
        }
        try:
            return ArmSceneSpec.model_validate(
                source.model_copy(update=candidate_updates).model_dump()
            )
        except ValidationError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise RuntimeError("unreachable arm action validation path")


class OpenAIArmActionGenerator:
    """Generate validated arm actions through OpenAI structured outputs."""

    def __init__(self, *, settings: Settings, client: OpenAIClientProtocol | None = None) -> None:
        self.settings = settings
        self.client = client

    def _client(self) -> OpenAIClientProtocol:
        if self.client is not None:
            return self.client
        if not self.settings.openai_api_key:
            raise LLMConfigurationError("OPENAI_API_KEY is not set for arm action generation.")
        from openai import OpenAI

        self.client = OpenAI(api_key=self.settings.openai_api_key)
        return self.client

    def generate(self, prompt: str) -> ArmActionSpec:
        """Generate and validate one arm action."""

        response = self._client().responses.parse(
            model=self.settings.openai_model,
            input=[
                {"role": "system", "content": ARM_ACTION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            text_format=ArmActionSpec,
        )
        parsed = getattr(response, "output_parsed", None)
        action = (
            parsed if isinstance(parsed, ArmActionSpec) else ArmActionSpec.model_validate(parsed)
        )
        apply_action_to_scene(action)
        return action


def generate_arm_action(
    prompt: str,
    *,
    settings: Settings,
    client: OpenAIClientProtocol | None = None,
) -> tuple[ArmActionSpec, Literal["llm", "local"]]:
    """Generate an arm action with LLM when configured, otherwise local parsing."""

    if client is not None or settings.openai_api_key:
        return OpenAIArmActionGenerator(settings=settings, client=client).generate(prompt), "llm"
    return parse_arm_action_locally(prompt), "local"
