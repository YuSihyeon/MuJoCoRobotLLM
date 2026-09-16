# Arm LLM Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a small LLM-backed chat window that turns natural-language robot-arm instructions into validated contact-only MuJoCo pick-and-place simulations.

**Architecture:** Natural language is converted into a bounded `ArmActionSpec`, then applied to `ArmSceneSpec`. The LLM never emits Python or MJCF; it only emits structured action parameters. The chat UI runs a headless validation simulation, reports metrics, and launches the existing MuJoCo viewer with the generated scene spec.

**Tech Stack:** Python 3.13, Pydantic v2, OpenAI Responses structured output via existing `settings.py`, Tkinter, MuJoCo Python viewer, pytest, ruff.

## Global Constraints

- Preserve contact-only object motion: `assisted_grasp=false` and `constraint_grasp=false`.
- Do not let LLM output executable code or arbitrary MJCF.
- Support local rule-based parsing when `OPENAI_API_KEY` is not set.
- Keep generated robot-arm scenes inside the validated table workspace.
- Open a visible MuJoCo Viewer after the chat prompt is accepted.

---

### Task 1: Natural-Language Action Model

**Files:**
- Create: `src/text2mujoco/arm_actions.py`
- Test: `tests/test_arm_actions.py`

**Interfaces:**
- Produces: `ArmActionSpec`, `parse_arm_action_locally(prompt: str) -> ArmActionSpec`, `apply_action_to_scene(action: ArmActionSpec, base: ArmSceneSpec | None = None) -> ArmSceneSpec`
- Consumes: `baseline_arm_scene`, `ArmSceneSpec`

- [ ] **Step 1: Write failing parser and scene tests**
  - Assert Korean and English phrases map to safe speed, drop height, mass, friction, and target coordinates.
  - Assert applying the action returns an `ArmSceneSpec` with contact-only-compatible controller settings.

- [ ] **Step 2: Run tests to verify failure**
  - Run: `python -m pytest tests/test_arm_actions.py -q`
  - Expected: import failure for missing `arm_actions`.

- [ ] **Step 3: Implement action model and local parser**
  - Use Pydantic fields with bounded target coordinates, drop height, mass, and friction.
  - Clamp local keyword mappings by constructing `ArmActionSpec`.

- [ ] **Step 4: Run tests to verify pass**
  - Run: `python -m pytest tests/test_arm_actions.py -q`
  - Expected: all tests pass.

### Task 2: Optional LLM Structured Parser

**Files:**
- Modify: `src/text2mujoco/arm_actions.py`
- Test: `tests/test_arm_actions.py`

**Interfaces:**
- Produces: `OpenAIArmActionGenerator.generate(prompt: str) -> ArmActionSpec`, `generate_arm_action(prompt: str, settings: Settings, client: OpenAIClientProtocol | None = None) -> tuple[ArmActionSpec, str]`

- [ ] **Step 1: Write failing fake-client tests**
  - Assert a fake Responses parser can return `ArmActionSpec`.
  - Assert missing API key falls back to local parsing and source `"local"`.

- [ ] **Step 2: Run tests to verify failure**
  - Run: `python -m pytest tests/test_arm_actions.py -q`
  - Expected: missing generator symbols.

- [ ] **Step 3: Implement structured LLM parser**
  - Reuse existing OpenAI client style from `llm_client.py`.
  - Validate by constructing `ArmActionSpec` and applying it to a scene.

- [ ] **Step 4: Run tests to verify pass**
  - Run: `python -m pytest tests/test_arm_actions.py -q`
  - Expected: all tests pass.

### Task 3: Chat Runner And Tkinter UI

**Files:**
- Create: `src/text2mujoco/arm_chat_app.py`
- Test: `tests/test_arm_chat_app.py`

**Interfaces:**
- Produces: `run_arm_prompt(prompt: str, settings: Settings, launch_viewer: bool = True) -> ArmPromptRun`
- Produces: `main(argv: list[str] | None = None) -> int`

- [ ] **Step 1: Write failing runner tests**
  - Assert `run_arm_prompt(..., launch_viewer=False)` uses a fake runner and returns a summary with source, success, artifact path, and metrics.

- [ ] **Step 2: Run tests to verify failure**
  - Run: `python -m pytest tests/test_arm_chat_app.py -q`
  - Expected: import failure for missing module.

- [ ] **Step 3: Implement runner and Tkinter app**
  - Keep simulation work off the Tkinter main thread.
  - Launch viewer as a subprocess after the headless validation simulation succeeds.

- [ ] **Step 4: Run tests to verify pass**
  - Run: `python -m pytest tests/test_arm_chat_app.py -q`
  - Expected: all tests pass.

### Task 4: CLI And Launchers

**Files:**
- Modify: `src/text2mujoco/cli.py`
- Create: `open_robot_arm_chat.ps1`
- Create: `open_robot_arm_chat.cmd`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces CLI command: `python -m text2mujoco arm-chat`
- Produces CLI command: `python -m text2mujoco arm-prompt --prompt "..."`

- [ ] **Step 1: Write failing CLI parser tests**
  - Assert parser accepts `arm-chat`.
  - Assert parser accepts `arm-prompt --prompt "..." --headless`.

- [ ] **Step 2: Run tests to verify failure**
  - Run: `python -m pytest tests/test_cli.py -q`
  - Expected: parser rejects new commands.

- [ ] **Step 3: Implement CLI and launchers**
  - Add `command_arm_chat` and `command_arm_prompt`.
  - Add PowerShell and cmd launchers.

- [ ] **Step 4: Run full verification**
  - Run: `python -m pytest -q`
  - Run: `python -m ruff check . --no-cache`
  - Run: `python -m text2mujoco arm-prompt --prompt "Move the red cube to the green target slowly and drop it from slightly above." --headless`

