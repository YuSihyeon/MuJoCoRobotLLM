# World Scene Prompt Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the robot-arm chat accept a user scene/action prompt, convert it into a bounded virtual-world spec, compile that into MuJoCo, and run the contact-based physics simulation.

**Architecture:** Add a `WorldSceneSpec` layer in front of the existing arm simulation. The LLM, or a clearly labeled limited local fallback, returns validated scene/task data; an adapter maps that into `ArmSceneSpec`; the MJCF builder renders dynamic object shape, color, mass, friction, and static scene props.

**Tech Stack:** Python 3.13, Pydantic, MuJoCo, Tkinter, pytest, ruff.

## Global Constraints

- Do not execute Python, MJCF, or arbitrary code returned by an LLM.
- Keep generated scenes bounded to reachable tabletop robot-arm physics.
- Preserve contact-only object motion: no weld constraints and no teleporting object behavior.
- Show whether a prompt came from `llm` or the `local-limited` fallback.

---

### Task 1: World Scene Schema And Parser

**Files:**
- Create: `src/text2mujoco/world_scenes.py`
- Test: `tests/test_world_scenes.py`

**Interfaces:**
- Produces: `WorldSceneSpec`, `WorldObjectSpec`, `WorldStaticPropSpec`, `parse_world_scene_locally(prompt)`, `generate_world_scene(prompt, settings, client=None)`, `world_to_arm_scene(world)`.

- [ ] Write failing tests for Korean/English prompts producing shape, color, task, floor friction, drop height, and static props.
- [ ] Run the new tests and confirm imports fail before implementation.
- [ ] Implement bounded Pydantic models, local parsing, OpenAI structured-output parsing, and the arm-scene adapter.
- [ ] Run the new tests and confirm they pass.

### Task 2: Arm MJCF Dynamic Scene Rendering

**Files:**
- Modify: `src/text2mujoco/arm_schemas.py`
- Modify: `src/text2mujoco/arm_mjcf_builder.py`
- Test: `tests/test_arm_mjcf_builder.py`

**Interfaces:**
- Consumes: `ArmSceneSpec.object_shape`, `ArmSceneSpec.static_props`.
- Produces: MJCF with box, cylinder, sphere dynamic objects and bounded static props.

- [ ] Write failing tests for cylinder/sphere object geoms and static prop geoms.
- [ ] Run the focused tests and confirm they fail.
- [ ] Add shape/static-prop fields and render them into MJCF with collision settings.
- [ ] Run focused tests and confirm they pass.

### Task 3: Chat And CLI Wiring

**Files:**
- Modify: `src/text2mujoco/arm_chat_app.py`
- Modify: `src/text2mujoco/cli.py`
- Test: `tests/test_arm_chat_app.py`

**Interfaces:**
- Consumes: `generate_world_scene` and `world_to_arm_scene`.
- Produces: `run_arm_prompt()` results that include the world scene and source label.

- [ ] Write failing tests proving `run_arm_prompt()` uses world scene generation and summaries show scene/task details.
- [ ] Run focused tests and confirm they fail.
- [ ] Replace the old action-only path with the world-scene path and fix readable Korean UI copy.
- [ ] Run focused tests and confirm they pass.

### Task 4: Verification And Launch

**Files:**
- No source changes unless verification exposes a defect.

**Interfaces:**
- Produces: a runnable chat window and a sample generated MuJoCo artifact.

- [ ] Run `python -m pytest -q`.
- [ ] Run `python -m ruff check . --no-cache`.
- [ ] Run a headless sample `arm-prompt` command.
- [ ] Launch the chat UI for the user.
