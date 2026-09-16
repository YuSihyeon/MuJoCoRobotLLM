# Text-to-MuJoCo Push World

한국어 또는 영어 자연어 요청을 안전한 `SceneSpec`으로 바꾸고, 검증된 값만 사용해 MuJoCo push-world를 실행하는 소규모 Python 프로젝트입니다.

LLM은 Python 코드나 MJCF XML을 만들지 않습니다. LLM은 제한된 Pydantic `SceneSpec`만 만들고, 이 프로젝트가 그 값을 검증한 뒤 결정론적인 MJCF XML을 생성합니다.

## 전체 구조

흐름은 다음과 같습니다.

```text
자연어 prompt
-> OpenAI Responses API structured output
-> Pydantic SceneSpec
-> 의미/물리 검증
-> 결정론적 MJCF 생성
-> MuJoCo compile
-> 규칙 기반 pusher controller
-> success/failure/timeout 판정
-> artifacts 저장
```

주요 파일:

- `src/text2mujoco/schemas.py`: LLM이 반환할 수 있는 유일한 데이터 구조입니다.
- `src/text2mujoco/validation.py`: 좌표, 거리, pusher 시작점, 힘 범위 등을 검사합니다.
- `src/text2mujoco/mjcf_builder.py`: 검증된 값으로만 MuJoCo XML을 만듭니다.
- `src/text2mujoco/controller.py`: 강화학습이 아닌 결정론적 state machine controller입니다.
- `src/text2mujoco/simulation.py`: MuJoCo compile, named lookup, headless/viewer 실행, metrics 저장을 담당합니다.
- `src/text2mujoco/llm_client.py`: OpenAI Responses API structured output 연결입니다.

## Windows 11 초보자 설치 순서

### 1. Python 설치

1. [python.org](https://www.python.org/downloads/)에서 Python 3.12 이상을 설치합니다.
2. 설치 화면에서 **Add python.exe to PATH**를 체크합니다.
3. 설치 후 PowerShell을 새로 열고 확인합니다.

```powershell
python --version
```

`Python 3.12.x` 이상이면 됩니다.

### 2. VS Code 설치

1. [Visual Studio Code](https://code.visualstudio.com/)를 설치합니다.
2. VS Code 왼쪽 Extensions에서 **Python**을 검색합니다.
3. Microsoft가 만든 **Python** 확장을 설치합니다.

### 3. 프로젝트 폴더 열기

VS Code에서:

1. `File -> Open Folder...`
2. 이 `text2mujoco` 폴더를 선택합니다.
3. `Terminal -> New Terminal`을 엽니다.

PowerShell 현재 위치가 `text2mujoco`인지 확인합니다.

```powershell
pwd
```

### 4. 가상환경 만들기

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

PowerShell 실행 정책 오류가 나오면 현재 PowerShell 창에서만 우회합니다.

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\.venv\Scripts\Activate.ps1
```

VS Code 오른쪽 아래 Python interpreter가 `.venv`를 가리키는지 확인합니다. 다르면 `Ctrl+Shift+P`를 누르고 `Python: Select Interpreter`를 실행한 뒤 `.venv`를 선택합니다.

## 첫 실행

환경 진단:

```powershell
python -m text2mujoco doctor
```

API 없이 baseline 실행:

```powershell
python -m text2mujoco baseline --headless
```

Viewer가 가능한 PC에서 시각적으로 보기:

```powershell
python -m text2mujoco baseline --viewer
```

Viewer 창에서는 마우스로 회전, 휠로 확대/축소할 수 있습니다. GUI가 없는 환경에서는 `--headless`를 사용하세요.

## OpenAI API 키 설정

자연어로 새 환경을 만들 때만 API 키가 필요합니다. baseline, validate, run은 API 키 없이 동작합니다.

주의: ChatGPT Plus/Pro 구독과 OpenAI API 결제는 별도입니다. API 사용량은 [OpenAI Platform](https://platform.openai.com/) 계정의 billing에서 관리됩니다.

Windows 사용자 환경 변수로 설정:

```powershell
setx OPENAI_API_KEY "replace_with_your_real_key"
setx OPENAI_MODEL "gpt-5.6"
```

PowerShell을 완전히 닫았다가 새로 열어야 적용됩니다.

API 키 값을 README, 코드, `.env.example`, 테스트, 로그, artifact에 넣지 마세요.

자연어 생성 및 실행:

```powershell
python -m text2mujoco generate --prompt "무거운 빨간 상자를 오른쪽 위 목표로 미는 환경을 만들어줘. 바닥은 약간 미끄럽게 해줘." --headless
```

생성만 하고 실행하지 않기:

```powershell
python -m text2mujoco generate --prompt "가벼운 상자를 왼쪽 목표로 밀어줘" --no-run --headless
```

## 기존 JSON 실행

baseline이나 generate를 실행하면 `artifacts/<run_id>/scene_spec.json`이 생깁니다.

검증:

```powershell
python -m text2mujoco validate --spec artifacts\20260716_103000_a1b2c3d4\scene_spec.json
```

다시 실행:

```powershell
python -m text2mujoco run --spec artifacts\20260716_103000_a1b2c3d4\scene_spec.json --headless
```

## 생성되는 artifact

각 실행은 `artifacts/<run_id>/`에 저장됩니다.

```text
artifacts/
└─ 20260716_103000_a1b2c3d4/
   ├─ scene_spec.json
   ├─ scene.xml
   ├─ metrics.json
   ├─ manifest.json
   └─ run.log
```

`metrics.json`에는 성공 여부, 최종 거리, 최소 거리, simulation time, physics steps, 안정성 상태가 기록됩니다.

## 개발자 검증 명령

```powershell
python -m ruff format .
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
python -m text2mujoco baseline --headless
```

## 자주 나는 오류

### `py`를 찾을 수 없음

이 프로젝트 문서는 `py` 대신 `python`을 사용합니다. `python --version`이 실패하면 Python을 다시 설치하고 PATH 옵션을 체크하세요.

### `python`을 찾을 수 없음

Python 설치 시 PATH가 설정되지 않았을 가능성이 큽니다. Python을 다시 설치하면서 **Add python.exe to PATH**를 체크하거나 Windows 앱 실행 별칭에서 Python alias를 확인하세요.

### PowerShell 스크립트 실행 정책 오류

현재 창에서만 우회합니다.

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\.venv\Scripts\Activate.ps1
```

### `No module named mujoco`

가상환경이 활성화되지 않았거나 설치가 끝나지 않은 상태입니다.

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

### VS Code interpreter가 잘못됨

`Ctrl+Shift+P -> Python: Select Interpreter`에서 `.venv` 아래 Python을 선택하세요.

### OpenGL 또는 GLFW 오류

GUI viewer 문제입니다. 물리 시뮬레이션 검증은 렌더링 없이 가능합니다.

```powershell
python -m text2mujoco baseline --headless
```

### Viewer가 바로 종료됨

GUI 세션이 없거나 그래픽 드라이버/원격 데스크톱 문제가 있을 수 있습니다. `--headless`로 실행하고, 로컬 Windows 데스크톱에서 다시 `--viewer`를 시도하세요.

### `OPENAI_API_KEY` 없음

`generate`만 API 키가 필요합니다. API 없이 확인하려면:

```powershell
python -m text2mujoco baseline --headless
```

### 401 인증 오류

API 키가 틀렸거나 새 PowerShell에 반영되지 않았을 수 있습니다. 키를 다시 발급하고 새 터미널을 여세요.

### 429 quota/billing 오류

API 결제 또는 quota 문제입니다. OpenAI Platform billing을 확인하세요. ChatGPT 구독만으로 API quota가 생기지는 않습니다.

### MJCF/XML compile 오류

`scene_spec.json` 값이 물리적으로 불가능하거나 범위를 벗어난 경우입니다.

```powershell
python -m text2mujoco validate --spec path\to\scene_spec.json
```

### NaN 또는 unstable simulation

질량, 마찰, 목표 위치, pusher 힘이 맞지 않을 때 발생할 수 있습니다. baseline이 정상 실행되는지 먼저 확인하세요.

### GUI가 없는 환경

Codex, CI, 원격 서버에서는 viewer 검증을 생략하고 headless 명령을 사용하세요.

## 프로젝트 삭제 또는 가상환경 재생성

가상환경만 다시 만들기:

```powershell
deactivate
Remove-Item -Recurse -Force .venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

프로젝트를 삭제하려면 VS Code를 닫고 `text2mujoco` 폴더를 삭제하면 됩니다. `artifacts` 안의 실행 결과도 함께 지워집니다.
