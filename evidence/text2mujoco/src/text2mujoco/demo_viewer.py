"""Slow, looping MuJoCo viewer demo for the rule-based push controller."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import mujoco
import mujoco.viewer
import numpy as np

from text2mujoco.controller import PushController
from text2mujoco.mjcf_builder import MJCFBuilder
from text2mujoco.schemas import SceneSpec, baseline_scene, load_scene_spec
from text2mujoco.simulation import (
    body_xy,
    compile_model,
    initialize_state,
    make_observation,
    resolve_handles,
)


def latest_scene_spec(artifact_dir: Path) -> Path | None:
    """Return the newest saved scene_spec.json, if one exists."""

    specs = sorted(
        artifact_dir.glob("*/scene_spec.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return specs[0] if specs else None


def run_demo(spec: SceneSpec, *, speed: float, loop: bool) -> None:
    """Run the controller in a visible MuJoCo viewer at a slow demo speed."""

    model, data = compile_model(MJCFBuilder().build(spec))
    handles = resolve_handles(model)
    controller = PushController(spec)
    initialize_state(model, data, spec, handles)
    control_decimation = max(1, round(1.0 / (spec.controller.control_hz * spec.timestep)))

    with mujoco.viewer.launch_passive(model, data) as viewer:
        viewer.cam.type = mujoco.mjtCamera.mjCAMERA_FREE
        viewer.cam.distance = spec.arena_half_size * 2.5
        viewer.cam.azimuth = 90
        viewer.cam.elevation = -60

        step_index = 0
        last_reset = time.perf_counter()
        while viewer.is_running():
            if step_index % control_decimation == 0:
                action = controller.compute_action(make_observation(data, handles, spec), data.time)
                data.ctrl[handles.move_x_actuator] = float(action[0])
                data.ctrl[handles.move_y_actuator] = float(action[1])

            mujoco.mj_step(model, data)
            viewer.sync()

            box_position = body_xy(data, handles.box_body)
            distance = float(np.linalg.norm(spec.target_position.array - box_position))
            success = controller.update_success_hold(distance <= spec.target_radius, spec.timestep)
            timed_out = data.time >= spec.simulation_duration

            if success or timed_out:
                if not loop:
                    while viewer.is_running():
                        viewer.sync()
                        time.sleep(0.05)
                    return
                if time.perf_counter() - last_reset > 1.5:
                    controller = PushController(spec)
                    initialize_state(model, data, spec, handles)
                    step_index = 0
                    last_reset = time.perf_counter()
                    continue

            step_index += 1
            time.sleep(max(spec.timestep / max(speed, 0.05), 0.001))


def build_parser() -> argparse.ArgumentParser:
    """Build the demo viewer argument parser."""

    parser = argparse.ArgumentParser(description="Slow looping MuJoCo push-world viewer demo.")
    parser.add_argument(
        "--spec", type=Path, help="SceneSpec JSON path. Defaults to latest artifact."
    )
    parser.add_argument("--artifact-dir", type=Path, default=Path("artifacts"))
    parser.add_argument(
        "--speed", type=float, default=0.2, help="Playback speed. 0.2 is 5x slower."
    )
    parser.add_argument(
        "--no-loop", action="store_true", help="Do not restart after success/timeout."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the demo viewer."""

    args = build_parser().parse_args(argv)
    spec_path = args.spec or latest_scene_spec(args.artifact_dir)
    spec = load_scene_spec(spec_path) if spec_path else baseline_scene()
    print("MuJoCo controller demo를 실행합니다.")
    print("행동: 파란 pusher가 빨간 box 뒤로 이동한 뒤 초록 target 방향으로 밀어 넣습니다.")
    print("Viewer 창을 닫으면 종료됩니다.")
    run_demo(spec, speed=args.speed, loop=not args.no_loop)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
