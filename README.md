# MuJoCo Robot LLM

“오른쪽으로 움직인 다음 집게를 닫아”라는 문장은 실행할 동작의 순서를 담고 있지만, 로봇이 받아야 하는 관절 목표와 물리 계산 조건까지 정해 주지는 않는다. 이 연구는 **자연어 해석, 실행 가능한 계획, 제어기, 물리 결과 사이의 경계를 작게 나누어 연결하는 방법**을 탐색했다. 독립 MuJoCo에서는 장면을 구조화된 명세로 생성하고 사용자 정의 팔로 집기·놓기를 수행했다. Unreal Engine 5.7에서는 Panda를 수동 제어와 규칙 명령으로 먼저 움직인 뒤, 제한된 동작 계획을 생성하는 LLM을 연결했다.

[<img src="media/robot-llm-poster.jpg" width="820" alt="Unreal Panda와 Python 콘솔을 통해 자연어 계획 검사 및 제어 연결을 보여주는 장면">](media/previews/robot-llm.mp4)

*그림 1. [Panda의 언어 계획과 제어 연결](media/previews/robot-llm.mp4), 70.30초. 초반에는 로봇을 연결하지 않는 `llm_test.py`에서 문장을 `right, close`로 해석하는 계획 검사를 수행한다. 이 구간에 `429 insufficient_quota` 오류와 미지원 명령 거부도 남아 있다. 이후의 `panda_llm.py` 구간에서 실제 Unreal 로봇 제어가 이어진다. 같은 영상에 담겼더라도 계획 생성과 물리 실행은 서로 다른 검증 단계다. [원본 MP4](https://github.com/YuSihyeon/MuJoCoRobotLLM/releases/download/research-media-2026-09-16/robot-llm.mp4)는 2940 × 2090, 30 FPS다.*

두 계열에서 공통으로 확인되는 선택은 LLM이 매 순간 관절값이나 힘을 결정하도록 두지 않는 것이다. 언어 모델은 작은 장면 스키마 또는 미리 정한 동작 이름을 반환하고, 실제 수치와 실행 순서는 검증 코드와 규칙 기반 제어기가 처리한다. 2026-09-16에는 독립 MuJoCo의 **고정 contact-only 팔 과제 한 회가 5.30초, 2,650 physics steps, 최종 목표 XY 거리 0.9059mm로 재현**되었다. 이 수치는 API나 Unreal을 실행하지 않은 물리 baseline 결과이며, 자연어 요청 전반의 성공률과는 별개다.

## 언어 모델의 표현력을 제한한 설계 이유

[푸셔 설계문서](evidence/text2mujoco/docs/superpowers/specs/2026-07-16-text-to-mujoco-push-world-design.md)는 한국어·영어 설명을 받아 Pydantic `SceneSpec`으로 변환하고, 의미 및 물리 검증을 거쳐 결정론적으로 MJCF를 생성한다는 목표를 명시한다. [아키텍처 문서](evidence/text2mujoco/docs/ARCHITECTURE.md)는 LLM이 임의 Python이나 XML을 직접 만들 경우 실행 범위가 커지고 joint·actuator·inertia·collision 설정의 오류가 compile 실패나 불안정한 simulation으로 이어질 수 있다고 설명한다. 스키마를 선택한 이유는 당시 문서에 직접 남아 있다.

그래서 언어 해석이 담당하는 범위는 위치·색상·질량·마찰 등 제한된 필드다. Pydantic은 자료형, 수치 범위, 허용 필드 등을 검사하고, 별도 validation은 물체가 테이블에 들어오는지, 시작 위치와 목표의 관계가 실행 가능한지 확인한다. 실제 XML은 한 빌더에서 만든다. 같은 검증된 spec에서 같은 모델을 만들 수 있어야 언어 해석 오류, 장면 생성 오류, 제어 실패를 구분할 수 있기 때문이다. 코드·스키마·실행 산출물을 함께 남긴 구성은 이러한 원인 추적을 가능하게 한다.

이 선택에는 분명한 대가도 있다. 스키마 밖의 작업은 표현할 수 없고, 스키마를 통과한 장면이라도 요청의 뜻을 정확히 반영하지 않을 수 있다. “원래 자리에 내려놓기”가 잘못된 목표 좌표로 바뀌면 물리적으로 성공한 실행이 언어 과제에서는 실패가 된다. 따라서 이 연구에서 살펴야 할 질문은 단순히 로봇이 움직였는가보다 세분된다. 요청을 올바른 spec이나 계획으로 바꾸었는지, 그 입력이 실행 가능했는지, 물체의 이동이 실제 접촉을 통해 일어났는지를 각각 확인해야 한다. 설계문서와 결과를 함께 보면, 언어 해석과 물리 실행의 성공을 단계별로 나누어 확인하는 접근으로 해석할 수 있다.

Panda 구현은 같은 원리를 다른 형태로 적용했다. 장면을 생성하는 대신 `home/left/right/open/close/stop/unknown`이라는 동작 어휘 안에서 계획을 만든다. 관절각·그리퍼 값·보간 시간은 Python 코드가 결정한다. 두 계열을 하나의 시스템이 순서대로 완성된 것으로 볼 근거는 충분하지 않다. 독립 MuJoCo는 사용자 정의 팔과 장면 생성의 실행 구조를, Unreal Panda는 외부 엔진에 있는 로봇에 명령과 언어 해석을 연결하는 구조를 시험한 별도 경로다. 보존 폴더에 초기 분류명 `unity`가 남아 있지만, 실제 프로젝트와 영상에서 확인되는 엔진은 **Unreal + MuJoCo**이며 로봇팔의 Unity 연동 코드나 프로젝트는 조사 범위에서 확인되지 않았다.

## 푸셔의 실패에서 장면·제어·종료 조건을 구분하다

독립 MuJoCo의 첫 구현은 팔보다 단순한 2D 푸셔였다. X/Y slide joint와 position actuator로 움직이는 푸셔가 상자와 목표 사이의 방향을 구하고, 목표 반대편으로 접근해 정렬한 뒤 밀고 유지한다. [제어 구조](evidence/text2mujoco/docs/ARCHITECTURE.md)는 `INITIALIZE → APPROACH → ALIGN → PUSH → HOLD → SUCCESS/FAILED`로 나뉜다. 이 구성은 손가락 파지 없이 장면 명세, XML 생성, 제어, 물리 실행, 결과 저장을 끝까지 연결하는 최소 과제를 제공했다.

```text
SceneSpec → 형식·의미 검증 → 결정론적 MJCF 생성
          → MuJoCo compile와 이름 기반 body/joint/actuator 조회
          → 규칙 기반 제어와 물리 실행
          → scene_spec.json / scene.xml / metrics.json / manifest.json / run.log
```

body나 joint를 배열의 임의 번호로 고정하지 않고 이름과 `jnt_qposadr`, `jnt_dofadr`를 통해 찾는 것도 이 구조에 포함된다. 모델이 바뀌었을 때 다른 관절에 제어값을 쓰는 오류를 줄이고, 어떤 상태를 읽고 조작했는지 코드에서 확인하기 위한 선택이다. headless 실행은 렌더링 없이 물리 루프를 돌리므로 화면 표시 문제와 물리 결과를 나눌 수 있다. 이 경로는 강화학습 정책의 학습·평가가 아니라 규칙 기반 제어기의 실행이다.

첫 보존 실행은 0.112초에 `unstable_speed`로 종료되었다. 최대 속도 약 4.0616이 당시 종료 임계 4.0을 넘었다. 이후 spec에서는 최대 힘을 90에서 12로, `push_target_overshoot`를 0.24에서 0.07로 낮췄고, 속도 종료 임계는 4에서 8로 높였다. 수정 spec의 네 보존 실행은 모두 0.492초에 success를 기록했다. [spec 차이 기록](evidence/scene-spec-deltas.json)과 [첫 실패 metrics](evidence/historical-runs/20260716_015152_e8e8c4de/metrics.json), [수정 후 metrics](evidence/historical-runs/20260716_015349_456887a4/metrics.json)가 이 변화를 뒷받침한다.

여기서 “힘을 줄여 문제가 해결되었다”라고 한 변수의 효과로 결론내리면 부정확하다. 제어 강도와 목표 overshoot뿐 아니라 실패 판정 임계도 함께 바뀌었다. 확인 가능한 결론은 바뀐 조건 묶음에서 해당 spec의 실행이 성공으로 종료되었다는 것이다. 또 첫 run의 `stable` 표시는 유한한 상태가 유지되었다는 맥락에서 읽어야 하며, 목표 작업의 성공이나 속도 조건 통과와 같은 뜻이 아니다. 이 초기 사례는 성공 플래그만 보지 않고 제어 설정과 종료 이유를 함께 보존해야 하는 이유를 보여준다.

## 사용자 정의 팔과 접촉 파지: 움직이는 장면에서 힘으로 옮기는 과제로

### 4자유도 모델을 선택한 이유와 제어 방식

[팔 설계문서](evidence/text2mujoco/docs/superpowers/specs/2026-07-16-robot-arm-pick-place-design.md)는 관절이 보이면서 시험하고 조정할 수 있는 작은 데모를 목표로 삼았다. XYZ gantry보다 팔의 동작 구조를 드러내되, 완전한 산업용 6자유도 팔보다 초기 구현 범위를 작게 하기 위해 사용자 정의 4자유도 모델을 선택했다. 이 선택은 당시 문서에 명시되어 있으며 다른 로봇 모델과의 정량 성능 비교로 결정한 것은 아니다.

팔은 base yaw, shoulder pitch, elbow pitch, wrist pitch와 양쪽 손가락 slide joint로 구성한다. base yaw로 물체 또는 목표 방향을 향하고, 반경–높이 평면에서 두 링크 IK를 풀며, wrist에는 범위 제한을 적용한다. [제어기](evidence/text2mujoco/src/text2mujoco/arm_controller.py)는 경유점 사이를 `α²(3−2α)`로 보간하고 시간에 따라 상태를 전환한다. 관절 목표를 순간적으로 바꾸지 않고 접근, 닫기, 들어올리기, 운반, 놓기를 나누어 조정할 수 있는 구성이다.

```text
RESET → 물체 위 접근 → 내려가기 → 그리퍼 닫기 → 들어올리기
      → 목표 위 이동 → 놓을 높이로 이동 → 그리퍼 열기 → 후퇴 → SUCCESS
```

[<img src="media/mujoco-test1-poster.jpg" width="820" alt="사용자 정의 MuJoCo 로봇팔이 빨간 물체를 집어 목표 영역으로 운반하는 장면">](media/previews/mujoco-test1.mp4)

*그림 2. [사용자 정의 팔의 집기·놓기 동작](media/previews/mujoco-test1.mp4), 18.87초. 빨간 물체를 목표 영역으로 옮기는 전체 동작을 보여준다. 접근·파지·운반·해제의 시각적 연결을 확인할 자료이지만, 영상 자체로는 위치 또는 제약 보조의 사용 여부와 특정 run 폴더의 대응을 확정할 수 없다. 따라서 아래의 contact-only 수치는 영상이 아닌 해당 metrics와 spec을 근거로 해석한다. [원본 MP4](https://github.com/YuSihyeon/MuJoCoRobotLLM/releases/download/research-media-2026-09-16/mujoco-test1.mp4)는 2560 × 1480, 30 FPS다.*

이 상태기계는 LLM을 물리 루프 안에서 호출하지 않는다. 정해진 경유점과 시간으로 동작을 진행하므로 파지 실패나 미끄러짐을 인식하고 새로운 경로를 생성하는 폐루프 계획기는 아니다. 물체를 옮길 수 있는 작은 과제를 재현하고 파지 조건을 조정하는 데 목적이 있다. 정적 소품을 장면에 추가하는 기능 역시 경유점이 그 소품과의 충돌을 피한다는 보장과는 별개다.

### 위치 보조·제약 보조·접촉만 사용한 실행의 차이

초기 설계는 접촉 기반 파지를 우선 시도하되 불안정하면 명시적으로 기록한 weld-equality 보조를 선택적으로 허용했다. 실제 보존 run에는 직접 위치 보조, 제약 보조, 두 보조를 끈 실행이 모두 남아 있다. 이러한 구분은 단순한 구현 옵션이 아니다. 물체가 손가락 사이에 보이더라도 위치를 직접 덮어쓰거나 제약으로 붙이면 접촉 마찰과 손가락 힘만으로 운반된 결과라고 할 수 없기 때문이다.

| 보존된 팔 실행 조건 | run 수 | 시간과 최종 목표 거리 | 검증하는 범위 |
|---|---:|---|---|
| 직접 위치 보조 | 2 | 0.750초, 거리 0 | 보조를 사용한 전체 동작 연결 |
| 위치 보조 off, 제약 보조 on | 1 | 3.300초, 25.513mm | 제약으로 파지를 보조한 운반 |
| 위치·제약 보조 모두 off | 9 | 5.300 또는 7.000초, 0.715–6.573mm | 보존된 각 조건의 접촉 기반 물리 실행 |

contact-only로 전환한 spec에서는 그리퍼 닫기 시간이 0.35에서 0.7초로, 상태 유지 시간이 0.45에서 0.7초로, 놓기 안정 시간이 0.35에서 0.55초로 늘었고 팔의 최대 힘은 80에서 140으로 바뀌었다. [조건 변화](evidence/scene-spec-deltas.json)는 보조를 끄는 것과 동시에 접촉에 시간을 주고 actuator 조건을 바꾼 흐름을 보여준다. 다만 중간 실패와 모든 튜닝 시도가 보존되었다는 보장은 없고 여러 값도 함께 바뀌었으므로, 어느 변화가 성공에 얼마나 기여했는지 추정할 수는 없다.

현재 [팔 실행 함수](evidence/text2mujoco/src/text2mujoco/arm_simulation.py)는 위치 보조나 제약 보조를 켠 요청을 거부한다. 따라서 과거 0.75초·3.30초 결과와 현재의 보조 없는 baseline을 동일 실행 조건의 성능 개선으로 비교하지 않는다. 보조를 줄인 기록의 의미는 최종 거리 자체보다, 물체가 이동한 물리적 경로를 더 엄격하게 구분하게 되었다는 데 있다.

## 채팅으로 장면을 만들 때 드러난 의미와 물리 성공의 간격

팔에 자연어를 연결하는 [채팅 앱](evidence/text2mujoco/src/text2mujoco/arm_chat_app.py)은 `generate_world_scene → world_to_arm_scene → headless 실행 → viewer 실행` 순서로 동작한다. [WorldSceneSpec](evidence/text2mujoco/src/text2mujoco/world_scenes.py)은 테이블, 한 개의 조작 물체, 선택적인 정적 소품, `pick_place` 작업을 표현한다. 물체에는 box/sphere/cylinder, 색상·크기·질량이 있고, 장면에는 마찰·목표·속도 구분 등이 있다. “창고”나 “주방” 같은 이름을 붙일 수 있어도 생성 가능한 물리 작업의 범위는 이 테이블 과제 안에 있다.

[<img src="media/mujoco-test2-poster.jpg" width="820" alt="자연어 채팅 입력과 생성된 MuJoCo 테이블 장면의 실행을 함께 보여주는 장면">](media/previews/mujoco-test2.mp4)

*그림 3. [채팅 입력과 MuJoCo 실행의 연결](media/previews/mujoco-test2.mp4), 34.07초. 텍스트 입력 화면과 팔 동작을 함께 보여주는 보존 영상이다. 입력이 장면과 실행으로 이어지는 사용 흐름은 관찰할 수 있지만, 모든 요청의 의미 정확도나 API 사용 여부를 영상만으로 판정하지 않는다. 현재 코드에는 API 키가 없을 때의 `local-limited` 경로가 있으며 두 경로 모두 제한된 테이블 작업을 만든다. [원본 MP4](https://github.com/YuSihyeon/MuJoCoRobotLLM/releases/download/research-media-2026-09-16/mujoco-test2.mp4)는 2458 × 1746, 30 FPS다.*

OpenAI 경로는 `responses.parse(..., text_format=...)`로 구조화 출력을 받으며, API 키가 없으면 제한된 로컬 규칙으로 장면을 만든다. 출력 요약에는 생성 출처를 표시한다. 보존 코드의 기본 모델 설정은 text2mujoco의 `gpt-5.6`, Panda의 `gpt-5.4-mini`다. 이는 당시 설정명이며 모델 선발 실험이나 현재 권장 모델의 의미를 갖지 않는다. 푸셔 manifest의 `model_name`·`input_prompt`는 null이고 팔 manifest에는 해당 필드가 없어, 과거 모든 run을 어느 모델 또는 API 경로에 귀속시킬 수 없다.

구체적인 의미 불일치는 [마지막 보존 spec](evidence/historical-runs/20260717_221155_arm_a1545c32/scene_spec.json)에 드러난다. task_description은 “빨간 상자를 들어올렸다가 다시 그대로 내려놓아.”인데, 물체 XY는 `(0.18, −0.12)`, 목표 XY는 `(0.22, 0.18)`이다. 이 실행이 목표 반경 안에 물체를 놓았다고 해도 원래 자리로 되돌려 달라는 뜻을 수행한 것은 아니다. 제한된 pick-and-place 틀로 요청이 변환된 사례이며, 저장된 자연어 문장만으로 실제 LLM 생성 여부도 확정할 수 없다.

도달하기 어려운 목표를 기본점 쪽으로 줄이는 fallback에도 같은 문제가 있다. 실행 가능한 좌표를 만드는 것과 원래 의도를 유지하는 것은 서로 다른 요구다. 후속 구현에서는 미지원 요청을 거부하거나 원래 요청 좌표와 실제 채택 좌표, 변경 이유를 함께 기록해야 한다. 현재 자료가 알려주는 것은 구조화와 실행 가능성 검사가 유용하다는 점과 함께, 그 검사만으로 의미 정확성이 확보되지는 않는다는 점이다.

## Unreal Panda에서는 연결·명령·언어 해석을 나누어 시험했다

### 로봇 이름과 actuator부터 확인한 수동 제어

Panda 계열의 기반은 Unreal Engine 5.7, Unreal Robotics Lab, MuJoCo Menagerie의 Panda 자산, URLab Python bridge다. [.uproject](evidence/unreal-project-skeleton/RobotLLM.uproject)와 [에셋 인벤토리](evidence/unreal-assets-inventory.json)에 엔진 버전과 실험 맵·로봇 자산의 존재가 남아 있다. 독립 MuJoCo의 사용자 정의 팔을 Unreal에 그대로 옮긴 구조가 아니라, 기존 Panda articulation에 외부 Python 제어를 연결한 실험이다.

보존 스크립트에는 diffbot의 바퀴 속도와 문자열 명령을 다루는 [manual_diffbot.py](evidence/panda-control/manual_diffbot.py), [text_diffbot.py](evidence/panda-control/text_diffbot.py)도 있다. Panda에서는 [inspect_panda.py](evidence/panda-control/inspect_panda.py)가 manager·MuJoCo 버전·articulation·joint·actuator 이름과 범위를 조회하고, [manual_panda.py](evidence/panda-control/manual_panda.py)가 `panda_C_1`과 `actuator1`부터 `actuator8`까지를 명시적으로 찾는다. 이 단계에서 이름·개수·범위가 맞는지 확인해야 이후 언어 명령 실패를 연결 오류와 구분할 수 있다.

[<img src="media/robot-manual-poster.jpg" width="820" alt="Unreal Panda 수동 제어와 Python 관절 상태 콘솔 장면">](media/previews/robot-manual.mp4)

*그림 4. [Panda 수동 제어](media/previews/robot-manual.mp4), 13.93초. Unreal RobotLLM 화면과 Python 콘솔을 통해 관절·그리퍼 조작을 확인하는 기록이다. 수동 스크립트는 첫 관절을 0.25rad로 움직인 뒤 home으로 돌아가며, 미리 정한 목표를 보간해 보낸다. 영상은 연결과 동작 관찰의 근거이고, 정밀 관절 추종 오차나 실물 Franka 성능을 측정한 자료는 아니다. [원본 MP4](https://github.com/YuSihyeon/MuJoCoRobotLLM/releases/download/research-media-2026-09-16/robot-manual.mp4)는 2552 × 2088, 30 FPS다.*

home 제어값은 `[0, 0, 0, −1.57079, 0, 1.57079, −0.7853, 255]`다. 앞의 일곱 값은 팔, 마지막은 gripper 제어값이다. 수동 시험은 2초 이동과 1초 관찰 유지, 약 30Hz 전송으로 구성된다. 이는 Cartesian 목표점으로 팔 끝을 보내는 IK 정확도 실험이 아니라, 알려진 관절 목표를 엔진 안의 로봇에 전달할 수 있는지 확인하는 단계다.

### 규칙 명령은 언어 계획의 실행 단위를 먼저 정한다

[panda_commands.py](evidence/panda-control/panda_commands.py)는 한국어 별칭을 `home`, `left`, `right`, `open`, `close`로 매핑한다. left/right는 첫 관절 목표 −0.35/+0.35rad인 고정 자세이고, 그리퍼는 0/255로 닫고 연다. “왼쪽”이라는 이름이 세계 좌표에서 일정 거리 이동한다는 뜻은 아니다. LLM이 등장하기 전에 각 동작 이름이 어떤 실제 제어를 뜻하는지 정한 단계로 이해할 수 있다.

[<img src="media/robot-command-poster.jpg" width="820" alt="규칙 명령을 입력하여 Unreal Panda의 자세와 그리퍼를 바꾸는 장면">](media/previews/robot-command.mp4)

*그림 5. [Panda 규칙 명령 제어](media/previews/robot-command.mp4), 37.30초. 정해진 문자열 명령에 대응해 자세와 그리퍼를 바꾸는 실행이다. 이 기록은 동작 이름과 제어 목표의 연결을 보여주며, 자유로운 자연어 해석 성능의 결과로 계산하지 않는다. 규칙 버전의 좌우 이동은 그리퍼 상태를 유지하지만 home은 기본 HOME 값을 적용해 그리퍼도 연다. 이러한 동작 의미는 뒤의 LLM 버전과 완전히 같지 않다. [원본 MP4](https://github.com/YuSihyeon/MuJoCoRobotLLM/releases/download/research-media-2026-09-16/robot-command.mp4)는 2548 × 2088, 30 FPS다.*

### 계획만 확인하는 코드와 로봇을 구동하는 코드는 다르다

[llm_test.py](evidence/panda-control/llm_test.py)는 구조화 계획을 생성하고 검사하지만 로봇에는 연결하지 않는다. 그림 1 초반에서 “오른쪽으로 조금 움직인 다음 집게를 닫아”가 `right, close`가 되는 장면은 이 경로의 증거다. “조금”이라는 표현이 임의 이동량을 계산했다는 의미는 아니다. right는 앞서 정의한 고정 관절 자세이고 LLM은 그 이름을 선택한다.

[panda_llm.py](evidence/panda-control/panda_llm.py)는 이 계획을 실제 제어에 연결한다. `RobotAction.name`의 일곱 가지 Literal, 비어 있지 않은 계획, 최대 다섯 동작, `unknown` 부재를 검사하고, 자세 길이와 actuator별 범위를 확인한다. 계획을 표시한 후 사용자 확인을 받아 실행한다. 이 실행 확인은 보존 프로그램의 동작 방식이다. 시스템 프롬프트에는 관절값·힘·속도 직접 지정이나 던지기·충돌 요청을 `unknown`으로 보내라는 규칙도 있지만, 모든 자연어 규칙이 독립된 코드 검사로 구현된 것은 아니다. 코드가 확인하는 범위와 언어 모델에게 요구한 분류 규칙을 같은 보장으로 볼 수 없다.

LLM 버전의 home/left/right는 현재 gripper 제어값을 유지한다. open/close는 1초, 팔 자세 이동은 2초로 보간하고 동작 후 0.3초 유지한다. `current_pose`는 주로 마지막 목표값을 기억한다. 목표가 전송되었다는 사실과 실제 관절이 허용 오차 안에 도달했다는 사실을 분리해 판단하는 피드백 완료 조건은 구현되어 있지 않다. 이는 동작 이름을 제한했더라도 실행 상태의 확인이 별도 문제로 남는다는 뜻이다.

### live 통신에서는 Python 호출과 물리 적분 시간이 다르다

```text
자연어 → RobotPlan → 계획 검사와 실행 확인
       → 고정 자세 / 그리퍼 목표 → 약 30Hz 보간
       → actuator.set_ctrl() / URLabClient.step()
       → TCP 5559 · MessagePack RPC
       → Unreal URLab 서버 / MuJoCo 상태와 화면
```

실제 설정은 `tcp://127.0.0.1`, `step_port=5559`, `step_mode="live"`, `mujoco_version_check=True`다. live 모드에서는 Unreal이 물리를 진행하고 Python 요청이 제어값을 적용하며 상태를 읽는다. 따라서 `step(n_steps=1)` 호출 한 번을 물리 적분 한 번으로, Python의 약 30Hz를 MuJoCo 적분 주파수로 해석하지 않는다. 버전 검사는 서버·클라이언트가 서로 다른 MuJoCo를 사용하는 상황을 식별하는 조건이며, 현재 복원에서 이를 끄는 것을 기본 해결법으로 삼을 이유는 없다.

여기서 LLM은 카메라나 로봇의 물리 상태를 다시 읽어 계획을 고치지 않는다. 계획 생성 뒤 동작을 순차 실행하는 구조다. 화면에서 상태가 계속 갱신된다는 사실은 물리 시뮬레이션과 통신이 이어진다는 뜻이며, LLM이 폐루프로 로봇을 제어하고 있다는 증거는 아니다.

## 보존 run과 현재 재현으로 판단할 수 있는 결과

### 과거 17개 실행은 조건 변화의 기록이다

[전체 실행 인덱스](evidence/historical-run-index.json)는 푸셔 5회와 팔 12회의 metrics·spec·XML·manifest·log를 연결한다. 이 17개 폴더는 선별 삭제 없이 보존했지만 모든 과거 시도를 포함한다는 보장은 없다. 아래 값은 서로 다른 보조 조건과 과제를 포함하므로 하나의 성능 순위로 비교하지 않는다.

| 보존 run | 실행 조건 | 기록된 결과 |
|---|---|---|
| [015152](evidence/historical-runs/20260716_015152_e8e8c4de/metrics.json) | 초기 푸셔 | 실패, `unstable_speed`, 0.112초 |
| [015349](evidence/historical-runs/20260716_015349_456887a4/metrics.json) | 힘·overshoot·속도 임계 변경 푸셔 | 성공, 0.492초, 67.525mm |
| [023036](evidence/historical-runs/20260716_023036_arm_d49f06e0/metrics.json) | 위치 보조 팔 | 성공, 0.750초, 거리 0 |
| [024938](evidence/historical-runs/20260716_024938_arm_c8964d4a/metrics.json) | 제약 보조 팔 | 성공, 3.300초, 25.513mm |
| [043519](evidence/historical-runs/20260716_043519_arm_18e9bcf8/metrics.json) | contact-only 팔 | 성공, 5.300초, 0.715mm |
| [054235](evidence/historical-runs/20260716_054235_arm_108be4f5/metrics.json) | contact-only, 파란 원통·마찰 0.45·선반·느린 이동 | 성공, 7.000초, 6.573mm |
| [마지막 보존 실행](evidence/historical-runs/20260717_221155_arm_a1545c32/metrics.json) | contact-only 기본 상자 | 성공, 5.300초, 약 0.906mm |

17개 중 16개는 `success=true`지만, 이를 벤치마크 성공률로 제시할 수는 없다. 직접 위치 보조의 거리 0과 접촉 기반의 작은 오차는 서로 다른 기전에서 나온 값이다. 같은 spec 반복도 포함되어 있고 모집단인 전체 시도 집합을 알 수 없다. 파란 원통과 마찰·소품·속도 변경 실행은 조건 확장의 사례지만, 각각의 영향을 독립적으로 평가한 실험 설계가 아니다.

### 2026-09-16의 고정 contact-only baseline 한 회

환경을 대조한 뒤 실행한 현재 baseline은 Python 3.13.10 / MuJoCo 3.10.0, NumPy 2.4.2, Pydantic 2.13.4, OpenAI 2.45.0 환경을 사용했다. OpenAI 패키지가 설치되어 있다는 사실과 API를 호출했다는 사실은 다르다. 이 실행에서는 API·GUI·Unreal을 구동하지 않았고, 고정 spec의 팔 물리 경로만 headless로 실행했다.

| 입력·측정 항목 | 값 |
|---|---|
| seed / 물체 / 질량 / 마찰 | 11 / 7cm box / 0.12kg / 0.8 |
| spec의 물체 위치와 목표 | `(0.18, −0.12, 0.13)m` → `(0.22, 0.18, 0.08)m` |
| 테이블 높이 / 목표 XY 반경 / 정적 소품 | 0.08m / 0.08m / 없음 |
| timestep / 최대 실행 시간 | 0.002초 / 8.0초 |
| 종료 | `success=true`, controller `SUCCESS`, 5.30초, 2,650 steps |
| 최종 목표 XY 거리 | 0.9059mm |
| 최대 물체 중심 높이 / 최소 물체 바닥 높이 | 약 0.321835m / 0.079626m |
| 보조·상태 기록 | `assisted_grasp=false`, `constraint_grasp=false`, `stable` |

[입력 spec](evidence/verification/reverified-baseline-20260916/scene_spec.json), [metrics](evidence/verification/reverified-baseline-20260916/metrics.json), [환경·실행 범위](evidence/verification/reverified-baseline-20260916/environment.json)가 한 실행의 근거다. spec에는 물체 z가 0.13m로 저장되어 있지만 [초기화 코드](evidence/text2mujoco/src/text2mujoco/arm_simulation.py)는 물체 중심을 `table_height + object_size.z / 2`에 놓는다. 이 입력에서는 0.115m다. 따라서 spec에 적힌 높이와 실제 reset 후 초기 중심 높이를 구분해야 한다.

현재 성공 판정은 controller `SUCCESS`, 목표 XY 반경 이내, 충분한 들어올림, 실행 중 물체 바닥이 테이블보다 4mm 이상 아래로 내려가지 않았는지를 함께 검사한다. 이 상자 조건에서 들어올림 기준은 `0.08 + 0.07 + 0.08 = 0.23m`의 중심 높이다. 최대 높이 약 0.321835m는 그 기준을 넘었으며 최소 바닥 높이는 0.08m 테이블보다 약 0.374mm 낮아 4mm 허용치 안에 있다. 이 두 값은 단순히 목표 가까이에 도착했다는 설명보다 파지·운반의 물리 조건을 더 구체적으로 뒷받침한다.

그렇더라도 최종 속도, 목표에서의 장시간 정착, 접촉 힘 상한은 현재 성공 기준에 들어 있지 않다. 초반의 과거 metrics에는 높이 지표 자체가 없으므로 이 판정을 소급 적용할 수 없다. 0.9059mm는 이 입력의 최종 XY 거리이며 3차원 자세 정확도, 임의 물체 일반화, LLM 계획 정확도 또는 Panda의 추종 오차가 아니다. 독립 MuJoCo metrics와 Unreal Panda 영상이 동일 run이라는 근거도 없다.

## 실행 경계가 드러낸 한계와 다음 실험

### 정지와 완료는 동작 이름만으로 보장되지 않는다

`panda_llm.py`는 입력 대기 상태에서 정지 문자열을 LLM 호출 없이 처리한다. 그러나 블로킹 API 호출이나 순차 이동 중에는 같은 입력 루프가 새로운 stop을 읽지 못한다. 계획 안의 `stop`도 현재 목표를 유지한 뒤 `continue`하므로 `[stop, right]`에서는 뒤의 right가 실행될 수 있다. 이는 제한된 동작 어휘와 별개로 취소 신호의 전달과 계획 종료 의미를 설계해야 한다는 문제다. 후속 작업에서는 별도 취소 신호와 제어 루프 중단 검사를 두고, API 대기 및 각 이동 중 중단 지연과 마지막 제어 상태를 측정해야 한다.

`current_pose`가 마지막 목표 중심이라는 점도 다음 동작의 시작 상태를 불확실하게 만든다. 실제 관절이 목표를 따라가지 못했거나 통신이 끊긴 경우에는 목표값으로 이어지는 보간과 실제 로봇 자세가 다를 수 있다. qpos 피드백, 도달 오차와 timeout, 재연결 후 상태 동기화가 필요한 이유다. 자세 검사에는 명시적인 유한성 검사도 없어 일반화된 입력에서 NaN이 비교 검사를 통과할 수 있다. 현재 LLM이 숫자를 직접 만들지는 않지만, 제어기를 확장한다면 shape·type·`isfinite`를 포함한 수치 입력 검증을 해야 한다.

### 물리 실패와 의미 실패에 서로 다른 평가가 필요하다

contact-only 결과를 확장하려면 형상·질량·마찰·시작 위치·목표를 정해 반복하고 모든 실패를 저장해야 한다. 시간 기반 상태 전이가 파지 실패와 미끄러짐을 검출하도록 접촉·높이·목표 오차를 활용하고, 실패 원인을 분리할 필요도 있다. 물체를 움직인 경로의 물리 타당성과 정착 상태가 그 평가의 대상이다.

언어 경로에는 다른 기준이 필요하다. 명령별 정답 계획, 미지원 요청의 거부율, 의미 불일치 유형, API/fallback 출처, 계획 생성 지연을 기록해야 한다. “같은 자리에 내려놓기”가 다른 목표로 변환된 사례처럼, 물리 성공이 의미 실패를 가리지 않도록 원문·채택 spec·실행 결과를 연결해야 한다. 기존 푸셔·팔 manifest의 생성 출처 부족은 이 평가를 과거 자료만으로 완성할 수 없게 하는 제한이다. 이 평가와 취소·피드백 개선은 제안이며 이미 완료한 기능으로 제시하지 않는다.

### 엔진·자산 변경의 존재와 호환성 검증은 다르다

보존된 Panda import에는 원본 대비 56개 요소 속성 차이가 있다. mesh 이름 추가와 파일명 조정 등의 [차이 기록](evidence/panda-import-delta.json)은 남아 있지만 변경별 실제 오류 로그는 충분하지 않다. bridge의 MuJoCo 핀은 upstream 3.8.1에서 3.10.0으로 바뀌고 OpenAI>=2.46.0이 추가된 상태다. 로컬 Unreal 플러그인의 두 C++ 테스트는 `.disabled`였지만 그 이유나 전체 엔진 테스트 통과는 확인되지 않았다. 변경이 있다는 사실을 완전한 호환성 해결로 설명할 수 없다.

외부 기반은 [URLab bridge](https://github.com/URLab-Sim/urlab_bridge), [Unreal Robotics Lab](https://github.com/URLab-Sim/UnrealRoboticsLab), [MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie)이며 보존 당시 확인된 로컬 HEAD는 각각 `c1fb34e`, `567cbd9`, `71f066a`다. 이 연구의 직접 구현 범위는 [Text2MuJoCo의 스키마·빌더·검증·제어·결과 저장](evidence/text2mujoco)과 [사용자 Panda/diffbot 제어 스크립트 7개](evidence/panda-control), 엔진·자산 연결의 구성과 실험이다. 해당 7개 스크립트는 당시 bridge에서 untracked였고 RobotLLM 본체와 text2mujoco에는 Git 저장소가 확인되지 않았다. 수정 시각만으로 빠짐없는 개발 순서를 복원하거나 외부 프로젝트 전체를 독자 개발 성과로 귀속할 수 없다.

## 이 연구가 확인한 연결과 아직 확인하지 못한 일반화

독립 MuJoCo 경로는 제한된 spec에서 물리 장면을 만들고, 보조 조건을 명시하면서 팔의 집기·놓기를 수행할 수 있음을 보여준다. 현재 고정 baseline의 재현은 보조 없는 실행 한 회의 근거를 추가했다. Unreal Panda 경로는 알려진 관절 목표와 규칙 동작을 먼저 정한 뒤, 언어 모델이 그 동작의 순서를 반환하도록 연결할 수 있음을 보여준다. 계획 전용 코드와 실제 제어 코드, API 오류와 미지원 명령 거부까지 남아 있어 각 연결 단계의 역할을 구분할 수 있다.

동시에 보존 자료는 ‘동작함’이 여러 종류의 성공을 포함한다는 사실을 드러낸다. 구조화된 출력의 성공, 요청 의미의 보존, 제어 목표의 전달, 접촉 기반 운반, 장시간 안정적인 놓기는 서로 다른 평가다. 본 연구는 그 경계를 드러내고 작은 구현으로 연결한 단계에 있다. 실물 로봇 작업, 범용 계획, 장애물 회피, LLM의 폐루프 제어 성능은 이 결과에서 확인되지 않았다. 다음 연구의 핵심은 연결 범위를 넓히는 일과 함께, 각 단계의 성공·실패를 같은 실행 기록에서 분리해 측정하는 데 있다.

## 독립 MuJoCo와 Unreal Panda의 재현 경로

### 독립 MuJoCo 실행

Python **3.12 이상**이 필요하다. 보존본을 별도 작업 위치로 복사한 뒤 해당 저장소 루트에서 시작한다.

```powershell
Set-Location .\evidence\text2mujoco
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

GUI는 `python -m text2mujoco.arm_chat_app` 또는 [보존 launcher](evidence/text2mujoco/open_robot_arm_chat.ps1)를 사용한다.
키가 없으면 world-scene 생성은 local-limited다. API 사용 시 `OPENAI_API_KEY`와 필요하면 `OPENAI_MODEL`을 로컬 환경에 설정한다.
원래 가상환경은 의존성 누락, URLab의 Python 3.11.15는 Python 3.12 문법 불일치로 실패했다. 이후 설치된 기본 Python 3.13 환경에서 위 baseline만 재현했다.
[첫 점검](evidence/verification/verification-results.json) · [환경 재확인](evidence/verification/recheck-results.json). Python 파일 43개의 구문 분석과 테스트 함수 48개 정적 집계는 전체 테스트 통과를 뜻하지 않는다.

### Unreal Panda 복원

1. 전체 원본의 UE 5.7 맵·Content·URLab 플러그인과 Panda 자산을 작업 복사본으로 준비한다. 공개 스켈레톤은 완성 배포 프로젝트가 아니다.
2. [bridge 의존성](evidence/dependency-snapshots/urlab-bridge-pyproject.toml)을 확인하고 Python 3.11 계열 환경과 서버 MuJoCo 버전을 맞춘다. 버전 검사를 끄는 것을 기본 복원법으로 삼지 않는다.
3. Play 상태에서 `panda_C_1`, actuator 8개, RPC 5559를 확인한다. `inspect_panda.py → manual_panda.py → panda_commands.py` 순서로 실행한다.
4. `llm_test.py`에서 계획만 검사한 후 `panda_llm.py` 실제 제어를 별도로 확인한다. 현재 보존 점검에서는 이 엔진/API 경로를 재실행하지 않았다.

### 공개 근거와 전체 원본의 위치

| 자료 | 공개 검토 경로 | 프로젝트 보존 폴더의 원본 위치 |
|---|---|---|
| 독립 MuJoCo 소스·과거 17개 run | [소스](evidence/text2mujoco), [과거 실행](evidence/historical-runs) | `originals/text2mujoco_session/` |
| 사용자 스크립트·bridge 환경 | [Panda 제어](evidence/panda-control), dependency snapshots | `originals/urlab_bridge/` |
| Unreal 전체 맵·Content·플러그인 | [프로젝트 구성](evidence/unreal-project-skeleton), [93개 Content 인벤토리](evidence/unreal-assets-inventory.json) | `originals/robot_unreal/` |
| Panda·diffbot 모델 | [Panda 차이](evidence/panda-import-delta.json), [diffbot XML](evidence/diffbot-models) | `originals/mujoco_menagerie/`, `originals/robot_assets/` |
| 영상 5개 | 본문 그림 1–5의 MP4·원본 링크와 [미디어 기록](media/README.md) | `originals/original-videos/` |
| 환경·복사 검증 | [전체 복원 안내](DATA_AND_RESTORE.md) | 컬렉션 `_shared/`, `_control/manifests/`, 프로젝트 `RESTORE.md` |

전체 위치는 `ResearchCollection/03-MuJoCoRobotLLM/`다. Menagerie 보존은 현재 Panda checkout 범위이며 전체 로봇 카탈로그·모든 Git blob의 보존은 아니다.
공개 근거에는 인증값 제거·이메일 삭제·줄바꿈 정규화가 적용된 사본이 있다. [변환 기록](evidence/copy-transformations.json)과 [출처·라이선스](ATTRIBUTION.md)를 따른다.
원래 README는 루트의 [RESEARCH_REPORT.md](RESEARCH_REPORT.md)에 바이트 그대로 보존했다. Git clone만으로 원본 에셋과 실행 환경이 복원되지는 않는다.
현재 C: 로컬 보존·내용 검증과 USB 외부 사본·초기화 후 전체 실행은 별도 상태이며, USB 전송과 초기화 후 복원 실행은 아직 수행하지 않았다.
