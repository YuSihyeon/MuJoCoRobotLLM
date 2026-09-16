import time

from urlab_client import URLabClient


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

# Panda 공식 home 키프레임의 액추에이터 제어값입니다.
# 마지막 255는 그리퍼를 연 상태입니다.
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

# 첫 번째 관절만 약 0.25 radian(약 14도) 움직이는 안전한 시험 자세
JOINT1_TEST = [
    0.25,
    0.0,
    0.0,
    -1.57079,
    0.0,
    1.57079,
    -0.7853,
    255.0,
]


def send_control(client, robot, values):
    """8개 액추에이터의 목표값을 Unreal로 전송합니다."""
    for actuator_name, value in zip(ACTUATOR_NAMES, values):
        robot.actuators[actuator_name].set_ctrl(value)

    client.step(n_steps=1)


def hold_pose(client, robot, pose, seconds, hz=30):
    """같은 자세를 일정 시간 유지합니다."""
    count = max(1, int(seconds * hz))

    for _ in range(count):
        send_control(client, robot, pose)
        time.sleep(1.0 / hz)


def move_smoothly(client, robot, start_pose, target_pose, seconds=2.0, hz=30):
    """시작 자세에서 목표 자세까지 부드럽게 이동합니다."""
    count = max(1, int(seconds * hz))

    for step_index in range(count + 1):
        alpha = step_index / count

        current_pose = [
            start + (target - start) * alpha
            for start, target in zip(start_pose, target_pose)
        ]

        send_control(client, robot, current_pose)
        time.sleep(1.0 / hz)


def print_joint_positions(robot):
    values = [round(float(value), 4) for value in robot.qpos_array]
    print("현재 관절 위치:", values)


def main():
    client = None
    robot = None

    print("=" * 60)
    print("Panda 수동 관절 제어 시험")
    print("=" * 60)

    try:
        print("Unreal URLab에 연결 중...")

        client = URLabClient(
            address="tcp://127.0.0.1",
            step_mode="live",
            step_port=5559,
            mujoco_version_check=True,
        )
        client.connect()

        print("연결 성공")
        print("manager_present:", client.manager_present)

        if not client.manager_present:
            raise RuntimeError(
                "AMjManager가 발견되지 않았습니다. "
                "Unreal 플레이 모드를 확인하세요."
            )

        robots = list(client.articulations.keys())
        print("발견된 로봇:", robots)

        if ROBOT_NAME not in client.articulations:
            raise RuntimeError(
                f"{ROBOT_NAME} 로봇이 없습니다. 발견된 로봇: {robots}"
            )

        robot = client.articulations[ROBOT_NAME]
        print("선택된 로봇:", robot.name)

        missing_actuators = [
            name
            for name in ACTUATOR_NAMES
            if name not in robot.actuators
        ]

        if missing_actuators:
            raise RuntimeError(
                f"다음 액추에이터가 없습니다: {missing_actuators}"
            )

        print()
        print("0단계: home 제어값을 적용합니다.")
        hold_pose(client, robot, HOME, seconds=1.0)
        print_joint_positions(robot)

        print()
        print("1단계: joint1을 약 14도 부드럽게 움직입니다.")
        move_smoothly(
            client,
            robot,
            HOME,
            JOINT1_TEST,
            seconds=2.0,
        )

        print("시험 자세를 1초 유지합니다.")
        hold_pose(client, robot, JOINT1_TEST, seconds=1.0)
        print_joint_positions(robot)

        print()
        print("2단계: home 자세로 부드럽게 돌아갑니다.")
        move_smoothly(
            client,
            robot,
            JOINT1_TEST,
            HOME,
            seconds=2.0,
        )

        hold_pose(client, robot, HOME, seconds=1.0)
        print_joint_positions(robot)

        print()
        print("Panda 수동 제어 시험 완료")

    except KeyboardInterrupt:
        print()
        print("사용자가 시험을 중단했습니다.")

    except Exception as error:
        print()
        print("오류가 발생했습니다.")
        print(type(error).__name__ + ":", error)
        raise

    finally:
        # 종료 또는 오류 발생 시 안전한 home 제어값을 다시 전달합니다.
        if client is not None and robot is not None:
            try:
                print("안전을 위해 home 제어값을 적용합니다.")
                hold_pose(client, robot, HOME, seconds=0.5)
            except Exception:
                pass

        if client is not None:
            try:
                client.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()