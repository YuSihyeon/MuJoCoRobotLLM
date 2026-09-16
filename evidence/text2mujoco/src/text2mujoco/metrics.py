"""Run metrics and artifact serialization."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from text2mujoco.schemas import SceneSpec

RunMode = Literal["headless", "viewer"]


@dataclass(frozen=True)
class SimulationMetrics:
    """Simulation outcome metrics saved to metrics.json."""

    success: bool
    terminated: bool
    truncated: bool
    termination_reason: str
    simulation_time: float
    wall_clock_time: float
    final_box_target_distance: float
    minimum_box_target_distance: float
    control_steps: int
    physics_steps: int
    maximum_speed: float
    stability_status: str


@dataclass(frozen=True)
class RunArtifacts:
    """Paths created for one simulation run."""

    run_id: str
    run_dir: Path
    scene_spec_path: Path
    scene_xml_path: Path
    metrics_path: Path
    manifest_path: Path
    log_path: Path


@dataclass(frozen=True)
class SimulationResult:
    """Simulation metrics plus saved artifact paths."""

    metrics: SimulationMetrics
    artifacts: RunArtifacts
    scene_xml: str


def _json_default(value: object) -> str:
    if isinstance(value, Path):
        return str(value)
    msg = f"Object of type {type(value).__name__} is not JSON serializable"
    raise TypeError(msg)


def make_run_id(spec: SceneSpec, mode: RunMode) -> str:
    """Create a filesystem-safe run ID from time plus spec hash."""

    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    digest = hashlib.sha256(f"{mode}:{spec.model_dump_json(round_trip=True)}".encode()).hexdigest()[
        :8
    ]
    return f"{stamp}_{digest}"


def save_run_artifacts(
    *,
    artifact_dir: Path,
    spec: SceneSpec,
    scene_xml: str,
    metrics: SimulationMetrics,
    mode: RunMode,
    prompt: str | None,
    model_name: str | None,
    log_lines: list[str],
) -> RunArtifacts:
    """Write scene, metrics, manifest, and log files for a run."""

    run_id = make_run_id(spec, mode)
    run_dir = artifact_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    scene_spec_path = run_dir / "scene_spec.json"
    scene_xml_path = run_dir / "scene.xml"
    metrics_path = run_dir / "metrics.json"
    manifest_path = run_dir / "manifest.json"
    log_path = run_dir / "run.log"

    spec.to_json_file(scene_spec_path)
    scene_xml_path.write_text(scene_xml, encoding="utf-8")
    metrics_path.write_text(
        json.dumps(asdict(metrics), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    manifest = {
        "run_id": run_id,
        "schema_version": spec.schema_version,
        "generator_version": "text2mujoco-0.1.0",
        "input_prompt": prompt,
        "model_name": model_name,
        "seed": spec.seed,
        "mode": mode,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "files": {
            "scene_spec": scene_spec_path,
            "scene_xml": scene_xml_path,
            "metrics": metrics_path,
            "manifest": manifest_path,
            "run_log": log_path,
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )
    log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    return RunArtifacts(
        run_id=run_id,
        run_dir=run_dir,
        scene_spec_path=scene_spec_path,
        scene_xml_path=scene_xml_path,
        metrics_path=metrics_path,
        manifest_path=manifest_path,
        log_path=log_path,
    )
