# Experiments

## 재현 방법

모든 실험은 `SceneSpec.seed`와 저장된 `scene_spec.json`을 함께 기록합니다. 같은 spec과 같은 seed를 사용하면 MJCF 내용과 초기 조건을 재현할 수 있습니다.

```powershell
python -m text2mujoco baseline --headless
python -m text2mujoco run --spec artifacts\<run_id>\scene_spec.json --headless
```

## 여러 prompt 비교

prompt별로 생성된 `scene_spec.json`, `metrics.json`, `manifest.json`을 비교합니다.

추천 비교 항목:

- `box_mass`
- `floor_friction`
- `target_position`
- `final_box_target_distance`
- `minimum_box_target_distance`
- `success`
- `termination_reason`
- `simulation_time`

## 평가 지표

- compile success rate: MJCF가 MuJoCo에서 compile되는 비율.
- validation pass rate: SceneSpec이 의미/물리 검증을 통과하는 비율.
- simulation stability rate: NaN/Inf 없이 종료되는 비율.
- task success rate: 목표 반경 안에서 `success_hold_time` 동안 유지되는 비율.
- 평균 완료 시간: 성공한 run의 `simulation_time` 평균.
- 환경 다양성: 질량, 마찰, 목표 방향, 색상 등의 분산.

## SceneSpec 방식과 직접 MJCF 생성 방식 비교

직접 MJCF 생성 방식은 더 자유롭지만 compile 실패, 보안 위험, 재현성 저하가 커집니다. SceneSpec 방식은 표현력은 제한되지만 검증과 테스트가 쉬우며, 실패 원인을 사용자에게 설명하기 쉽습니다.

비교 실험 방법:

1. 같은 자연어 prompt 집합을 준비합니다.
2. SceneSpec 방식은 `generate`로 실행합니다.
3. 직접 MJCF 방식은 별도 sandbox에서만 실험하고, 이 프로젝트 runtime에는 연결하지 않습니다.
4. compile success rate, validation pass rate, stability rate, task success rate를 비교합니다.

## Seed 사용법

현재 baseline은 deterministic scene입니다. 향후 random obstacle이나 target sampling을 추가할 때도 seed를 `SceneSpec`에 저장하고 artifact manifest에 기록합니다.
