# Architecture

## 데이터 흐름

사용자 prompt는 `llm_client.OpenAISceneGenerator`로 들어갑니다. OpenAI Responses API는 Pydantic `SceneSpec` structured output만 반환합니다. 이후 `validation.validate_scene()`이 숫자 범위, 공간 관계, pusher 시작점, 힘의 타당성을 검사합니다. 검증된 spec만 `MJCFBuilder`로 전달되어 MuJoCo XML이 생성됩니다.

## SceneSpec이 필요한 이유

LLM이 직접 Python 코드나 XML을 만들면 실행 가능한 공격면이 커지고, 물리적으로 불가능한 장면도 섞일 수 있습니다. `SceneSpec`은 LLM 출력을 작은 숫자와 색상, 위치, 질량 값으로 제한합니다. 이 구조 덕분에 Pydantic 문법 검증과 별도 의미 검증을 모두 적용할 수 있습니다.

## LLM XML 직접 생성을 금지하는 이유

MJCF XML은 actuator, joint, body inertia, collision 설정이 조금만 틀려도 compile 실패나 unstable simulation을 만들 수 있습니다. 이 프로젝트는 XML을 deterministic builder 한 곳에서만 만들고, LLM이 만든 임의 XML은 실행하지 않습니다.

## mjModel과 mjData

`mjModel`은 compile된 MuJoCo 모델의 정적 구조입니다. body, joint, actuator 이름과 주소가 들어 있습니다. `mjData`는 현재 simulation state입니다. `qpos`, `qvel`, `qacc`, `ctrl`, body world position 등이 여기에 들어 있습니다.

## qpos, qvel, ctrl

코드는 `qpos[0]` 같은 매직 인덱스에 의존하지 않습니다. `mujoco.mj_name2id`, `model.jnt_qposadr`, `model.jnt_dofadr`로 `pusher_x`, `pusher_y`, `box_free`, `move_x`, `move_y` 주소를 찾습니다.

## timestep

기본 timestep은 `0.002`초입니다. controller는 물리 step마다 갱신하지 않고 `control_hz`와 timestep으로 계산한 decimation 주기에 맞춰 actuator target을 갱신합니다.

## actuator

pusher는 X/Y slide joint 두 개와 position actuator 두 개를 갖습니다. actuator control 값은 원하는 X/Y 위치이고, `ctrlrange`와 `forcerange`로 제한됩니다.

## Controller State Machine

`PushController`는 다음 상태를 사용합니다.

- `INITIALIZE`
- `APPROACH`
- `ALIGN`
- `PUSH`
- `HOLD`
- `SUCCESS`
- `FAILED`

상자에서 목표까지 방향벡터를 구하고, 목표 반대편 behind point로 이동한 뒤, 상자를 목표 방향으로 미는 방식입니다.

## Headless와 Viewer

headless 실행은 렌더링을 사용하지 않고 `mj_step()`만 수행합니다. CI나 Codex 환경에서도 검증 가능합니다. viewer 실행은 `mujoco.viewer.launch_passive()`를 사용하며 GUI가 가능한 로컬 환경에서만 확인합니다.

## 모듈 책임

- `schemas.py`: Pydantic schema, JSON load/save, baseline scene.
- `validation.py`: semantic validation and pusher geometry.
- `mjcf_builder.py`: deterministic MJCF generation.
- `controller.py`: rule-based pusher state machine.
- `simulation.py`: model compile, named lookup, reset, run loop.
- `environment.py`: RL 확장용 reset/step/reward 인터페이스.
- `metrics.py`: metrics, manifest, artifact 저장.
- `llm_client.py`: OpenAI Responses API structured output.
- `cli.py`: 사용자 명령어와 오류 요약.
