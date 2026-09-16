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

# Panda 기본 자세
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

# Panda의 첫 번째 관절을 좌우로 움직이는 자세
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


def send_control(client, robot, values):
    for actuator_name, value in zip(ACTUATOR_NAMES, values):
        robot.actuators[actuator_name].set_ctrl(float(value))

    client.step(n_steps=1)


def move_smoothly(
    client,
    robot,
    start_pose,
    target_pose,
    seconds=2.0,
    hz=30,
):
    count = max(1, int(seconds * hz))

    for index in range(count + 1):
        alpha = index / count

        pose = [
            start + (target - start) * alpha
            for start, target in zip(start_pose, target_pose)
        ]

        send_control(client, robot, pose)
        time.sleep(1.0 / hz)


def hold_pose(client, robot, pose, seconds=0.5, hz=30):
    count = max(1, int(seconds * hz))

    for _ in range(count):
        send_control(client, robot, pose)
        time.sleep(1.0 / hz)


def normalize_command(text):
    text = text.strip().lower()

    aliases = {
        "홈": "home",
        "원위치": "home",
        "기본 자세": "home",
        "처음 자세": "home",

        "왼쪽": "left",
        "왼쪽으로": "left",
        "왼쪽으로 가": "left",
        "왼쪽으로 움직여": "left",

        "오른쪽": "right",
        "오른쪽으로": "right",
        "오른쪽으로 가": "right",
        "오른쪽으로 움직여": "right",

        "열어": "open",
        "집게 열어": "open",
        "그리퍼 열어": "open",
        "손 열어": "open",

        "닫아": "close",
        "집게 닫아": "close",
        "그리퍼 닫아": "close",
        "손 닫아": "close",

        "종료": "quit",
        "끝": "quit",
        "나가기": "quit",

        "도움말": "help",
        "도움": "help",
    }

    return aliases.get(text)


def print_help():
    print()
    print("사용할 수 있는 명령")
    print("  홈")
    print("  왼쪽")
    print("  오른쪽")
    print("  집게 열어")
    print("  집게 닫아")
    print("  도움말")
    print("  종료")
    print()


def main():
    client = None
    robot = None
    current_pose = HOME.copy()

    print("=" * 60)
    print("Panda 사용자 명령 제어")
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

        if not client.manager_present:
            raise RuntimeError(
                "AMjManager를 찾을 수 없습니다. "
                "Unreal 플레이 모드를 확인하세요."
            )

        if ROBOT_NAME not in client.articulations:
            raise RuntimeError(
                f"{ROBOT_NAME}을 찾을 수 없습니다. "
                f"발견된 로봇: {list(client.articulations.keys())}"
            )

        robot = client.articulations[ROBOT_NAME]

        print("연결 성공")
        print("선택된 로봇:", robot.name)
        print("안전한 home 자세를 적용합니다.")

        hold_pose(client, robot, HOME, seconds=1.0)
        print_help()

        while True:
            user_text = input("명령> ")
            command = normalize_command(user_text)

            if command is None:
                print("알 수 없는 명령입니다.")
                print("'도움말'을 입력해 명령 목록을 확인하세요.")
                continue

            if command == "quit":
                print("프로그램을 종료합니다.")
                break

            if command == "help":
                print_help()
                continue

            target_pose = current_pose.copy()

            if command == "home":
                target_pose = HOME.copy()
                print("home 자세로 이동합니다.")

            elif command == "left":
                target_pose = LEFT.copy()

                # 현재 그리퍼 상태는 그대로 유지
                target_pose[7] = current_pose[7]
                print("왼쪽 자세로 이동합니다.")

            elif command == "right":
                target_pose = RIGHT.copy()

                # 현재 그리퍼 상태는 그대로 유지
                target_pose[7] = current_pose[7]
                print("오른쪽 자세로 이동합니다.")

            elif command == "open":
                target_pose[7] = 255.0
                print("그리퍼를 엽니다.")

            elif command == "close":
                target_pose[7] = 0.0
                print("그리퍼를 닫습니다.")

            move_smoothly(
                client,
                robot,
                current_pose,
                target_pose,
                seconds=2.0,
            )

            current_pose = target_pose
            hold_pose(client, robot, current_pose, seconds=0.3)

            print("동작 완료")

    except KeyboardInterrupt:
        print()
        print("사용자가 프로그램을 중단했습니다.")

    except Exception as error:
        print()
        print("오류 발생:")
        print(type(error).__name__ + ":", error)
        raise

    finally:
        if client is not None and robot is not None:
            try:
                print("종료 전에 home 자세로 돌아갑니다.")

                move_smoothly(
                    client,
                    robot,
                    current_pose,
                    HOME,
                    seconds=1.5,
                )

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