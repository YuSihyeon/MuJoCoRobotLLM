# Text-to-MuJoCo Push World Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an installable, tested MuJoCo push-world generator and runner from constrained SceneSpec objects.

**Architecture:** Implement a narrow LLM boundary, strict schema, semantic validator, deterministic MJCF builder, named MuJoCo access layer, deterministic pusher controller, artifact writer, and beginner-friendly CLI/docs.

**Tech Stack:** Python 3.12+, MuJoCo official Python package, NumPy, Pydantic v2, OpenAI Python SDK, pytest, ruff.

## Global Constraints

- Do not execute LLM-generated Python code.
- Do not execute LLM-generated XML.
- Do not store real API keys in source, tests, logs, or artifacts.
- Use `pathlib.Path` for paths.
- Tests must not call the network or real OpenAI API.
- `python -m ruff check .`, `python -m ruff format --check .`, `python -m pytest -q`, and `python -m text2mujoco baseline --headless` must pass or be reported with exact blockers.

---

### Task 1: Tests And Package Shell

**Files:**
- Create: `pyproject.toml`, `AGENTS.md`, `.gitignore`, `.env.example`, `src/text2mujoco/__init__.py`
- Create tests under `tests/`

**Interfaces:**
- Produces expected public modules and function names for subsequent tasks.

- [x] Write failing schema, validation, MJCF, controller, simulation, and LLM tests.
- [x] Run tests to verify the missing modules fail before production implementation.

### Task 2: Core Types And Validation

**Files:**
- Create: `src/text2mujoco/errors.py`
- Create: `src/text2mujoco/schemas.py`
- Create: `src/text2mujoco/validation.py`

**Interfaces:**
- `SceneSpec`, `Vec2`, `Vec3`, `RgbColor`, `ControllerConfig`
- `baseline_scene() -> SceneSpec`
- `load_scene_spec(path: Path) -> SceneSpec`
- `validate_scene(spec: SceneSpec, *, include_mujoco: bool = True) -> ValidationReport`
- `compute_pusher_start(spec: SceneSpec) -> Vec2`

- [x] Implement strict Pydantic models and semantic validation until schema and validation tests pass.

### Task 3: MJCF And MuJoCo Runtime

**Files:**
- Create: `src/text2mujoco/mjcf_builder.py`
- Create: `src/text2mujoco/simulation.py`
- Create: `src/text2mujoco/environment.py`

**Interfaces:**
- `MJCFBuilder().build(spec: SceneSpec) -> str`
- `compile_model(xml: str) -> tuple[mujoco.MjModel, mujoco.MjData]`
- `resolve_handles(model: mujoco.MjModel) -> ModelHandles`
- `PushEnvironment.reset(seed: int | None = None) -> dict[str, list[float]]`

- [x] Implement deterministic MJCF, named lookup, reset, finite smoke stepping, and environment API until MJCF/simulation tests pass.

### Task 4: Controller And Metrics

**Files:**
- Create: `src/text2mujoco/controller.py`
- Create: `src/text2mujoco/metrics.py`

**Interfaces:**
- `PushController.compute_action(observation: Observation, simulation_time: float) -> np.ndarray`
- `run_push_simulation(spec: SceneSpec, *, artifact_dir: Path, mode: RunMode, prompt: str | None = None) -> SimulationResult`
- `save_run_artifacts(...) -> RunArtifacts`

- [x] Implement state machine, saturation, success hold, timeout, metrics, and artifact writing.

### Task 5: OpenAI Client And CLI

**Files:**
- Create: `src/text2mujoco/settings.py`
- Create: `src/text2mujoco/llm_client.py`
- Create: `src/text2mujoco/cli.py`
- Create: `src/text2mujoco/__main__.py`

**Interfaces:**
- `Settings.from_env() -> Settings`
- `OpenAISceneGenerator.generate(prompt: str) -> SceneSpec`
- CLI subcommands: `doctor`, `baseline`, `generate`, `run`, `validate`

- [x] Implement Responses API structured output with `text_format=SceneSpec`, semantic retry, no-key error path, doctor, and command error summaries.

### Task 6: Korean Docs And Final Verification

**Files:**
- Expand: `README.md`
- Create: `docs/ARCHITECTURE.md`, `docs/EXPERIMENTS.md`, `docs/TROUBLESHOOTING.md`

**Interfaces:**
- User-facing docs are Korean and include Windows PowerShell commands.

- [x] Run install, ruff format/check, pytest, baseline headless, validate saved spec, and run saved spec.
- [x] Record GUI/API limitations honestly in final report.
