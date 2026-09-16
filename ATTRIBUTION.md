# 출처와 자료 귀속

이 독립 저장소는 해당 연구의 기록과 공개 가능한 소스·산출물을 정리한다. 아래는 연구 계열에서 사용한 도구·데이터의 공통 출처 목록이며 해당 연구에 실제 사용한 항목은 README를 따른다. 외부 도구·데이터·코드를 연구자가 새로 발명하거나 단독 제작했다고 주장하지 않는다. 원본 프로젝트의 라이선스와 저작권 고지는 해당 항목에 계속 적용되며, 이 archive 전체에 임의의 단일 소프트웨어 라이선스를 덧씌우지 않았다.

| 대상 | 원출처·설명 |
|---|---|
| Graphdeco 3D Gaussian Splatting | [공식 구현](https://github.com/graphdeco-inria/gaussian-splatting), Kerbl et al., SIGGRAPH 2023. 학습·렌더링 핵심 구현의 출처 |
| Unity Gaussian Splatting | [aras-p/UnityGaussianSplatting](https://github.com/aras-p/UnityGaussianSplatting). Unity용 렌더러 및 import 기반 |
| COLMAP | [공식 프로젝트](https://colmap.github.io/). 카메라·희소 기하 복원 |
| CloudCompare | [공식 프로젝트](https://www.cloudcompare.org/). 점군 열람·분석 |
| Replica | [Meta Replica-Dataset](https://github.com/facebookresearch/Replica-Dataset). 스캔 공간과 semantic 자료 |
| ReplicaCAD | [AI Habitat 공식 데이터](https://huggingface.co/datasets/ai-habitat/ReplicaCAD_dataset), CC BY 4.0. 화면·시뮬레이션의 객체 형상·장면·metadata 원자료 |
| MuJoCo | [공식 프로젝트](https://github.com/google-deepmind/mujoco). 물리 엔진 |
| MuJoCo Menagerie / Panda | [공식 모델 모음](https://github.com/google-deepmind/mujoco_menagerie). 로봇 모델의 개별 라이선스를 따름 |
| Unreal / Unity | 각 엔진과 외부 plugin의 라이선스를 따름. 엔진·플러그인 전체를 재배포하지 않음 |
| 광학 데이터·Mitsuba·CNN | 개별 출처와 실험상 역할은 [광학 보고서](https://github.com/YuSihyeon/OpticalResearch)의 원문 및 source metadata에 기재 |
| OmniGibson / PhysX / YCB | [후속 물성 연구](https://github.com/YuSihyeon/GSPhysicalInference)의 source·실험 조건을 따름. 원본 대형 데이터와 hidden-GT는 제외 |
| 연구실 촬영과 실행 영상 | 사용자가 제공하거나 작업 폴더에 보관한 연구 자료. 원본 파일명·hash와 새 렌더링 여부를 별도 기록 |

소스 사본은 당시 작업 상태를 설명하기 위한 evidence이며, 수정된 프로젝트 소스와 upstream 원본의 차이는 각 보고서를 따른다. `source-map.json`은 로컬 전용이며 공개 사본으로 경로를 익명화하거나 설정의 credential을 제거한 경우 변환 내역을 남겼다.
