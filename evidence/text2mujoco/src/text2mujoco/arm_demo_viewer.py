"""Slow looping viewer for the robot-arm pick-and-place demo."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import mujoco
import mujoco.viewer

from text2mujoco.arm_controller import ArmPickPlaceController, ArmState
from text2mujoco.arm_mjcf_builder import ArmMJCFBuilder
from text2mujoco.arm_schemas import baseline_arm_scene, load_arm_scene_spec
from text2mujoco.arm_simulation import (
    apply_command,
    compile_arm_model,
    initialize_arm_state,
    resolve_arm_handles,
)


def latest_arm_spec(artifact_dir: Path) -> Path | None:
    """Find newest robot-arm scene spec."""

    specs = sorted(
        artifact_dir.glob("*_arm_*/scene_spec.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return specs[0] if specs else None


def run_demo(spec_path: Path | None, *, speed: float) -> None:
    """Run a slow looping visible demo."""

    spec = load_arm_scene_spec(spec_path) if spec_path else baseline_arm_scene()
    model, data = compile_arm_model(ArmMJCFBuilder().build(spec))
    handles = resolve_arm_handles(model)
    controller = ArmPickPlaceController(spec)
    initialize_arm_state(model, data, spec, handles)

    with mujoco.viewer.launch_passive(model, data) as viewer:
        viewer.cam.type = mujoco.mjtCamera.mjCAMERA_FREE
        viewer.cam.distance = 1.25
        viewer.cam.azimuth = 120
        viewer.cam.elevation = -35
        while viewer.is_running():
            command = controller.compute(dt=spec.timestep)
            apply_command(data, handles, command)
            mujoco.mj_step(model, data)
            viewer.sync()
            time.sleep(max(spec.timestep / max(speed, 0.05), 0.001))
            if command.state is ArmState.SUCCESS:
                time.sleep(0.8)
                controller = ArmPickPlaceController(spec)
                initialize_arm_state(model, data, spec, handles)


def main(argv: list[str] | None = None) -> int:
    """Entry point."""

    parser = argparse.ArgumentParser(description="Visible robot-arm pick-and-place demo.")
    parser.add_argument(
        "--spec", type=Path, help="SceneSpec JSON path. Defaults to latest arm artifact."
    )
    parser.add_argument("--artifact-dir", type=Path, default=Path("artifacts"))
    parser.add_argument(
        "--speed", type=float, default=0.25, help="Playback speed. 0.25 is 4x slower."
    )
    args = parser.parse_args(argv)
    spec_path = args.spec or latest_arm_spec(args.artifact_dir)
    print("Running robot arm pick-and-place demo.")
    print("Mode: contact-only MuJoCo grasp, no cube teleport and no weld constraint.")
    print("Close the MuJoCo Viewer window to exit.")
    run_demo(spec_path, speed=args.speed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
