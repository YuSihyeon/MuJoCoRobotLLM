# MuJoCo 로봇팔·자연어 제어 연구 아카이브


**독립 연구 저장소:** [GitHub](https://github.com/YuSihyeon/MuJoCoRobotLLM) · [전체 데이터와 복원 범위](DATA_AND_RESTORE.md) · [영상 갤러리](https://yusihyeon.github.io/MuJoCoRobotLLM/gallery.html)

이 연구는 **자연어를 제한된 데이터 구조로 해석한 뒤, 검증 가능한 제어기로 로봇을 움직이는 과정**을 탐색했다. 확인된 구현은 ① 독립 MuJoCo의 장면 생성·집기/놓기와 ② **Unreal Engine 5.7 + Unreal Robotics Lab + Panda + Python/LLM**의 두 계열이다. 폴더 식별자에는 초기 분류명 `unity`가 남아 있지만, 이 자료를 Unity 구현으로 소개하면 부정확하다. 로봇팔과 연결된 Unity 프로젝트·통신 코드는 조사 범위에서 확인하지 못했다.

2026-09-16에 보존된 로컬 소스, 설계문서, Git 상태, 실행 산출물을 대조했다. **과거 실행 기록**, **현재 코드에 구현된 기능**, **아직 검증하지 못한 주장**, **후속 개선 제안**을 구분한다. 관련 연구는 각각 독립 저장소로 정리했으며 이 저장소는 해당 연구의 기록만 다룬다.

## 1. 확인된 성과와 범위

| 구분 | 확인한 내용 | 근거와 해석 범위 |
|---|---|---|
| 장면 생성 | 한국어/영어 요청 → Pydantic 스키마 → 의미 검증 → 결정론적 MJCF | [아키텍처 원문](evidence/text2mujoco/docs/ARCHITECTURE.md), [LLM 클라이언트](evidence/text2mujoco/src/text2mujoco/llm_client.py) |
| 독립 MuJoCo 조작 | 사용자 정의 4자유도 팔과 두 손가락, IK·상태기계 기반 집기/놓기 | [팔 제어기](evidence/text2mujoco/src/text2mujoco/arm_controller.py), [물리 루프](evidence/text2mujoco/src/text2mujoco/arm_simulation.py) |
| 보조 없는 물리 기록 | 보존된 팔 실행 12회 중 9회에서 위치 보조·제약 보조가 모두 false이고 성공 기록 | [17개 과거 실행 인덱스](evidence/historical-run-index.json). 정해진 벤치마크의 성공률은 아님 |
| Unreal Panda 수동 제어 | 관절 목록 확인 → 8개 액추에이터 → 자세 보간 → 상태 확인 | [inspect_panda.py](evidence/panda-control/inspect_panda.py), [manual_panda.py](evidence/panda-control/manual_panda.py) |
| 명령 제어 | 한국어 별칭을 home/left/right/open/close로 매핑 | [panda_commands.py](evidence/panda-control/panda_commands.py). 이 단계는 규칙 기반 |
| LLM 제어 | 구조화된 최대 5개 동작 계획, 유효성 검사, 사용자 실행 확인 후 제어 | [llm_test.py](evidence/panda-control/llm_test.py), [panda_llm.py](evidence/panda-control/panda_llm.py) |
| 엔진 | `.uproject`의 EngineAssociation이 5.7, Panda/로봇 실험 맵과 에셋 존재 | [프로젝트 정의](evidence/unreal-project-skeleton/RobotLLM.uproject), [에셋 인벤토리](evidence/unreal-assets-inventory.json) |
| 현재 재현 | Python 파일 43개 구문 분석 통과. 기존 가상환경 실패 후 설치된 Python 3.13 환경에서 contact-only 팔 baseline 재실행 성공 | [초기 환경 점검](evidence/verification/recheck-results.json), [새 실행 지표](evidence/verification/reverified-baseline-20260916/metrics.json) |

실물 Franka 로봇을 구동한 기록, 강화학습을 학습한 결과, 장애물 회피나 범용 작업 계획의 성능 평가, Unity 연동 완료를 입증하는 자료는 이 묶음에 없다.

## 2. 연구 의도와 도구 선택

### 의도: 언어 해석과 물리 실행을 분리하기

독립 MuJoCo 설계문서는 LLM이 임의의 Python이나 MJCF를 직접 작성하지 않도록 하고, 작은 스키마의 위치·질량·마찰·색상 값을 반환하게 한다. 숫자 범위와 공간 관계를 검사한 뒤 단일 빌더가 XML을 만든다. 자유 생성의 표현력보다 컴파일 가능성, 원인 추적, 실행 재현을 우선한 선택이다. 이는 당시 [설계 및 구현 문서](evidence/text2mujoco/docs/superpowers/specs/2026-07-16-text-to-mujoco-push-world-design.md)에 명시된 방향이다.

Unreal Panda 코드에서는 이 원리가 동작 어휘 제한으로 나타난다. LLM은 관절각·힘·속도를 생성하지 않고 이미 작성된 `home`, `left`, `right`, `open`, `close`, `stop`, `unknown` 중에서 계획을 만든다. 실제 수치는 Python 상수와 보간기가 결정한다. 자연어 입력의 편의성을 추가하면서 물리 제어 경로를 작게 유지하려는 구현 구조다.

### 도구별 역할과 선택 근거

| 도구·구성 | 실제 역할 | 선택 이유를 말할 수 있는 수준 |
|---|---|---|
| MuJoCo | MJCF 컴파일, 접촉·마찰·중력·액추에이터 시뮬레이션, headless 평가 | 코드와 아키텍처에 직접 확인됨. 다른 엔진 대비 정량 비교는 없음 |
| Pydantic | 스키마, 수치 범위, 추가 필드 거부, 공간·도달성 검증 | LLM 출력을 검증 가능한 계약으로 만들기 위한 명시적 설계 |
| 사용자 정의 4자유도 팔 | base yaw, shoulder, elbow, wrist와 두 finger | [설계문서](evidence/text2mujoco/docs/superpowers/specs/2026-07-16-robot-arm-pick-place-design.md)는 산업용 전체 모델보다 구현·조정·테스트가 쉬운 가시적 데모를 선택했다고 설명 |
| Franka Emika Panda | Unreal 실험의 7개 팔 관절과 gripper 모델 | 실제 로봇 형태와 알려진 MJCF 자산을 사용한 구성. 다른 로봇과 비교 선발한 문서는 없음 |
| Unreal Engine 5.7 / URLab | 시각화, MJCF import, articulation과 원격 제어 서버 | 프로젝트·플러그인·맵·클라이언트 코드에서 확인. Unity보다 우수해서 선택했다는 기록은 없음 |
| OpenAI Responses structured output | 사용자 명령을 Pydantic 객체로 반환 | 코드에서 `responses.parse(..., text_format=...)` 사용 확인 |
| `gpt-5.4-mini` | Panda 계획 해석기의 코드상 모델명 | 실제 상수로 보존됨. 비용·지연·정확도 비교나 모델 선정 회의 기록은 없음 |
| `gpt-5.6` | text2mujoco 환경 설정의 기본 모델명 | `OPENAI_MODEL`로 변경 가능. 과거 모든 실행이 이 모델을 사용했다는 뜻은 아님 |
| ZeroMQ / MessagePack | Unreal과 Python의 로컬 RPC 및 상태 전달 | 설치된 upstream 클라이언트의 `connect()`·`step()` 구현 확인 |

소형 모델로 작은 동작 집합을 해석하는 구성이 비용·지연을 줄이는 데 적합할 수 있다는 설명은 **현재의 설계 분석**이다. 당시 실제 선정 동기나 측정 결과로 취급하지 않는다. 모델명은 보존 당시 코드의 설정이며, 현재 이용 가능성이나 권장 모델을 의미하지 않는다.

## 3. 진행 과정: 독립 MuJoCo 계열

기록의 날짜는 artifact의 UTC 생성 시각을 기준으로 한다. 파일 수정 시각은 보조 근거이며, 커밋이 없는 프로젝트에서 코드 변경 순서와 모든 시행착오를 완전히 복원할 수는 없다.

### 3.1 푸셔로 최소 물리 파이프라인 구성

초기 문제는 XY 평면의 pusher가 상자를 목표로 미는 것이었다. 파이프라인은 `SceneSpec → validate_scene → MJCFBuilder → PushController → metrics/manifest`로 구성된다. pusher는 X/Y slide joint와 position actuator를 갖고, body·joint·actuator 주소는 이름으로 조회한다. 상태기계는 접근, 정렬, 밀기, 유지와 성공/실패를 구분한다. 강화학습 정책은 사용하지 않는다.

첫 보존 실행 `20260716_015152_e8e8c4de`는 `unstable_speed`로 0.112초에 끝났다. 기록된 최대 속도는 약 4.0616이고 당시 임계값은 4.0이었다. 다음 spec은 최대 힘을 **90 → 12**, 목표 너머 밀기 거리를 **0.24 → 0.07**, 최대 속도 임계값을 **4 → 8**로 변경했다. 이후 같은 spec의 네 실행은 0.492초, 최종 목표 거리 약 0.067525m로 일치했다. [실패 metrics](evidence/historical-runs/20260716_015152_e8e8c4de/metrics.json), [성공 metrics](evidence/historical-runs/20260716_015349_456887a4/metrics.json), [전체 spec 차이](evidence/scene-spec-deltas.json)

힘·overshoot를 줄이고 종료 임계값도 동시에 변경했기 때문에, 성공을 특정 변경 하나의 인과 효과로 단정할 수 없다. 첫 metrics의 `stability_status`가 `stable`이더라도 `success=false`와 `unstable_speed`가 우선하는 작업 실패 기록이다. 이 필드는 수치의 유한성 상태와 작업 안정성 판정을 구분해서 읽어야 한다.

### 3.2 로봇팔과 집기/놓기 추가

다음 단계는 시각적으로 팔의 관절이 보이는 조작 데모였다. 팔 제어기는 목표의 수평 방향으로 base yaw를 계산하고, 반경–높이 평면의 두 링크 IK로 shoulder/elbow를 정한다. wrist와 각 관절은 범위 안으로 제한한다. 손가락은 양쪽 slide joint로 열리고 닫힌다.

```text
RESET → 물체 위 접근 → 내려가기 → 손가락 닫기 → 들어올리기
      → 목표 위 이동 → 놓을 높이로 내려가기 → 열기 → 후퇴 → SUCCESS
```

현재 컨트롤러는 시간에 따라 상태를 진행하고 경유점 사이를 `α²(3−2α)`로 부드럽게 보간한다. 물리 루프 안에서 LLM을 호출하지 않는다. 상태기계의 SUCCESS 도달만으로 최종 작업 성공이 되지는 않으며, 시뮬레이터가 거리·들어올림·테이블 관통 여부를 추가 검사한다.

### 3.3 보조 동작을 거쳐 접촉 물리로 발전

| 단계 | 보존 run 수 | 구체적 기록 | 해석 |
|---|---:|---|---|
| 직접 위치 보조 | 2 | `assisted_grasp=true`, 0.75초, 목표 거리 0 | 시퀀스·가시적 동작 확인용. 순수 물리 파지 성능으로 계산하면 안 됨 |
| 제약 보조 | 1 | `assisted_grasp=false`, `constraint_grasp=true`, 3.30초, 약 25.513mm | 위치 보조와는 다른 보조 조건. 현재 코드와 동일 조건 아님 |
| 접촉 기반 | 9 | 두 보조 모두 false, 5.30초 또는 7.00초, 약 0.715–6.573mm | 보존 metrics상 성공. 9개 독립 무작위 시도라는 뜻은 아님 |

첫 contact-only 기록으로 넘어갈 때 손가락 닫기 시간이 0.35→0.7초, 상태 유지 시간이 0.45→0.7초, 놓기 안정 시간이 0.35→0.55초, 팔 최대 힘이 80→140으로 바뀐다. 이후 `release_drop_height=0.035`가 추가되고, 느린 동작·가벼운 물체·목표 위치·마찰·원통 형태·선반 등을 바꾼 기록이 있다. 이는 [spec 차이](evidence/scene-spec-deltas.json)로 확인되는 수정 사항이며, 모든 차이에 대한 당시 설명이나 실패 동영상이 남은 것은 아니다.

현재 `run_arm_simulation()`은 `assisted_grasp`나 `constraint_grasp`가 true인 요청을 명시적으로 거부한다. 과거 보조 처리 함수와 내부 조건문 일부가 코드에 남아 있지만 공개 진입점에서는 비활성화되어 있다. 따라서 초기 보조 성공 기록을 현재 baseline의 검증 결과와 합쳐 주장하면 안 된다.

### 3.4 자연어 장면과 채팅 UI로 확장

[WorldSceneSpec](evidence/text2mujoco/src/text2mujoco/world_scenes.py)은 하나의 조작 물체, 테이블, 정적 소품, `pick_place` 작업을 표현한다. box/sphere/cylinder, 색상, 질량, 마찰, 목표와 속도 구분을 포함한다. “창고”나 “주방”이라는 환경명도 존재하지만, 실제 지원 공간은 **제한된 테이블 위 조작 환경**이다. 일반적인 실내 전체를 생성하는 월드 모델로 확대 해석하지 않는다.

채팅 UI의 현재 경로는 `generate_world_scene → world_to_arm_scene → headless 실행 → viewer 실행`이다. `arm_actions.py`의 간단한 동작 스키마도 남아 있으나 현재 채팅 앱은 더 큰 world-scene 계층을 호출한다. API 키가 없으면 공통 표현을 파싱하는 `local-limited` 경로를 사용하고, 결과 요약에 생성 출처를 표시한다. [채팅 앱](evidence/text2mujoco/src/text2mujoco/arm_chat_app.py)

“빨간 상자를 들어올렸다가 다시 그대로 내려놓아”라는 task_description이 남아 있는 마지막 실행의 spec은 물체 XY=(0.18, −0.12), 목표 XY=(0.22, 0.18)이다. 따라서 자연어 문장이 저장되었다는 사실만으로 “같은 자리에 내려놓기” 의미를 정확히 수행했다고 주장할 수 없다. 현재 구현이 제한된 pick-and-place 틀에 요청을 투영한다는 사례다. [해당 spec](evidence/historical-runs/20260717_221155_arm_a1545c32/scene_spec.json)

## 4. 진행 과정: Unreal Panda 계열

### 4.1 diffbot으로 연결 확인

[manual_diffbot.py](evidence/panda-control/manual_diffbot.py)는 좌우 바퀴에 같은 속도, 반대 속도, 후진 속도를 보내고 마지막에 0으로 만든다. [text_diffbot.py](evidence/panda-control/text_diffbot.py)는 전진·후진·좌우·정지 단어와 초 단위를 파싱한다. 기본 지속 시간 1.5초, 최대 5초, 속도 상수 3.0/2.0을 사용하며 동작 종료 시 정지 명령을 보낸다. 두 [diffbot XML](evidence/diffbot-models)은 외부 mesh 없이 단순 기하로 구성된 모델 자료다.

이 파일들은 네트워크 연결·actuator 이름·문자열 명령을 작게 시험한 기반으로 읽을 수 있다. 로봇팔보다 먼저 작성되었다는 방향은 로컬 수정 시각과 파일 구성에 부합하지만, 개발 대화 전체가 보존된 것은 아니다.

### 4.2 Panda 구조 확인과 수동 관절 제어

`inspect_panda.py`는 manager 존재, MuJoCo 버전, articulation 이름, joint와 actuator의 이름·타입·범위를 출력한다. `manual_panda.py`는 `panda_C_1`과 `actuator1`…`actuator8`을 명시적으로 찾는다. home 자세는 다음과 같다.

```text
[0, 0, 0, −1.57079, 0, 1.57079, −0.7853, 255]
```

앞의 7개 값은 팔 제어값이고 마지막은 gripper 제어값이다. 수동 시험은 첫 관절을 0.25rad로 움직였다가 home으로 돌아온다. 한 자세를 유지하거나 두 자세를 선형 보간하면서 대략 30Hz로 제어값을 전송하고 관절 위치를 출력한다. 전체 이동은 2초, 관찰용 유지 시간은 1초다. 이는 Cartesian 목표 IK 실험이 아니라 미리 정한 관절 목표의 기본 동작 확인이다.

### 4.3 규칙 명령 제어

`panda_commands.py`는 한국어 별칭을 정확히 매핑한다. left/right는 첫 관절 목표를 −0.35/+0.35rad로 설정한 고정 자세이다. “왼쪽”이라는 말이 세계 좌표의 일정 거리 이동을 의미하지 않는다. gripper는 0/255로 닫고 연다. 좌우 이동 시 gripper 상태를 유지하지만, 이 파일의 home 동작은 기본 HOME을 그대로 적용해 그리퍼도 열린다.

### 4.4 LLM 계획 검증과 실제 실행을 분리

`llm_test.py`는 구조화된 계획을 생성하고 검사하되 로봇에는 연결하지 않는다. `panda_llm.py`는 같은 계열의 계획을 실제 URLab 제어 경로에 연결한다. 후자는 다음 검사를 수행한다.

1. `RobotAction.name`을 일곱 종류의 Literal로 제한한다.
2. 비어 있는 계획, 5개 초과 동작, 하나라도 `unknown`인 계획을 거부한다.
3. 모든 자세의 길이와 액추에이터별 범위를 확인한다.
4. 계획을 표시하고 y/yes/예/응 확인을 받은 뒤 실행한다.
5. 한글/영문 정지 입력은 입력 대기 상태에서 LLM 호출 없이 처리한다.

LLM 시스템 프롬프트는 관절값·힘·속도의 직접 요청과 던지기·충돌 명령을 unknown으로 분류하도록 한다. 다만 이 자연어 분류 규칙 전체가 독립된 코드 검사로 구현된 것은 아니다. 실제 코드가 보장하는 것은 enum·개수·unknown·자세 범위 검사다.

이 버전의 home/left/right는 현재 gripper 제어값을 보존한다. open/close는 1초, 팔 자세 이동은 2초로 보간하고, 동작 뒤 0.3초 동안 유지한다. `current_pose`는 주로 마지막 목표값을 기억하는 변수이며, 각 동작 완료를 실제 관절 오차로 판정하는 제어는 아니다.

## 5. 통신 프로토콜과 제어 흐름

```text
한국어/영어 명령
  → OpenAI Responses API (RobotPlan)
  → 계획 검사 + 사용자 실행 확인
  → 고정 자세 선택 / gripper 값 변경
  → 관절 목표 보간 (약 30Hz)
  → actuator.set_ctrl()
  → URLabClient.step(n_steps=1)
  → 로컬 TCP 5559 / MessagePack RPC
  → Unreal URLab 서버 / AMjManager / MuJoCo
  → 관절 상태 반환 + Unreal 화면 갱신
```

실제 스크립트의 접속 설정은 `tcp://127.0.0.1`, `step_port=5559`, `step_mode="live"`, `mujoco_version_check=True`이다. `connect()`는 `hello`를 보내 MessagePack 인코딩을 지정하고 서버 모델 및 articulation 정보를 구성한다. 서버와 클라이언트의 MuJoCo 버전이 맞지 않으면 기본적으로 연결을 거부한다.

**live 모드에서 `step(n_steps=1)`은 Python 호출 한 번이 물리 step 한 번을 수행한다는 뜻이 아니다.** 설치된 upstream 구현에서는 Unreal이 물리를 자율적으로 진행하고 요청은 제어값을 적용하며 현재 상태를 읽는다. 따라서 Python의 30Hz 전송률과 MuJoCo 물리 적분 주기를 혼동하면 안 된다. upstream 문서에 별도로 등장하는 5555 상태, 5556 제어, 5558 카메라 PUB/SUB 포트를 이 스크립트의 5559 RPC 경로와 동일시하지 않는다.

LLM은 카메라 프레임이나 물리 상태를 읽고 경로를 재계획하지 않는다. 이 데모에서는 언어를 제한된 순차 동작으로 해석하는 역할이다. 가시적 로봇 상태가 계속 바뀌더라도 LLM의 폐루프 제어를 입증하지 않는다.

## 6. 실패·수정·호환성 단서

| 관찰 | 확인된 수정 또는 현재 상태 | 말할 수 없는 부분 |
|---|---|---|
| 푸셔 속도 임계 초과 | 힘·overshoot 감소, 속도 종료 임계값 증가 후 성공 기록 | 각각의 변경이 기여한 정도 |
| 초기 팔의 보조 사용 | 위치 보조 → 제약 보조 → 보조 없는 contact-only artifact | 중간 모든 실패와 튜닝 시도의 횟수 |
| Panda import 변형 | 원본 대비 mesh에 이름 추가, link1/link2 파일명 조정 등 56개 요소 속성 차이 | 실제 import 오류 메시지나 변경별 원인. [의미 차이](evidence/panda-import-delta.json) 참조 |
| bridge 패키지 변경 | upstream MuJoCo 3.8.1 핀을 3.10.0으로 변경, OpenAI>=2.46.0 추가 | 서버 build와 모든 선택 extras의 완전 호환성 |
| API 이름 변화 | 로컬 스크립트가 `discover()` 대신 `connect()`, `set_ctrl()` 사용 | 사용자가 실제로 겪은 오류 로그 전체 |
| URLab 테스트 제외 | 로컬 플러그인의 두 C++ 테스트 파일이 `.disabled`로 존재하고 Git에서는 원본 삭제로 표시 | 비활성화 이유, 엔진 테스트 전체 통과 여부 |
| API 할당량 오류 | LLM 영상 초반에 `429 insufficient_quota`가 나타난다는 영상 검토 관찰 | 이후 결제 상태나 모든 API 호출의 성공률 |

bridge는 [URLab-Sim/urlab_bridge](https://github.com/URLab-Sim/urlab_bridge), 플러그인은 [URLab-Sim/UnrealRoboticsLab](https://github.com/URLab-Sim/UnrealRoboticsLab), Panda 자산은 [MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie)에서 온 외부 기반이다. 해당 저장소 전체의 개발 성과를 이 연구의 독자 구현으로 주장하지 않는다. 확인한 로컬 HEAD는 각각 `c1fb34e`, `567cbd9`, `71f066a`이며, 사용자의 제어 스크립트 7개는 bridge 저장소에서 당시 untracked였다. `RobotLLM`과 `text2mujoco` 자체에서는 Git 저장소를 확인하지 못했다.

## 7. 결과를 읽는 방법

### 과거 정량 기록

17개 폴더의 metrics·spec·XML·manifest·log를 선별 삭제 없이 보존했다. 구성은 푸셔 5회와 팔 12회다. 팔의 마지막 9개 실행은 보조 없는 성공으로 기록되어 있고, 그 중 같은 spec을 반복한 실행도 있다. 물체와 목표의 최종 거리 값이 작아졌다는 것은 해당 환경의 작업 결과이며, 다양한 물체와 환경에서의 일반화 성능이나 계획 정확도는 아니다.

대표 기록:

| run | 조건 | 결과 |
|---|---|---|
| [015152](evidence/historical-runs/20260716_015152_e8e8c4de/metrics.json) | 초기 푸셔 | 실패, unstable_speed, 0.112초 |
| [015349](evidence/historical-runs/20260716_015349_456887a4/metrics.json) | 수정 푸셔 | 성공, 0.492초, 거리 67.525mm |
| [023036](evidence/historical-runs/20260716_023036_arm_d49f06e0/metrics.json) | 위치 보조 팔 | 성공, 0.750초, 거리 0; 보조 조건 명시 |
| [024938](evidence/historical-runs/20260716_024938_arm_c8964d4a/metrics.json) | 제약 보조 팔 | 성공, 3.300초, 거리 25.513mm |
| [043519](evidence/historical-runs/20260716_043519_arm_18e9bcf8/metrics.json) | contact-only 팔 | 성공, 5.300초, 거리 0.715mm |
| [054235](evidence/historical-runs/20260716_054235_arm_108be4f5/metrics.json) | 파란 원통, 마찰 0.45, 선반, 느린 이동 | 성공, 7.000초, 거리 6.573mm |
| [마지막 보존 실행](evidence/historical-runs/20260717_221155_arm_a1545c32/metrics.json) | contact-only 기본 상자 | 성공, 5.300초, 거리 0.906mm |

17개 중 16개가 success=true라는 단순 합계는 가능하지만, **실험 설계에 따른 성공률로 제시하지 않는다.** 보조 조건이 섞이고 반복 spec이 있으며, 실패를 포함한 전체 시도 집합의 완전성도 알 수 없기 때문이다.

현재 팔 성공 판정은 controller가 SUCCESS 상태이고, 목표까지 XY 거리가 반경 안이며, 물체가 충분히 높이 들렸고, 실행 중 물체 바닥이 테이블보다 4mm 이상 아래로 관통하지 않았는지를 검사한다. 최종 물체 속도, 목표에서 장시간 안정적으로 놓였는지, 충돌 힘의 상한은 성공 조건으로 명시되지 않는다. 과거 초반 metrics에는 현재의 높이 지표 자체가 없어 동일 성공 기준으로 소급 비교하지 않는다.

### 영상 증거와 수치 증거의 역할

사용자가 제공한 [수동 제어](media/README.md#robot-manual), [명령 제어](media/README.md#robot-command), [LLM 제어](media/README.md#robot-llm), [MuJoCo test1](media/README.md#mujoco-test1)은 이 저장소의 미디어 자료에서 다룬다. [오프라인 영상 갤러리](gallery.html)에서도 볼 수 있다. 영상 검토에서는 엔진 화면이 Unreal로 확인되었다. LLM 영상 초반에는 `llm_test.py`의 계획만 검증하는 구간과 API quota 오류, unknown 거부가 나오고, “오른쪽으로 조금 움직인 다음 집게를 닫아”를 `right, close`로 변환하는 장면이 관찰된다. 이 구간은 프로그램 스스로 로봇을 움직이지 않는 시험이라고 표시한다. 후반의 `panda_llm.py` 실제 제어 구간과 분리해 설명해야 한다.

영상은 사용 흐름과 동작 관찰의 근거다. 영상만으로 정확한 추종 오차, 비상 정지 지연, 모든 명령 성공률을 계산하지 않았다. 독립 MuJoCo의 metrics와 Unreal Panda 동영상을 동일 run의 데이터로 연결할 근거도 없다.

### LLM 검증에 남은 빈칸

푸셔 manifest의 `model_name`·`input_prompt`는 null이며, 팔 manifest에는 해당 필드가 없다. task_description에 자연어가 저장된 실행은 있지만, 현재 코드에 local-limited 경로도 있으므로 이것만으로 실제 API 생성 여부를 식별할 수 없다. 보존 artifact를 LLM 모델별 성능 비교에 사용할 수는 없다. LLM 연결 코드와 영상상 계획 변환의 존재, 정량 평가 완료는 서로 다른 주장이다.

## 8. 현재 코드 분석과 개선 방향

다음은 보존 코드에서 확인되는 한계와 그에 대한 **후속 제안**이며, 이미 구현한 기능으로 표시하지 않는다.

| 한계 | 구체적 영향 | 다음 개선 |
|---|---|---|
| 정지 입력이 입력 루프에 있음 | 블로킹 API 호출·순차 이동 중 같은 콘솔의 stop을 즉시 읽지 못함 | 별도 취소 신호, control loop 중단 검사, 비상 정지 지연 계측 |
| 계획 안 stop 뒤 `continue` | `[stop, right]`는 stop 후 right를 수행할 수 있음 | stop 의미를 전체 계획 종료 또는 취소로 명확히 정의 |
| current_pose가 목표값 중심 | 외력·통신 실패·추종 오차가 나도 다음 보간이 실제 자세와 다를 수 있음 | qpos 피드백, 도달 오차/timeout, 상태 동기화 |
| `validate_pose`에 유한성 검사 없음 | 일반화해 NaN을 넣으면 비교 검사를 통과할 수 있음 | `isfinite` 검사와 shape/type 검증. 현재 LLM은 숫자를 직접 만들지 않으므로 현 데모 입력면은 제한적 |
| home/종료 처리 정책 차이 | 수동·명령·LLM 버전의 gripper 유지와 귀환 행동이 다름 | 공통 RobotController와 명시적 종료 정책 |
| 시간 기반 IK 시퀀스 | 파지 실패·미끄러짐·장애물 접촉을 감지해 재시도하지 않음 | 접촉/물체 높이/오차 기반 상태 전이와 실패 진단 |
| 목표 위치 fallback | 도달하기 어려운 목표를 기본점 쪽으로 줄여 실행할 수 있음 | 원래 요청과 실제 채택 좌표를 함께 보여주고 변경 이유 기록 |
| 정적 소품 존재와 경로 계획 분리 | 소품을 장면에 넣어도 경유점이 충돌을 회피한다는 보장 없음 | collision 검사, 경로 계획, 도달성·간섭 검증 분리 |
| local-limited 의미 범위 | 임의 요청을 기본 pick_place로 변환해 의도를 놓칠 수 있음 | 지원 불가 요청 거부, 의미 테스트셋, 파싱 출처 및 fallback 기록 |
| 역사적 환경 기록 부족 | 같은 소스와 정확히 같은 환경을 다시 만들기 어려움 | Python·MuJoCo·SDK lock, 소스 commit/hash, OS/engine build를 manifest에 저장 |

다음 정량 실험은 명령별 정답 계획, unknown 거부율, 계획 생성 지연, 실제 관절 추종 오차, API 실패 후 상태, 중단 지연을 따로 측정하는 방식이 적절하다. contact-only 평가에는 질량·마찰·초기 위치·목표·형상을 정해 반복하고, 실패 run도 모두 저장해야 한다. 이는 제안이며 아직 수행한 실험이 아니다.

## 9. 재현 방법과 현재 검증 상태

### 9.1 독립 MuJoCo 실행 묶음

[보존 소스](evidence/text2mujoco)에는 전체 Python package, pyproject, 테스트 14개 파일의 `test_` 함수 48개, 설계문서와 실행 launcher가 포함되어 있다. 48은 정적 함수 개수이며, parametrization을 펼친 pytest 실행 개수나 통과 개수가 아니다. 새 환경에서 아래 순서로 복원한다.

```powershell
cd evidence/text2mujoco
# Python 3.12 이상인 인터프리터 사용
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m text2mujoco baseline --headless
python -m text2mujoco arm-baseline --headless
```

GUI 환경에서는 `python -m text2mujoco.arm_chat_app` 또는 보존된 launcher를 사용할 수 있다. 키를 설정하지 않으면 현재 world-scene 생성은 local-limited 경로를 사용한다. API를 사용할 때는 별도로 환경 변수 `OPENAI_API_KEY`, 필요하면 `OPENAI_MODEL`을 설정한다. 키를 소스나 결과 파일에 기록하지 않는다. 보조 파지를 요청하는 옛 실행 조건은 현재 공개 실행 함수가 거부하므로 과거 0.75초·3.3초 결과의 그대로 재실행을 보장하지 않는다.

아카이브 시점에는 원본 프로젝트를 수정하지 않고 복사본으로 검증했다. 원래 text2mujoco 가상환경은 Python 3.13.10이지만 MuJoCo·NumPy·pytest·ruff 등이 없어 실행하지 못했다. URLab 가상환경에는 MuJoCo 3.10.0, NumPy 2.4.6, Pydantic 2.13.4, OpenAI 2.46.0이 있었으나 Python **3.11.15**여서 이 프로젝트의 Python 3.12 `type Observation = ...` 문법에서 실패했다. 이것은 환경 불일치이며, 과거 성공 기록을 무효화하는 재실험 결과도 현재 실행 성공의 증거도 아니다. [첫 검증 로그](evidence/verification/verification-results.json), [다른 기존 환경 재확인](evidence/verification/recheck-results.json)

이후 이미 의존성이 설치된 기본 Python 3.13.10 환경을 찾아, 보존 소스의 `src`를 `PYTHONPATH`로 지정하고 별도 작업 폴더에서 `python -m text2mujoco arm-baseline --headless`를 실행했다. 2026-09-16 실행은 **success=true**, simulation time **5.30초**, **2,650 physics steps**, 최종 목표 거리 **0.9059mm**, `assisted_grasp=false`, `constraint_grasp=false`, `stability_status=stable`이었다. [실행 지표](evidence/verification/reverified-baseline-20260916/metrics.json), [입력 spec](evidence/verification/reverified-baseline-20260916/scene_spec.json), [환경과 실행 범위](evidence/verification/reverified-baseline-20260916/environment.json).

이 결과는 고정된 기본 팔 과제 1회의 물리 실행 재현이다. 과거 17회 집계와 별도로 보존했고, 자연어 API·Unreal Panda·전체 테스트·실물 로봇의 검증으로 확장하지 않는다. 의존성을 새로 설치하거나 GUI/Unreal/API를 실행하지 않았으며 원본 프로젝트도 수정하지 않았다.

### 9.2 Unreal Panda 실행 복원

보존된 [Unreal 스켈레톤](evidence/unreal-project-skeleton)은 프로젝트 정의·Source·Config를 보여주는 근거다. 완성된 맵, Blueprint와 import된 mesh 바이너리를 포함하는 배포 프로젝트가 아니다. 공개 묶음만으로 이 `.uproject`를 열어 같은 화면이 즉시 나온다고 주장하지 않는다.

1. UE 5.7 환경에 URLab 플러그인을 준비한다. 위에 기록한 로컬 revision은 당시 기반을 찾는 단서다.
2. MuJoCo Menagerie Panda와 필요한 mesh를 원 upstream에서 준비한다. 로컬 import 변경은 [속성 차이 기록](evidence/panda-import-delta.json)을 참고한다.
3. Panda articulation을 import하고 실험 맵에 AMjManager와 함께 배치한다. 보존 코드의 articulation 이름 `panda_C_1`, actuator 이름 8개가 실제 맵과 일치하는지 검사한다.
4. 서버와 클라이언트 MuJoCo 버전을 맞춘다. [보존된 bridge metadata](evidence/dependency-snapshots/urlab-bridge-pyproject.toml)는 로컬에서 3.10.0으로 변경된 상태이며 upstream 원래 핀과 다르다. 버전 검사를 끄는 것을 기본 해결책으로 삼지 않는다.
5. Unreal Play 상태에서 `inspect_panda.py → manual_panda.py → panda_commands.py → llm_test.py → panda_llm.py` 순서로 확인한다.

Panda 스크립트에는 `openai`, `pydantic`, `urlab_client`가 필요하다. `urlab_client`는 외부 bridge package에서 제공한다. 이름/포트/범위/버전이 맞는지 먼저 확인하고 이후 자연어 제어를 연결한다. 현재 아카이브에서는 서버와 재연결하거나 엔진 테스트를 수행하지 않았다.

## 10. 보존·제외·출처

- **보존:** 사용자 제어 스크립트 7개, 독립 MuJoCo 소스·설계·테스트·launcher, 과거 17회 실행의 spec/XML/metrics/manifest/log, 간단한 diffbot 모델, Unreal 프로젝트 텍스트 구성.
- **인벤토리만 보존:** Unreal Content 아래 93개 파일의 상대경로·크기·SHA-256. `PandaLLMMap.umap`, `RobotLabMap.umap`, Panda/diffbot Blueprint 및 import 자산의 존재를 확인한다.
- **복사하지 않음:** 외부 플러그인·bridge 라이브러리 전체, Menagerie 원본 모델/mesh, `.venv`, 빌드 결과, Saved/webcache, DerivedDataCache, `.vs`, 개인 인증 자료.
- **공개 복사본 변경:** UTF-8/LF 정규화, bridge 메타데이터의 외부 저자 이메일 삭제, Unreal 설정의 Android File Server `SecurityToken` 값 제거. [변경 내역](evidence/copy-transformations.json)에 기록했다. 모델·제어 알고리즘의 결함을 임의로 고치지 않았다.
- **로컬 추적용:** `evidence/source-map.json`은 원본 절대경로와 원본·복사본 SHA-256을 연결한다. 개인 경로가 있으므로 공개 저장소 대상에서 제외한다.

upstream의 저작권과 라이선스는 원 저장소를 따른다. 독립 text2mujoco의 pyproject에는 MIT가 선언되어 있으나 별도 원본 LICENSE 문서는 확인되지 않았다. 사용자 제어 스크립트 자체에도 별도의 라이선스 헤더는 없으므로 외부 프로젝트의 라이선스를 자동으로 덧씌우지 않는다.

이 아카이브가 입증하는 핵심은 **스키마를 통한 자연어 입력 제한, 규칙 기반 제어와 물리 시뮬레이션의 연결, 보조 조건을 줄여 가는 로봇팔 데모, Unreal Panda의 단계별 제어 실험**이다. 범용 로봇 지능이나 실물 작업 성공으로 확장하려면 위의 미확인 항목을 별도 실험으로 채워야 한다.
