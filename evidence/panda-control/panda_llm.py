import os
import time
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel
from urlab_client import URLabClient


MODEL_NAME = "gpt-5.4-mini"
ROBOT_NAME = "panda_C_1"

ACTUATOR_NAMES = [
    "actuator1",
    "actuator2",
    "actuator3",
    "actuator4",
    "actuator5",
    "actuator6",
    "actuator7",
    "actuator8",
]

ACTUATOR_LIMITS = [
    (-2.8973, 2.8973),
    (-1.7628, 1.7628),
    (-2.8973, 2.8973),
    (-3.0718, -0.0698),
    (-2.8973, 2.8973),
    (-0.0175, 3.7525),
    (-2.8973, 2.8973),
    (0.0, 255.0),
]

HOME = [
    0.0,
    0.0,
    0.0,
    -1.57079,
    0.0,
    1.57079,
    -0.7853,
    255.0,
]

LEFT = [
    -0.35,
    0.0,
    0.0,
    -1.57079,
    0.0,
    1.57079,
    -0.7853,
    255.0,
]

RIGHT = [
    0.35,
    0.0,
    0.0,
    -1.57079,
    0.0,
    1.57079,
    -0.7853,
    255.0,
]


class RobotAction(BaseModel):
    name: Literal[
        "home",
        "left",
        "right",
        "open",
        "close",
        "stop",
        "unknown",
    ]


class RobotPlan(BaseModel):
    actions: list[RobotAction]
    summary: str


SYSTEM_PROMPT = """
당신은 Franka Emika Panda 로봇팔의 안전한 명령 해석기입니다.

사용자의 한국어 또는 영어 명령을 다음 동작만 사용해서 변환하세요.

- home: 기본 자세로 이동
- left: 왼쪽 자세로 이동
- right: 오른쪽 자세로 이동
- open: 그리퍼 열기
- close: 그리퍼 닫기
- stop: 현재 자세에서 정지
- unknown: 지원하지 않거나 위험하거나 모호한 명령

규칙:
1. 정의된 동작 외에는 절대로 만들지 마세요.
2. 직접적인 관절 각도나 힘 값을 만들지 마세요.
3. 여러 동작은 실행 순서대로 actions에 넣으세요.
4. 최대 5개의 동작만 만드세요.
5. 위험하거나 지원되지 않는 명령은 unknown으로 처리하세요.
6. 사용자가 직접 관절값, 힘, 속도를 지정하면 unknown으로 처리하세요.
7. 물체를 던지거나 충돌시키는 명령은 unknown으로 처리하세요.
8. summary에는 계획을 짧은 한국어로 설명하세요.
"""


def create_robot_plan(openai_client, user_text):
    response = openai_client.responses.parse(
        model=MODEL_NAME,
        input=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_text,
            },
        ],
        text_format=RobotPlan,
    )

    return response.output_parsed


def validate_plan(plan):
    if plan is None:
        return False, "LLM 결과를 해석하지 못했습니다."

    if not plan.actions:
        return False, "동작 목록이 비어 있습니다."

    if len(plan.actions) > 5:
        return False, "동작이 5개를 초과했습니다."

    if any(action.name == "unknown" for action in plan.actions):
        return False, "지원하지 않거나 위험하거나 모호한 명령입니다."

    return True, "안전 검사 통과"


def validate_pose(pose):
    if len(pose) != len(ACTUATOR_LIMITS):
        return False

    for value, limits in zip(pose, ACTUATOR_LIMITS):
        minimum, maximum = limits

        if value < minimum or value > maximum:
            return False

    return True


def print_plan(plan):
    print()
    print("LLM이 생성한 계획")
    print("-" * 50)

    for index, action in enumerate(plan.actions, start=1):
        print(f"{index}. {action.name}")

    print("설명:", plan.summary)
    print("-" * 50)


def send_control(urlab_client, robot, pose):
    if not validate_pose(pose):
        raise ValueError(
            "안전 범위를 벗어난 액추에이터 값이 감지됐습니다."
        )

    for actuator_name, value in zip(ACTUATOR_NAMES, pose):
        robot.actuators[actuator_name].set_ctrl(float(value))

    urlab_client.step(n_steps=1)


def hold_pose(
    urlab_client,
    robot,
    pose,
    seconds=0.5,
    hz=30,
):
    count = max(1, int(seconds * hz))

    for _ in range(count):
        send_control(urlab_client, robot, pose)
        time.sleep(1.0 / hz)


def move_smoothly(
    urlab_client,
    robot,
    start_pose,
    target_pose,
    seconds=2.0,
    hz=30,
):
    if not validate_pose(start_pose):
        raise ValueError("시작 자세가 안전 범위를 벗어났습니다.")

    if not validate_pose(target_pose):
        raise ValueError("목표 자세가 안전 범위를 벗어났습니다.")

    count = max(1, int(seconds * hz))

    for index in range(count + 1):
        alpha = index / count

        current_pose = [
            start + (target - start) * alpha
            for start, target in zip(start_pose, target_pose)
        ]

        send_control(
            urlab_client,
            robot,
            current_pose,
        )

        time.sleep(1.0 / hz)


def make_target_pose(action_name, current_pose):
    target_pose = current_pose.copy()

    if action_name == "home":
        target_pose = HOME.copy()

        # 현재 그리퍼 상태는 유지합니다.
        target_pose[7] = current_pose[7]

    elif action_name == "left":
        target_pose = LEFT.copy()
        target_pose[7] = current_pose[7]

    elif action_name == "right":
        target_pose = RIGHT.copy()
        target_pose[7] = current_pose[7]

    elif action_name == "open":
        target_pose[7] = 255.0

    elif action_name == "close":
        target_pose[7] = 0.0

    elif action_name == "stop":
        target_pose = current_pose.copy()

    else:
        raise ValueError(
            f"지원하지 않는 동작입니다: {action_name}"
        )

    return target_pose


def execute_plan(
    urlab_client,
    robot,
    plan,
    current_pose,
):
    for index, action in enumerate(plan.actions, start=1):
        action_name = action.name

        print()
        print(
            f"[{index}/{len(plan.actions)}] "
            f"{action_name} 동작을 실행합니다."
        )

        if action_name == "stop":
            hold_pose(
                urlab_client,
                robot,
                current_pose,
                seconds=0.5,
            )

            print("현재 자세를 유지합니다.")
            continue

        target_pose = make_target_pose(
            action_name,
            current_pose,
        )

        if action_name in ["open", "close"]:
            movement_seconds = 1.0
        else:
            movement_seconds = 2.0

        move_smoothly(
            urlab_client,
            robot,
            current_pose,
            target_pose,
            seconds=movement_seconds,
        )

        current_pose = target_pose

        hold_pose(
            urlab_client,
            robot,
            current_pose,
            seconds=0.3,
        )

        print(f"{action_name} 동작 완료")

    return current_pose


def main():
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY가 설정되지 않았습니다.")
        print("PowerShell에서 API 키를 먼저 설정하세요.")
        return

    openai_client = OpenAI()
    urlab_client = None
    robot = None
    current_pose = HOME.copy()

    print("=" * 60)
    print("Panda LLM 실제 제어 프로그램")
    print("=" * 60)

    try:
        print("Unreal URLab에 연결 중...")

        urlab_client = URLabClient(
            address="tcp://127.0.0.1",
            step_mode="live",
            step_port=5559,
            mujoco_version_check=True,
        )
        urlab_client.connect()

        if not urlab_client.manager_present:
            raise RuntimeError(
                "AMjManager를 찾을 수 없습니다. "
                "Unreal 플레이 모드를 확인하세요."
            )

        if ROBOT_NAME not in urlab_client.articulations:
            raise RuntimeError(
                f"{ROBOT_NAME}을 찾을 수 없습니다. "
                f"발견된 로봇: "
                f"{list(urlab_client.articulations.keys())}"
            )

        robot = urlab_client.articulations[ROBOT_NAME]

        missing_actuators = [
            name
            for name in ACTUATOR_NAMES
            if name not in robot.actuators
        ]

        if missing_actuators:
            raise RuntimeError(
                f"액추에이터가 없습니다: {missing_actuators}"
            )

        print("Unreal 연결 성공")
        print("선택된 로봇:", robot.name)
        print("home 제어값을 적용합니다.")

        hold_pose(
            urlab_client,
            robot,
            HOME,
            seconds=1.0,
        )

        print()
        print("입력 예시:")
        print("  오른쪽으로 움직인 다음 집게를 닫아")
        print("  집게를 열고 홈으로 돌아가")
        print("  왼쪽으로 이동해")
        print("  정지")
        print("  종료")
        print()

        while True:
            user_text = input("사용자 명령> ").strip()

            if not user_text:
                continue

            if user_text.lower() in [
                "종료",
                "끝",
                "quit",
                "exit",
            ]:
                print("프로그램을 종료합니다.")
                break

            # 정지 명령은 LLM/API를 거치지 않고 즉시 처리합니다.
            if user_text.lower() in [
                "정지",
                "멈춰",
                "멈춰라",
                "stop",
            ]:
                hold_pose(
                    urlab_client,
                    robot,
                    current_pose,
                    seconds=0.5,
                )

                print("현재 목표 자세를 유지합니다.")
                continue

            try:
                print("LLM이 명령을 해석하고 있습니다...")

                plan = create_robot_plan(
                    openai_client,
                    user_text,
                )

                if plan is None:
                    print("LLM 결과를 해석하지 못했습니다.")
                    continue

                print_plan(plan)

                is_safe, message = validate_plan(plan)

                if not is_safe:
                    print("실행 거부:", message)
                    continue

                print("검사 결과:", message)

                confirmation = input(
                    "이 계획을 실행할까요? (y/n)> "
                ).strip().lower()

                if confirmation not in [
                    "y",
                    "yes",
                    "예",
                    "네",
                ]:
                    print("사용자가 실행을 취소했습니다.")
                    continue

                current_pose = execute_plan(
                    urlab_client,
                    robot,
                    plan,
                    current_pose,
                )

                print()
                print("전체 계획 실행 완료")

            except Exception as error:
                print()
                print("명령 처리 중 오류가 발생했습니다.")
                print(type(error).__name__ + ":", error)
                print("로봇 동작을 중단하고 현재 상태를 유지합니다.")

        print("최종 자세를 유지한 상태로 연결을 종료합니다.")

    except KeyboardInterrupt:
        print()
        print("Ctrl+C가 입력되어 프로그램을 중단합니다.")
        print("Unreal의 빨간 정지 버튼으로도 정지할 수 있습니다.")

    except Exception as error:
        print()
        print("프로그램 오류:")
        print(type(error).__name__ + ":", error)

    finally:
        if urlab_client is not None:
            try:
                urlab_client.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()