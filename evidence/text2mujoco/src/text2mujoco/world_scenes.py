"""Bounded world-scene layer for natural-language robot-arm prompts."""

from __future__ import annotations

from typing import Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import ValidationError

from text2mujoco.arm_schemas import (
    ArmObjectShape,
    ArmPosition,
    ArmSceneSpec,
    ArmSize3,
    ArmStaticProp,
    baseline_arm_scene,
)
from text2mujoco.errors import LLMConfigurationError
from text2mujoco.schemas import RgbColor, Vec3
from text2mujoco.settings import Settings

WORLD_SCHEMA_VERSION = "1.0"
WorldSpeed = Literal["normal", "slow", "careful"]
WorldSceneSource = Literal["llm", "local-limited"]

WORLD_SCENE_SYSTEM_PROMPT = """Convert the user's request into a WorldSceneSpec.
Return only structured output. Do not return Python, MuJoCo XML, code, markdown, or prose.
The current simulator is a bounded tabletop robot-arm world. It can create a virtual scene
with one manipulated object, optional static props, and a pick-and-place task. Use realistic
SI units, keep all objects on the table, and keep the target reachable by the robot arm.
The object must move through MuJoCo contacts, friction, gravity, and actuator motion only."""


class WorldTaskSpec(BaseModel):
    """High-level robot-arm task requested by the user."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["pick_place"] = "pick_place"
    instruction_summary: str = Field(
        default="Pick and place the object in the generated scene.", max_length=300
    )
    target_x: float = Field(default=0.22, ge=-0.34, le=0.34)
    target_y: float = Field(default=0.18, ge=-0.24, le=0.24)
    speed: WorldSpeed = "normal"
    drop_height: float = Field(default=0.035, ge=0.01, le=0.08)


class WorldObjectSpec(BaseModel):
    """Dynamic object that the robot arm should manipulate."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="red_box", min_length=1, max_length=48, pattern=r"^[A-Za-z0-9_]+$")
    shape: ArmObjectShape = "box"
    position: ArmPosition = Field(
        default_factory=lambda: ArmPosition(x=0.18, y=-0.12, z=0.13)
    )
    size: Vec3 = Field(default_factory=lambda: Vec3(x=0.07, y=0.07, z=0.07))
    mass: float = Field(default=0.12, ge=0.03, le=1.0)
    color: RgbColor = Field(default_factory=lambda: RgbColor(r=0.88, g=0.18, b=0.12))


class WorldStaticPropSpec(BaseModel):
    """Static object used to make the virtual world visible in MuJoCo."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=48, pattern=r"^[A-Za-z0-9_]+$")
    shape: ArmObjectShape = "box"
    position: ArmPosition
    size: ArmSize3
    color: RgbColor = Field(default_factory=lambda: RgbColor(r=0.42, g=0.44, b=0.48))
    collision: bool = True


class WorldSceneSpec(BaseModel):
    """LLM-safe virtual-world contract consumed by the MuJoCo arm adapter."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    schema_version: str = Field(default=WORLD_SCHEMA_VERSION)
    environment_name: str = Field(default="tabletop", min_length=1, max_length=80)
    table_size: ArmSize3 = Field(default_factory=lambda: ArmSize3(x=0.9, y=0.7, z=0.08))
    table_height: float = Field(default=0.08, ge=0.04, le=0.2)
    floor_friction: float = Field(default=0.8, ge=0.2, le=1.5)
    task: WorldTaskSpec = Field(default_factory=WorldTaskSpec)
    manipulated_object: WorldObjectSpec = Field(default_factory=WorldObjectSpec)
    static_props: tuple[WorldStaticPropSpec, ...] = Field(default_factory=tuple)

    @field_validator("schema_version")
    @classmethod
    def version_is_supported(cls, value: str) -> str:
        if value != WORLD_SCHEMA_VERSION:
            msg = f"schema_version must be {WORLD_SCHEMA_VERSION}"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def scene_fits_table(self) -> Self:
        table_half_x = self.table_size.x / 2.0
        table_half_y = self.table_size.y / 2.0
        object_margin = max(self.manipulated_object.size.x, self.manipulated_object.size.y) / 2.0
        if (
            abs(self.manipulated_object.position.x) + object_margin > table_half_x
            or abs(self.manipulated_object.position.y) + object_margin > table_half_y
        ):
            msg = "manipulated_object must fit on the table"
            raise ValueError(msg)
        for prop in self.static_props:
            if (
                abs(prop.position.x) + prop.size.x / 2.0 > table_half_x
                or abs(prop.position.y) + prop.size.y / 2.0 > table_half_y
            ):
                msg = f"static prop {prop.name} must fit on the table"
                raise ValueError(msg)
        return self


class ResponsesClient(Protocol):
    """Small protocol for OpenAI or fake test clients."""

    def parse(self, **kwargs: object) -> object:
        """Parse a structured response."""


class OpenAIClientProtocol(Protocol):
    """OpenAI client subset used by the world-scene generator."""

    responses: ResponsesClient


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _clamp(value: float, low: float, high: float) -> float:
    return min(max(value, low), high)


def _object_color(text: str) -> tuple[str, RgbColor]:
    if _contains_any(text, ("파란", "파랑", "blue")):
        return "blue", RgbColor(r=0.05, g=0.25, b=0.9)
    if _contains_any(text, ("초록", "녹색", "green")):
        return "green", RgbColor(r=0.08, g=0.62, b=0.22)
    if _contains_any(text, ("노란", "노랑", "yellow")):
        return "yellow", RgbColor(r=0.94, g=0.78, b=0.1)
    return "red", RgbColor(r=0.88, g=0.18, b=0.12)


def _object_shape_and_size(text: str) -> tuple[ArmObjectShape, Vec3]:
    if _contains_any(text, ("원통", "cylinder")):
        return "cylinder", Vec3(x=0.08, y=0.08, z=0.1)
    if _contains_any(text, ("구", "공", "sphere", "ball")):
        return "sphere", Vec3(x=0.075, y=0.075, z=0.075)
    return "box", Vec3(x=0.07, y=0.07, z=0.07)


def _environment_name(text: str) -> str:
    if _contains_any(text, ("창고", "warehouse")):
        return "warehouse"
    if _contains_any(text, ("실험실", "lab", "laboratory")):
        return "lab"
    if _contains_any(text, ("작업장", "workshop")):
        return "workshop"
    if _contains_any(text, ("주방", "kitchen")):
        return "kitchen"
    return "tabletop"


def _static_props_for_prompt(text: str) -> tuple[WorldStaticPropSpec, ...]:
    props: list[WorldStaticPropSpec] = []
    if _contains_any(text, ("선반", "shelf", "받침대", "platform")):
        props.append(
            WorldStaticPropSpec(
                name="shelf",
                shape="box",
                position=ArmPosition(x=0.0, y=0.28, z=0.105),
                size=ArmSize3(x=0.22, y=0.06, z=0.05),
                color=RgbColor(r=0.4, g=0.42, b=0.48),
                collision=True,
            )
        )
    if _contains_any(text, ("벽", "wall", "칸막이")):
        props.append(
            WorldStaticPropSpec(
                name="back_wall",
                shape="box",
                position=ArmPosition(x=0.0, y=0.33, z=0.2),
                size=ArmSize3(x=0.55, y=0.04, z=0.24),
                color=RgbColor(r=0.52, g=0.55, b=0.6),
                collision=False,
            )
        )
    return tuple(props)


def parse_world_scene_locally(prompt: str) -> WorldSceneSpec:
    """Parse common scene/task requests without claiming full LLM understanding."""

    text = prompt.casefold()
    target_x = 0.22
    target_y = 0.18
    speed: WorldSpeed = "normal"
    drop_height = 0.035
    floor_friction = 0.8
    mass = 0.12

    if _contains_any(text, ("오른쪽", "right")):
        target_x += 0.06
    if _contains_any(text, ("왼쪽", "left")):
        target_x -= 0.06
    if _contains_any(text, ("뒤", "뒤쪽", "back", "rear")):
        target_y += 0.04
    if _contains_any(text, ("앞", "앞쪽", "front", "forward")):
        target_y -= 0.06

    if _contains_any(text, ("조심", "정확", "careful", "precise")):
        speed = "careful"
    elif _contains_any(text, ("천천히", "slow", "slowly")):
        speed = "slow"

    if _contains_any(text, ("높게", "higher", "높은 곳")):
        drop_height = 0.06
    elif _contains_any(text, ("아주 조금", "살짝", "lower")):
        drop_height = 0.025
    elif _contains_any(text, ("조금 위", "떨어", "drop")):
        drop_height = 0.035

    if _contains_any(text, ("무겁", "heavy", "heavier")):
        mass = 0.2
    elif _contains_any(text, ("가볍", "light", "lighter")):
        mass = 0.08

    if _contains_any(text, ("미끄러운", "미끄럽", "slippery")):
        floor_friction = 0.45
    elif _contains_any(text, ("거친", "마찰", "rough", "grippy")):
        floor_friction = 1.2

    color_label, color = _object_color(text)
    shape, size = _object_shape_and_size(text)
    object_z = 0.08 + size.z / 2.0
    target_x = _clamp(target_x, -0.34, 0.34)
    target_y = _clamp(target_y, -0.24, 0.24)
    summary = prompt.strip()[:300] or "Pick and place the object in the generated scene."

    return WorldSceneSpec(
        environment_name=_environment_name(text),
        floor_friction=floor_friction,
        task=WorldTaskSpec(
            kind="pick_place",
            instruction_summary=summary,
            target_x=target_x,
            target_y=target_y,
            speed=speed,
            drop_height=drop_height,
        ),
        manipulated_object=WorldObjectSpec(
            name=f"{color_label}_{shape}",
            shape=shape,
            position=ArmPosition(x=0.18, y=-0.12, z=object_z),
            size=size,
            mass=mass,
            color=color,
        ),
        static_props=_static_props_for_prompt(text),
    )


def _controller_updates(task: WorldTaskSpec) -> dict[str, float]:
    updates: dict[str, float] = {"release_drop_height": task.drop_height}
    if task.speed == "slow":
        updates |= {
            "state_hold_time": 0.95,
            "gripper_close_time": 0.85,
            "place_settle_time": 0.7,
        }
    elif task.speed == "careful":
        updates |= {
            "state_hold_time": 1.1,
            "gripper_close_time": 0.95,
            "place_settle_time": 0.85,
        }
    return updates


def _arm_static_prop(prop: WorldStaticPropSpec) -> ArmStaticProp:
    return ArmStaticProp(
        name=prop.name,
        shape=prop.shape,
        position=prop.position,
        size=prop.size,
        color=prop.color,
        collision=prop.collision,
    )


def world_to_arm_scene(world: WorldSceneSpec, base: ArmSceneSpec | None = None) -> ArmSceneSpec:
    """Adapt a bounded world scene to the existing contact-only arm simulator."""

    source = base or baseline_arm_scene()
    obj = world.manipulated_object
    task = world.task
    object_z = max(obj.position.z, world.table_height + obj.size.z / 2.0)
    updates: dict[str, object] = {
        "task_description": task.instruction_summary,
        "table_size": world.table_size,
        "table_height": world.table_height,
        "object_position": ArmPosition(x=obj.position.x, y=obj.position.y, z=object_z),
        "object_shape": obj.shape,
        "object_size": obj.size,
        "object_mass": obj.mass,
        "floor_friction": world.floor_friction,
        "controller": source.controller.model_copy(update=_controller_updates(task)),
        "static_props": tuple(_arm_static_prop(prop) for prop in world.static_props),
        "object_color": obj.color,
    }

    fallback_x = source.target_position.x
    fallback_y = source.target_position.y
    delta_x = task.target_x - fallback_x
    delta_y = task.target_y - fallback_y
    last_error: ValidationError | None = None
    for scale in (1.0, 0.75, 0.5, 0.25, 0.0):
        candidate_updates = updates | {
            "target_position": ArmPosition(
                x=fallback_x + delta_x * scale,
                y=fallback_y + delta_y * scale,
                z=world.table_height,
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
    raise RuntimeError("unreachable world-to-arm validation path")


def baseline_world_scene() -> WorldSceneSpec:
    """Return a deterministic world-scene prompt equivalent to the arm baseline."""

    return WorldSceneSpec(
        task=WorldTaskSpec(
            instruction_summary=(
                "Pick up the red cube with a simple robot arm and place it on the green target."
            )
        )
    )


class OpenAIWorldSceneGenerator:
    """Generate validated world scenes through OpenAI structured outputs."""

    def __init__(self, *, settings: Settings, client: OpenAIClientProtocol | None = None) -> None:
        self.settings = settings
        self.client = client

    def _client(self) -> OpenAIClientProtocol:
        if self.client is not None:
            return self.client
        if not self.settings.openai_api_key:
            raise LLMConfigurationError("OPENAI_API_KEY is not set for world scene generation.")
        from openai import OpenAI

        self.client = OpenAI(api_key=self.settings.openai_api_key)
        return self.client

    def generate(self, prompt: str) -> WorldSceneSpec:
        """Generate and validate one bounded world scene."""

        response = self._client().responses.parse(
            model=self.settings.openai_model,
            input=[
                {"role": "system", "content": WORLD_SCENE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            text_format=WorldSceneSpec,
        )
        parsed = getattr(response, "output_parsed", None)
        world = (
            parsed if isinstance(parsed, WorldSceneSpec) else WorldSceneSpec.model_validate(parsed)
        )
        world_to_arm_scene(world)
        return world


def generate_world_scene(
    prompt: str,
    *,
    settings: Settings,
    client: OpenAIClientProtocol | None = None,
) -> tuple[WorldSceneSpec, WorldSceneSource]:
    """Generate a world scene with an LLM when configured, otherwise a limited parser."""

    if client is not None or settings.openai_api_key:
        return OpenAIWorldSceneGenerator(settings=settings, client=client).generate(prompt), "llm"
    return parse_world_scene_locally(prompt), "local-limited"
