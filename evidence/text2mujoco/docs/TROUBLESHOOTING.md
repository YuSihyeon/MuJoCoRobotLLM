# Troubleshooting

## 설치 확인

```powershell
python -m text2mujoco doctor
```

`mujoco`, `numpy`, `pydantic`, `openai`가 `OK`인지 확인하세요.

## Python을 찾을 수 없음

Python을 다시 설치하고 **Add python.exe to PATH**를 체크합니다. PowerShell을 새로 열고 확인합니다.

```powershell
python --version
```

## PowerShell 실행 정책 오류

현재 Process 범위에서만 우회합니다.

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\.venv\Scripts\Activate.ps1
```

## `No module named mujoco`

가상환경이 활성화되었는지 확인하고 다시 설치합니다.

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## 잘못된 VS Code interpreter

`Ctrl+Shift+P -> Python: Select Interpreter`에서 프로젝트의 `.venv`를 선택합니다.

## OpenGL 또는 GLFW 오류

Viewer 문제입니다. 먼저 headless를 실행하세요.

```powershell
python -m text2mujoco baseline --headless
```

headless가 성공하면 물리 엔진과 controller는 정상입니다. viewer는 로컬 그래픽 환경에서 다시 확인합니다.

## Viewer가 바로 종료됨

원격 세션, GUI 없는 환경, 그래픽 드라이버 문제일 수 있습니다. `--viewer` 대신 `--headless`를 사용하세요.

## `OPENAI_API_KEY` 없음

`generate` 명령에만 필요합니다. API 없이 baseline을 실행할 수 있습니다.

```powershell
python -m text2mujoco baseline --headless
```

## 401 인증 오류

API 키가 잘못되었거나 새 터미널에 반영되지 않았습니다. OpenAI Platform에서 키를 재발급하고 PowerShell을 새로 여세요.

## 429 quota 또는 billing 오류

API 사용량 한도 또는 결제 설정 문제입니다. ChatGPT 구독과 API billing은 별도입니다.

## MJCF/XML compile 오류

대부분 SceneSpec 값이 물리적으로 불가능한 경우입니다.

```powershell
python -m text2mujoco validate --spec path\to\scene_spec.json
```

검증 메시지에서 arena, target, pusher, mass, friction 관련 문제를 확인하세요.

## NaN 또는 unstable simulation

상자가 너무 무겁거나, 마찰이 너무 크거나, pusher force가 너무 작을 수 있습니다. baseline이 먼저 통과하는지 확인하고 `scene_spec.json`의 `box_mass`, `floor_friction`, `controller.max_force`를 점검하세요.

## API 비용이 걱정됨

`python -m pytest -q`, `baseline`, `validate`, `run`은 실제 API를 호출하지 않습니다. 실제 비용이 발생할 수 있는 경로는 사용자가 직접 실행한 `generate` 명령뿐입니다.
