# 전체 데이터와 복원 범위

**2026-09-16 최종 보존 상태:** 조사한 Windows 연구 원본과 WSL 전체 export, 연구별 직접 추출본, conda·Unity·Unreal 환경 archive의 로컬 내용 검증을 마쳤다. USB 전송·외부 사본 검증과 초기화 후 전체 실행은 아직 수행하지 않았다. 실제 복사 목록·해시·확인하지 못한 자료는 개인 보존 묶음의 `PRESERVATION_STATUS.md`와 `_control/manifests/`를 기준으로 확인한다.

이 저장소는 MuJoCo 로봇 조작과 **Unreal Engine 5.7 + Panda + LLM** 연구의 공개 기록이다. 공개 `evidence/`는 검토를 위한 선별 자료다. PC 초기화에 대비한 별도 비공개 `ResearchCollection/03-MuJoCoRobotLLM/` 묶음은 전체 원 프로젝트, Git 변경, 에셋, 환경, 원본 영상을 보존했다. Unity 연동이나 실물 로봇 제어를 복원하는 패키지는 아니다.

최종 복사·검증 범위와 아직 남은 외부 보관·실행 검증은 아래 최종 상태와 개인 보존 묶음의 관리 기록을 확인한다.

## 원본 묶음의 구성

| 프로젝트 폴더 기준 위치 | 원본에서 확인한 내용 | 원본 파일 수 / 논리 크기 |
|---|---|---:|
| `originals/robot_unreal/` | RobotLLM `.uproject`, Source, Config, 전체 Content, UnrealRoboticsLab 플러그인과 nested Git/submodules, Binaries/Intermediate/Saved/캐시 | 71,258 / 8,998,929,427 bytes |
| `originals/robot_assets/` | 사용자 정의 `diffbot.xml`, `diffbot_ue.xml` | 2 / 5,133 bytes |
| `originals/urlab_bridge/` | bridge 전체 코드·Git·RoboJuDo submodules, 수정된 의존성 선언, 사용자 제어 스크립트, `.venv` | 9,281 / 787,082,892 bytes |
| `originals/mujoco_menagerie/` | 현재 로컬 Panda 모델, mesh 원본, 수정 XML, OBJ/GLB 변환, Git | 205 / 55,015,253 bytes |
| `originals/text2mujoco_session/` | `text2mujoco/` 전체 소스·테스트·문서·17개 과거 run을 포함한 산출물과 환경 흔적, 세션의 `outputs/`, `work/` 구조 | 667 / 7,037,126 bytes |
| `originals/original-videos/` | 아래 다섯 원본 MP4 | 5 / 138,230,694 bytes |

파일 수와 크기는 원본 조사 시점 기준이다. 압축 후 크기나 목적지 검증값이 아니며, 의존성·빌드 캐시도 포함한다. 세션 루트의 `outputs/`와 `work/`는 조사 시점에 비어 있었고 실제 파일은 `text2mujoco/` 아래에 있었다.

원본 영상은 `MuJoCo_test1.mp4`, `MuJoCo_test2.mp4`, `로봇팔Mujoco_수동제어.mp4`, `로봇팔Mujoco_명령제어.mp4`, `로봇팔Mujoco_llm.mp4`다. 공개 영상 목록의 미리보기·프레임 추출물과 구분해 원래 이름과 바이트를 유지한다. LLM 영상 초반의 계획 검증 모드는 로봇을 움직이지 않으며, 후반의 실제 Panda 제어와 구분한다.

## 소스 외에 필요한 에셋과 상태

Unreal 프로젝트에는 `Content/Maps/PandaLLMMap.umap`, `RobotLabMap.umap`, `MuJoCoImports`, `RobotArms`, `Robots` 등이 있다. Content 전체는 93개 파일, 8,074,523 bytes다. `.uproject`와 Python 파일만으로 맵·Blueprint·imported mesh를 복원할 수 없다. `Plugins/UnrealRoboticsLab`의 소스, native 라이브러리, MuJoCo·CoACD·libzmq 등의 submodule을 함께 유지한다.

Panda의 `panda.xml`과 `panda_ue.xml`은 각각 67개 mesh 참조가 조사 시점에 모두 존재했다. Menagerie는 sparse/partial clone이므로 현재 Panda checkout을 보존하는 범위이며, upstream의 전체 로봇 카탈로그와 모든 과거 Git blob을 확보했다는 의미는 아니다. 로컬 변환물 70개가 미추적 상태여서 upstream 재clone만으로 복구되지 않는다.

Git 바깥의 변경도 원본의 일부다. bridge에는 `pyproject.toml` 수정과 `inspect_panda.py`, `manual_panda.py`, `panda_commands.py`, `llm_test.py`, `panda_llm.py`, `manual_diffbot.py`, `text_diffbot.py`가 있다. 플러그인에는 두 테스트의 삭제 상태와 대응 `.disabled` 파일이 남아 있다. 이 상태를 임의로 clean/reset하거나 최신 upstream으로 덮어쓰지 않는다. RobotLLM 본체와 text2mujoco는 조사 시 Git 저장소가 아니었다.

별도의 학습 모델 가중치는 이 로봇 데모의 필수 입력으로 확인되지 않았다. text2mujoco의 MJCF·scene spec·metrics·manifest와 Panda 관절 상수가 실행 정의를 이룬다. LLM은 외부 API이며 모델 자체의 가중치는 로컬 백업에 없다. bridge의 선택적 policy 관련 의존성이 존재한다는 이유로 강화학습 정책 학습·실행 완료를 주장하지 않는다.

## 실행 환경

| 실행 경로 | 조사 시점 환경 | 복원 시 확인할 것 |
|---|---|---|
| 독립 text2mujoco | Python 3.13.10, MuJoCo 3.10.0, NumPy 2.4.2, Pydantic 2.13.4, OpenAI 2.45.0 | 프로젝트 요구 Python >=3.12. 과거 `.venv`가 새 경로에서 동작한다고 가정하지 않음 |
| URLab Python bridge | Python 3.11.15, MuJoCo 3.10.0, NumPy 2.4.6, Pydantic 2.13.4, OpenAI 2.46.0 | 프로젝트 요구 Python >=3.11,<3.13. 독립 baseline의 Python 3.13 환경과 별도 |
| Unreal | EngineAssociation 5.7, UnrealRoboticsLab native plugin | UE 5.7, Visual Studio 2022 C++/MSVC, Windows SDK, 플러그인 빌드와 서버 MuJoCo 버전 |
| LLM | 코드 설정 `gpt-5.4-mini` 및 text2mujoco 기본 `gpt-5.6` | 당시 설정명. 현재 API 제공 여부·할당량·출력 호환성은 별도 확인 |

컬렉션 공용 `_shared/originals/python313/`는 글로벌 Python 설치본의 보존 대상이다. 공유 `_shared/environments/snapshots/UE_5.7-full.tar.zst`는 원 프로젝트 밖의 Unreal 엔진 보존 경로이며, `_shared/environments/snapshots/miniconda3-full.tar.zst`는 다른 연구와 공유하는 Miniconda 설치본이다. 실제 archive 완성·검증 여부는 컬렉션 manifest를 따른다. 이 로봇 경로의 핵심 환경은 bridge `.venv`와 독립 Python이며, Miniconda 보관 자체가 Unreal/bridge 실행을 대신하지 않는다.

환경 디렉터리 복사는 Windows 등록, compiler, 드라이버, 절대 경로, DLL 탐색 설정까지 자동 복원하지 않는다. 환경 목록과 버전 기록을 보존하고 새 작업 복사본에서 재구성한다. 공개 버전에는 개인 설정·인증값을 포함하지 않는다.

## 복원과 점검 순서

1. 비공개 컬렉션의 복사 manifest와 검증 기록을 확인하고, `originals/`를 별도 작업 위치에 복사한다. 재실행 출력은 새 폴더에 둔다.
2. 독립 text2mujoco부터 해당 `pyproject.toml`과 버전에 맞춰 환경을 구성한다. 작업 복사본에서 `python -m pip install -e ".[dev]"`, `python -m pytest`를 수행하고 `python -m text2mujoco arm-baseline --headless`의 새 metrics를 확인한다. 이 문서는 해당 명령들의 복원 후 성공을 보장하지 않는다.
3. Unreal 원본 맵·에셋과 URLab 플러그인을 복원한다. 기존 build cache는 보존하되 새 환경에서 재빌드가 필요할 수 있다. `panda_ue.xml`의 상대 mesh 경로와 import 자산을 확인한다.
4. Python 3.11 계열의 bridge 환경을 별도로 구성한다. live server의 articulation 이름 `panda_C_1`, 액추에이터 8개, RPC port 5559, MuJoCo version handshake를 확인한 뒤 `inspect_panda.py` → 수동 제어 → 명령 제어 순으로 시험한다. 버전 mismatch를 임의로 무시하지 않는다.
5. 마지막으로 API 설정을 새 환경에 제공하고 `llm_test.py`에서 계획 검증만 수행한 뒤 `panda_llm.py` 실행을 별도로 확인한다. 키는 로컬 환경에서 관리하고 공개 Git에 넣지 않는다.

2026-09-16 공개 아카이브 점검에서는 설치된 Python 3.13 환경으로 contact-only 팔 baseline이 성공했다. 이는 초기화 후 전체 복원, Unreal 실행, LLM API, 전체 테스트 통과를 의미하지 않는다. 검증 결과는 [baseline metrics](evidence/verification/reverified-baseline-20260916/metrics.json)와 [연구 기록](README.md)에 있다.

비공개 원본의 환경설정·캐시에는 인증 또는 개인 정보가 남을 수 있다. 전체 원본 보존본을 공개 저장소에 일괄 추가하지 않는다. 공개 자료의 선별과 라이선스 출처는 [ATTRIBUTION.md](ATTRIBUTION.md)를 따른다.
