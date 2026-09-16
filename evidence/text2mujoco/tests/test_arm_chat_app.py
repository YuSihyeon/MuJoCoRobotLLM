from __future__ import annotations

from pathlib import Path

from text2mujoco.arm_chat_app import (
    DEFAULT_CHAT_PROMPT,
    ArmPromptRun,
    format_prompt_summary,
    normalize_chat_prompt,
    run_arm_prompt,
)
from text2mujoco.arm_schemas import baseline_arm_scene
from text2mujoco.arm_simulation import ArmSimulationMetrics
from text2mujoco.settings import Settings
from text2mujoco.world_scenes import parse_world_scene_locally


class FakeArtifacts:
    scene_spec_path = Path("artifacts/fake_arm/scene_spec.json")
    run_dir = Path("artifacts/fake_arm")


class FakeResult:
    def __init__(self) -> None:
        self.artifacts = FakeArtifacts()
        self.metrics = ArmSimulationMetrics(
            success=True,
            terminated=True,
            truncated=False,
            termination_reason="success",
            simulation_time=5.3,
            wall_clock_time=0.1,
            final_object_target_distance=0.01,
            minimum_object_target_distance=0.01,
            maximum_object_height=0.32,
            release_object_height=0.15,
            release_object_bottom_height=0.12,
            minimum_object_bottom_height=0.079,
            physics_steps=2650,
            controller_state="SUCCESS",
            assisted_grasp=False,
            constraint_grasp=False,
            stability_status="stable",
        )


def test_run_arm_prompt_builds_scene_runs_headless_and_skips_viewer_when_requested(
    tmp_path,
) -> None:
    calls: dict[str, object] = {}

    def fake_scene_generator(prompt: str, *, settings: Settings) -> tuple[object, str]:
        calls["prompt"] = prompt
        return (
            parse_world_scene_locally(
                "창고에서 파란 원통을 오른쪽 뒤로 천천히 옮기고 조금 위에서 떨어뜨려."
            ),
            "local-limited",
        )

    def fake_runner(*, spec: object, artifact_dir: Path, mode: str) -> FakeResult:
        calls["spec"] = spec
        calls["artifact_dir"] = artifact_dir
        calls["mode"] = mode
        return FakeResult()

    result = run_arm_prompt(
        "move slowly",
        settings=Settings(openai_api_key=None, openai_model="gpt-5.6", artifact_dir=tmp_path),
        scene_generator=fake_scene_generator,
        simulation_runner=fake_runner,
        launch_viewer=False,
    )

    assert isinstance(result, ArmPromptRun)
    assert calls["prompt"] == "move slowly"
    assert calls["artifact_dir"] == tmp_path
    assert calls["mode"] == "headless"
    assert result.scene_source == "local-limited"
    assert result.viewer_started is False
    assert result.metrics.success is True
    assert result.scene_spec.object_shape == "cylinder"
    assert result.scene_spec.controller.release_drop_height == 0.035


def test_format_prompt_summary_mentions_contact_only_physics() -> None:
    result = ArmPromptRun(
        prompt="move cube",
        world_scene=parse_world_scene_locally("창고에서 파란 원통을 천천히 옮겨."),
        scene_source="local-limited",
        scene_spec=baseline_arm_scene(),
        metrics=FakeResult().metrics,
        artifact_dir=Path("artifacts/fake_arm"),
        scene_spec_path=Path("artifacts/fake_arm/scene_spec.json"),
        viewer_started=True,
    )

    summary = format_prompt_summary(result)

    assert "contact-only" in summary
    assert "source=local-limited" in summary
    assert "object=cylinder" in summary
    assert "success=True" in summary
    assert "viewer=True" in summary


def test_normalize_chat_prompt_uses_default_when_entry_is_empty() -> None:
    assert normalize_chat_prompt("   ") == DEFAULT_CHAT_PROMPT
    assert normalize_chat_prompt("move slowly") == "move slowly"
