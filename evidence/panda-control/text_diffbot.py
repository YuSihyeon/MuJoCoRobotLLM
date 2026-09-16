import re
import time

from urlab_client import URLabClient


LEFT_ACTUATOR = "left_wheel_velocity"
RIGHT_ACTUATOR = "right_wheel_velocity"

FORWARD_SPEED = 3.0
TURN_SPEED = 2.0
DEFAULT_DURATION = 1.5
MAX_DURATION = 5.0


def set_wheels(robot, left_speed, right_speed):
    """양쪽 바퀴의 속도를 설정한다."""
    robot.actuators[LEFT_ACTUATOR].set_ctrl(left_speed)
    robot.actuators[RIGHT_ACTUATOR].set_ctrl(right_speed)


def stop_robot(client, robot):
    """로봇을 즉시 정지시킨다."""
    set_wheels(robot, 0.0, 0.0)
    client.step(n_steps=1)


def extract_duration(command):
    """
    명령에서 '3초', '1.5초' 같은 시간을 찾는다.
    시간이 없으면 기본값을 사용하며 최대 5초로 제한한다.
    """
    match = re.search(r"(\d+(?:\.\d+)?)\s*초", command)

    if match is None:
        return DEFAULT_DURATION

    duration = float(match.group(1))
    return max(0.1, min(duration, MAX_DURATION))


def parse_command(command):
    """
    사용자의 문장을 안전한 로봇 행동으로 변환한다.

    반환값:
        action, left_speed, right_speed, duration
    """
    text = command.strip().lower()
    duration = extract_duration(text)

    if text in ("종료", "끝", "나가기", "exit", "quit"):
        return "exit", 0.0, 0.0, 0.0

    if any(word in text for word in ("정지", "멈춰", "멈추기", "stop")):
        return "stop", 0.0, 0.0, 0.0

    if any(word in text for word in ("좌회전", "왼쪽", "left")):
        return "turn_left", -TURN_SPEED, TURN_SPEED, duration

    if any(word in text for word in ("우회전", "오른쪽", "right")):
        return "turn_right", TURN_SPEED, -TURN_SPEED, duration

    if any(word in text for word in ("후진", "뒤로", "backward", "reverse")):
        return (
            "backward",
            -FORWARD_SPEED,
            -FORWARD_SPEED,
            duration,
        )

    if any(word in text for word in ("전진", "앞으로", "직진", "forward")):
        return (
            "forward",
            FORWARD_SPEED,
            FORWARD_SPEED,
            duration,
        )

    return None


def execute_motion(
    client,
    robot,
    left_speed,
    right_speed,
    duration,
):
    """해석된 바퀴 속도를 정해진 시간 동안 실행한다."""
    set_wheels(robot, left_speed, right_speed)

    deadline = time.monotonic() + duration

    try:
        while time.monotonic() < deadline:
            client.step(n_steps=1)
            time.sleep(0.05)

    finally:
        stop_robot(client, robot)


def main():
    print("Unreal URLab에 연결 중...")

    with URLabClient(
        "tcp://localhost",
        step_mode="live",
        step_port=5559,
    ) as client:
        client.connect()

        if not client.manager_present:
            print("AMjManager를 찾지 못했습니다.")
            print("Unreal 플레이 모드를 먼저 실행하세요.")
            return

        if not client.articulations:
            print("발견된 로봇이 없습니다.")
            return

        robot = next(iter(client.articulations.values()))

        print("연결 성공")
        print("선택된 로봇:", robot.prefix)
        print("액추에이터:", list(robot.actuators.keys()))

        missing = [
            name
            for name in (LEFT_ACTUATOR, RIGHT_ACTUATOR)
            if name not in robot.actuators
        ]

        if missing:
            print("필요한 액추에이터가 없습니다:", missing)
            return

        print()
        print("명령 입력을 시작합니다.")
        print("예시:")
        print("  앞으로 1초")
        print("  뒤로 2초")
        print("  왼쪽으로 1초 돌아")
        print("  오른쪽으로 돌아")
        print("  정지")
        print("  종료")
        print()
        print("안전을 위해 한 번의 동작은 최대 5초입니다.")

        try:
            while True:
                try:
                    user_command = input("\n명령> ")
                except EOFError:
                    break

                result = parse_command(user_command)

                if result is None:
                    print("명령을 이해하지 못했습니다.")
                    print("전진, 후진, 왼쪽, 오른쪽, 정지를 사용하세요.")
                    continue

                action, left, right, duration = result

                if action == "exit":
                    print("프로그램을 종료합니다.")
                    break

                if action == "stop":
                    stop_robot(client, robot)
                    print("로봇을 정지했습니다.")
                    continue

                print(
                    f"명령 해석: {action}, "
                    f"왼쪽={left}, 오른쪽={right}, "
                    f"시간={duration:.1f}초"
                )

                execute_motion(
                    client,
                    robot,
                    left,
                    right,
                    duration,
                )

                print("동작 완료")

        except KeyboardInterrupt:
            print("\n사용자가 실행을 중단했습니다.")

        finally:
            stop_robot(client, robot)
            print("로봇을 안전하게 정지했습니다.")


if __name__ == "__main__":
    main()