import time

from urlab_client import URLabClient


LEFT_ACTUATOR = "left_wheel_velocity"
RIGHT_ACTUATOR = "right_wheel_velocity"


def set_wheels(robot, left_speed, right_speed):
    """왼쪽·오른쪽 바퀴의 목표 속도를 지정한다."""
    robot.actuators[LEFT_ACTUATOR].set_ctrl(left_speed)
    robot.actuators[RIGHT_ACTUATOR].set_ctrl(right_speed)


def move_for(client, robot, left_speed, right_speed, seconds, message):
    """지정한 시간 동안 바퀴를 움직인다."""
    print(message)

    set_wheels(robot, left_speed, right_speed)

    end_time = time.monotonic() + seconds

    while time.monotonic() < end_time:
        # set_ctrl()에 저장한 값을 Unreal로 전송한다.
        client.step(n_steps=1)
        time.sleep(0.05)

    set_wheels(robot, 0.0, 0.0)
    client.step(n_steps=1)
    time.sleep(0.5)


def main():
    print("Unreal URLab에 연결 중...")

    with URLabClient(
        "tcp://localhost",
        step_mode="live",
        step_port=5559,
    ) as client:

        # 현재 브리지 버전에서는 discover()가 아니라 connect()를 사용한다.
        client.connect()

        print("연결 성공")
        print("manager_present:", client.manager_present)
        print("발견된 로봇:", list(client.articulations.keys()))

        if not client.manager_present:
            print()
            print("AMjManager를 찾지 못했습니다.")
            print("Unreal에서 플레이 모드가 실행 중인지 확인하세요.")
            return

        if not client.articulations:
            print()
            print("발견된 로봇이 없습니다.")
            print("diffbot과 AMjManager가 레벨에 배치되어 있는지 확인하세요.")
            return

        # 현재 레벨에 있는 첫 번째 로봇을 선택한다.
        robot = next(iter(client.articulations.values()))

        print("선택된 로봇:", robot.prefix)
        print("발견된 액추에이터:", list(robot.actuators.keys()))

        missing = [
            name
            for name in (LEFT_ACTUATOR, RIGHT_ACTUATOR)
            if name not in robot.actuators
        ]

        if missing:
            print()
            print("필요한 액추에이터 이름을 찾지 못했습니다:", missing)
            print("위에 출력된 '발견된 액추에이터' 목록을 확인하세요.")
            return

        try:
            move_for(
                client,
                robot,
                left_speed=3.0,
                right_speed=3.0,
                seconds=2.0,
                message="1단계: 양쪽 바퀴를 같은 방향으로 움직입니다.",
            )

            move_for(
                client,
                robot,
                left_speed=-2.0,
                right_speed=2.0,
                seconds=1.5,
                message="2단계: 제자리 회전을 시도합니다.",
            )

            move_for(
                client,
                robot,
                left_speed=-3.0,
                right_speed=-3.0,
                seconds=2.0,
                message="3단계: 양쪽 바퀴를 반대 방향으로 움직입니다.",
            )

        finally:
            # 실행 중 오류가 발생하더라도 바퀴를 정지시킨다.
            set_wheels(robot, 0.0, 0.0)
            client.step(n_steps=1)

        print("수동 주행 시험 완료")


if __name__ == "__main__":
    main()