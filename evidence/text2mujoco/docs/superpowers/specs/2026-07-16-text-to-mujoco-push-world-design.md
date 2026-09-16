# Text-to-MuJoCo Push World Design

## Goal

Create an installable Python project that accepts Korean or English natural-language push-world descriptions, obtains a constrained Pydantic `SceneSpec` from OpenAI Responses structured outputs, validates the spec semantically and physically, builds deterministic MuJoCo MJCF, runs a 2D pusher controller, and saves artifacts.

## Architecture

The LLM boundary is intentionally narrow: OpenAI may produce only a `SceneSpec`; it never produces executable Python or raw MJCF. `schemas.py` owns the strict Pydantic contract, `validation.py` owns semantic and physical checks, `mjcf_builder.py` owns deterministic XML generation, `simulation.py` and `environment.py` own MuJoCo runtime state, `controller.py` owns deterministic pusher motion, and `metrics.py` owns artifact serialization.

## Data Flow

Natural-language prompt flows to `llm_client.OpenAISceneGenerator`, which calls `client.responses.parse(..., text_format=SceneSpec)`. Validated specs flow to `MJCFBuilder`, then to MuJoCo model compilation. The simulator resets named joints and bodies, runs the state-machine controller, evaluates success or termination, and writes `scene_spec.json`, `scene.xml`, `metrics.json`, `manifest.json`, and `run.log`.

## Error Handling

Project exceptions separate user-facing causes: `SceneValidationError`, `MJCFBuildError`, `SimulationStabilityError`, and `LLMConfigurationError`. CLI commands print concise Korean summaries by default and expose tracebacks only with `--debug`.

## Testing

Tests are offline by default. They cover strict schema parsing, NaN/Inf rejection, semantic geometry checks, deterministic MJCF generation, MuJoCo compile and finite stepping, named lookup, controller vector math and saturation, success hold and timeout behavior, mock LLM parsing, and missing API-key behavior.

## Constraints

The first version uses only Python, `mujoco`, `numpy`, `pydantic`, and `openai`; it avoids ROS2, Docker, WSL requirements, CUDA, PyTorch, reinforcement-learning libraries, `mujoco-py`, arbitrary LLM Python execution, and arbitrary LLM XML execution.
