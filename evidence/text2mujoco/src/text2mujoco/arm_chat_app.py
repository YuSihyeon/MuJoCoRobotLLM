"""Tkinter chat app for natural-language robot-arm simulation prompts."""

from __future__ import annotations

import argparse
import subprocess
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from text2mujoco.arm_schemas import ArmSceneSpec
from text2mujoco.arm_simulation import (
    ArmRunMode,
    ArmSimulationMetrics,
    ArmSimulationResult,
    run_arm_simulation,
)
from text2mujoco.settings import Settings
from text2mujoco.world_scenes import (
    WorldSceneSource,
    WorldSceneSpec,
    generate_world_scene,
    world_to_arm_scene,
)

DEFAULT_CHAT_PROMPT = "빨간 상자를 오른쪽 뒤로 천천히 옮기고 조금 위에서 떨어뜨려."


class SceneGenerator(Protocol):
    """Callable protocol for prompt-to-world-scene conversion."""

    def __call__(
        self, prompt: str, *, settings: Settings
    ) -> tuple[WorldSceneSpec, WorldSceneSource]:
        """Return a bounded world scene and its source."""


class SimulationRunner(Protocol):
    """Callable protocol for running a headless arm simulation."""

    def __call__(
        self, *, spec: ArmSceneSpec, artifact_dir: Path, mode: ArmRunMode
    ) -> ArmSimulationResult:
        """Run a simulation and return artifacts plus metrics."""


@dataclass(frozen=True)
class ArmPromptRun:
    """Result shown in the chat app after one prompt."""

    prompt: str
    world_scene: WorldSceneSpec
    scene_source: WorldSceneSource
    scene_spec: ArmSceneSpec
    metrics: ArmSimulationMetrics
    artifact_dir: Path
    scene_spec_path: Path
    viewer_started: bool


def launch_arm_viewer(scene_spec_path: Path) -> None:
    """Launch the visible MuJoCo viewer for a generated arm scene."""

    subprocess.Popen(  # noqa: S603 - arguments are fixed except a local generated path
        [
            sys.executable,
            "-m",
            "text2mujoco.arm_demo_viewer",
            "--spec",
            str(scene_spec_path),
            "--speed",
            "0.25",
        ],
        cwd=Path.cwd(),
    )


def normalize_chat_prompt(prompt: str) -> str:
    """Return user text or the default runnable prompt when the entry is empty."""

    return prompt.strip() or DEFAULT_CHAT_PROMPT


def run_arm_prompt(
    prompt: str,
    *,
    settings: Settings,
    scene_generator: SceneGenerator = generate_world_scene,
    simulation_runner: SimulationRunner = run_arm_simulation,
    viewer_launcher: Callable[[Path], None] = launch_arm_viewer,
    launch_viewer: bool = True,
) -> ArmPromptRun:
    """Convert a prompt to a physical scene, validate it headlessly, and optionally view it."""

    normalized_prompt = normalize_chat_prompt(prompt)
    world_scene, source = scene_generator(normalized_prompt, settings=settings)
    scene_spec = world_to_arm_scene(world_scene)
    result = simulation_runner(
        spec=scene_spec,
        artifact_dir=settings.artifact_dir,
        mode="headless",
    )
    viewer_started = False
    if launch_viewer:
        viewer_launcher(result.artifacts.scene_spec_path)
        viewer_started = True
    return ArmPromptRun(
        prompt=normalized_prompt,
        world_scene=world_scene,
        scene_source=source,
        scene_spec=scene_spec,
        metrics=result.metrics,
        artifact_dir=result.artifacts.run_dir,
        scene_spec_path=result.artifacts.scene_spec_path,
        viewer_started=viewer_started,
    )


def format_prompt_summary(result: ArmPromptRun) -> str:
    """Return a compact chat-readable simulation summary."""

    metrics = result.metrics
    obj = result.world_scene.manipulated_object
    task = result.world_scene.task
    return (
        f"source={result.scene_source}, contact-only, "
        f"scene={result.world_scene.environment_name}, task={task.kind}, object={obj.shape}, "
        f"success={metrics.success}, reason={metrics.termination_reason}, "
        f"target_distance={metrics.final_object_target_distance:.4f}m, "
        f"drop_bottom={metrics.release_object_bottom_height:.4f}m, "
        f"viewer={result.viewer_started}, artifact={result.artifact_dir}"
    )


class ArmChatWindow:
    """Small Tkinter UI that accepts robot-arm natural-language prompts."""

    def __init__(self, root: object, *, settings: Settings) -> None:
        import tkinter as tk
        from tkinter import ttk

        self.root = root
        self.settings = settings
        root.title("Text2MuJoCo Robot Arm Chat")
        root.geometry("760x480")

        frame = ttk.Frame(root, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        self.log = tk.Text(frame, height=20, wrap=tk.WORD)
        self.log.pack(fill=tk.BOTH, expand=True)
        self.log.configure(state=tk.DISABLED)

        entry_frame = ttk.Frame(frame)
        entry_frame.pack(fill=tk.X, pady=(10, 0))
        self.entry = ttk.Entry(entry_frame)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.insert(0, DEFAULT_CHAT_PROMPT)
        self.entry.focus_set()
        self.entry.bind("<Return>", lambda _event: self.submit())

        self.button = ttk.Button(entry_frame, text="Run", command=self.submit)
        self.button.pack(side=tk.LEFT, padx=(8, 0))

        self._append("입력창의 문장을 바꾸고 Run을 누르면 장면을 생성해 MuJoCo로 실행합니다.")
        self._append(f"Try: {DEFAULT_CHAT_PROMPT}")

    def _append(self, message: str) -> None:
        import tkinter as tk

        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def submit(self) -> None:
        """Handle the current prompt in a background thread."""

        prompt = normalize_chat_prompt(self.entry.get())
        self.entry.delete(0, "end")
        self.button.configure(state="disabled")
        self._append(f"\nUser: {prompt}")
        self._append("Generating a bounded scene and running contact-only MuJoCo physics...")

        def worker() -> None:
            try:
                result = run_arm_prompt(prompt, settings=self.settings)
                message = format_prompt_summary(result)
            except Exception as exc:  # noqa: BLE001 - show UI-friendly error
                message = f"Error: {exc}"
            self.root.after(0, lambda: self._finish(message))

        threading.Thread(target=worker, daemon=True).start()

    def _finish(self, message: str) -> None:
        self._append(f"Result: {message}")
        self.entry.insert(0, DEFAULT_CHAT_PROMPT)
        self.button.configure(state="normal")


def main(argv: list[str] | None = None) -> int:
    """Launch the robot-arm chat app."""

    parser = argparse.ArgumentParser(description="Robot-arm natural-language chat UI.")
    parser.parse_args(argv)
    import tkinter as tk

    root = tk.Tk()
    ArmChatWindow(root, settings=Settings.from_env())
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
