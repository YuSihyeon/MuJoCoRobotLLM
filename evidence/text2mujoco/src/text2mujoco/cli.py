"""Command-line interface for Text-to-MuJoCo Push World."""

from __future__ import annotations

import argparse
import importlib.util
import platform
import sys
import traceback
from pathlib import Path
from typing import NoReturn

from text2mujoco.errors import Text2MujocoError
from text2mujoco.llm_client import OpenAISceneGenerator
from text2mujoco.schemas import baseline_scene, load_scene_spec
from text2mujoco.settings import Settings
from text2mujoco.simulation import run_push_simulation
from text2mujoco.validation import validate_scene


def _write(message: str) -> None:
    sys.stdout.write(message + "\n")


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""

    parser = argparse.ArgumentParser(
        prog="text2mujoco",
        description="Generate and run MuJoCo scenes from structured specs or prompts.",
    )
    parser.add_argument("--debug", action="store_true", help="Show full traceback on errors.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("doctor", help="Print Python, package, and API-key diagnostics.")

    baseline = subparsers.add_parser("baseline", help="Run the deterministic push-world demo.")
    _add_mode_flags(baseline)

    arm_baseline = subparsers.add_parser(
        "arm-baseline", help="Run the deterministic robot-arm pick-and-place demo."
    )
    _add_mode_flags(arm_baseline)

    subparsers.add_parser("arm-chat", help="Open a robot-arm natural-language chat window.")

    arm_prompt = subparsers.add_parser(
        "arm-prompt", help="Run one natural-language robot-arm prompt."
    )
    arm_prompt.add_argument("--prompt", required=True, help="Robot-arm instruction.")
    _add_mode_flags(arm_prompt)

    generate = subparsers.add_parser("generate", help="Generate a push-world SceneSpec.")
    generate.add_argument("--prompt", required=True, help="Natural-language scene description.")
    generate.add_argument(
        "--no-run", action="store_true", help="Save SceneSpec and MJCF without running physics."
    )
    _add_mode_flags(generate)

    run = subparsers.add_parser("run", help="Run an existing push-world SceneSpec JSON.")
    run.add_argument("--spec", required=True, type=Path, help="Path to scene_spec.json.")
    _add_mode_flags(run)

    validate = subparsers.add_parser("validate", help="Validate a push-world SceneSpec JSON.")
    validate.add_argument("--spec", required=True, type=Path, help="Path to scene_spec.json.")
    return parser


def _add_mode_flags(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--headless", action="store_true", help="Run physics without GUI.")
    group.add_argument("--viewer", action="store_true", help="Open the MuJoCo Viewer.")


def _mode(args: argparse.Namespace) -> str:
    return "viewer" if getattr(args, "viewer", False) else "headless"


def command_doctor(settings: Settings) -> int:
    """Print environment diagnostics without exposing secrets."""

    _write(f"Python: {platform.python_version()} ({sys.executable})")
    _write(f"OS: {platform.platform()}")
    for module in ["mujoco", "numpy", "pydantic", "openai", "pytest", "ruff"]:
        available = importlib.util.find_spec(module) is not None
        _write(f"{module}: {'OK' if available else 'MISSING'}")
    _write(f"OPENAI_API_KEY: {'set' if settings.has_api_key else 'not set'}")
    _write(f"OPENAI_MODEL: {settings.openai_model}")
    _write(f"Artifact directory: {settings.artifact_dir}")
    return 0


def command_baseline(args: argparse.Namespace, settings: Settings) -> int:
    """Run the deterministic baseline push-world scene."""

    result = run_push_simulation(
        baseline_scene(),
        artifact_dir=settings.artifact_dir,
        mode=_mode(args),
        prompt=None,
        model_name=None,
    )
    _print_result(
        result.artifacts.run_dir, result.metrics.success, result.metrics.termination_reason
    )
    return 0


def command_arm_baseline(args: argparse.Namespace, settings: Settings) -> int:
    """Run the deterministic robot-arm pick-and-place scene."""

    from text2mujoco.arm_schemas import baseline_arm_scene
    from text2mujoco.arm_simulation import run_arm_simulation

    result = run_arm_simulation(
        baseline_arm_scene(),
        artifact_dir=settings.artifact_dir,
        mode=_mode(args),
    )
    _write(
        "Robot arm run complete: "
        f"success={result.metrics.success}, reason={result.metrics.termination_reason}"
    )
    _write(f"artifact: {result.artifacts.run_dir}")
    return 0


def command_arm_chat(settings: Settings) -> int:
    """Open the natural-language robot-arm chat window."""

    from text2mujoco.arm_chat_app import main as arm_chat_main

    return arm_chat_main([])


def command_arm_prompt(args: argparse.Namespace, settings: Settings) -> int:
    """Run one natural-language robot-arm prompt."""

    from text2mujoco.arm_chat_app import format_prompt_summary, run_arm_prompt

    result = run_arm_prompt(
        args.prompt,
        settings=settings,
        launch_viewer=_mode(args) == "viewer",
    )
    _write(format_prompt_summary(result))
    return 0


def command_validate(args: argparse.Namespace) -> int:
    """Validate a SceneSpec JSON file."""

    spec = load_scene_spec(args.spec)
    report = validate_scene(spec)
    _write(
        "Validation OK: "
        f"pusher start=({report.pusher_start.x:.3f}, {report.pusher_start.y:.3f})"
    )
    return 0


def command_run(args: argparse.Namespace, settings: Settings) -> int:
    """Run an existing SceneSpec JSON file."""

    spec = load_scene_spec(args.spec)
    result = run_push_simulation(
        spec,
        artifact_dir=settings.artifact_dir,
        mode=_mode(args),
        prompt=None,
        model_name=None,
    )
    _print_result(
        result.artifacts.run_dir, result.metrics.success, result.metrics.termination_reason
    )
    return 0


def command_generate(args: argparse.Namespace, settings: Settings) -> int:
    """Generate a SceneSpec with OpenAI structured output and optionally run it."""

    spec = OpenAISceneGenerator(settings=settings).generate(args.prompt)
    if args.no_run:
        from text2mujoco.metrics import SimulationMetrics, save_run_artifacts
        from text2mujoco.mjcf_builder import MJCFBuilder

        scene_xml = MJCFBuilder().build(spec)
        metrics = SimulationMetrics(
            success=False,
            terminated=False,
            truncated=False,
            termination_reason="not_run",
            simulation_time=0.0,
            wall_clock_time=0.0,
            final_box_target_distance=spec.box_position.distance_to(spec.target_position),
            minimum_box_target_distance=spec.box_position.distance_to(spec.target_position),
            control_steps=0,
            physics_steps=0,
            maximum_speed=0.0,
            stability_status="not_run",
        )
        artifacts = save_run_artifacts(
            artifact_dir=settings.artifact_dir,
            spec=spec,
            scene_xml=scene_xml,
            metrics=metrics,
            mode=_mode(args),
            prompt=args.prompt,
            model_name=settings.openai_model,
            log_lines=[
                "spec generated",
                "spec validated",
                "MJCF built",
                "not run",
                "artifacts saved",
            ],
        )
        _write(f"Generated: {artifacts.run_dir}")
        return 0

    result = run_push_simulation(
        spec,
        artifact_dir=settings.artifact_dir,
        mode=_mode(args),
        prompt=args.prompt,
        model_name=settings.openai_model,
    )
    _print_result(
        result.artifacts.run_dir, result.metrics.success, result.metrics.termination_reason
    )
    return 0


def _print_result(run_dir: Path, success: bool, reason: str) -> None:
    _write(f"Run complete: success={success}, reason={reason}")
    _write(f"artifact: {run_dir}")


def _die(parser: argparse.ArgumentParser, args: argparse.Namespace, exc: Exception) -> NoReturn:
    if getattr(args, "debug", False):
        traceback.print_exception(exc)
    else:
        parser.exit(2, f"Error: {exc}\n")
    raise SystemExit(2)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    parser = build_parser()
    args = parser.parse_args(argv)
    settings = Settings.from_env()
    try:
        if args.command == "doctor":
            return command_doctor(settings)
        if args.command == "baseline":
            return command_baseline(args, settings)
        if args.command == "arm-baseline":
            return command_arm_baseline(args, settings)
        if args.command == "arm-chat":
            return command_arm_chat(settings)
        if args.command == "arm-prompt":
            return command_arm_prompt(args, settings)
        if args.command == "validate":
            return command_validate(args)
        if args.command == "run":
            return command_run(args, settings)
        if args.command == "generate":
            return command_generate(args, settings)
    except Text2MujocoError as exc:
        _die(parser, args, exc)
    parser.error(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
