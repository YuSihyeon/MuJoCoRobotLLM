from urlab_client import URLabClient


def value_text(value):
    """Enum 또는 일반 값을 보기 쉬운 문자열로 변환한다."""
    if value is None:
        return "None"

    if hasattr(value, "value"):
        return str(value.value)

    return str(value)


def range_text(value):
    """관절·액추에이터 범위를 문자열로 변환한다."""
    if value is None:
        return "제한 없음"

    return f"{tuple(float(x) for x in value)}"


def main():
    print("=" * 60)
    print("Panda 정보 확인 프로그램")
    print("=" * 60)
    print("Unreal URLab에 연결 중...")

    with URLabClient(
        "tcp://localhost",
        step_mode="live",
        step_port=5559,
    ) as client:
        client.connect()

        print("연결 성공")
        print("manager_present:", client.manager_present)
        print("MuJoCo 서버 버전:", client.mujoco_version)
        print("발견된 로봇:", list(client.articulations.keys()))

        if not client.manager_present:
            print()
            print("AMjManager가 발견되지 않았습니다.")
            print("Unreal 바깥쪽 플레이 모드가 실행 중인지 확인하세요.")
            return

        if not client.articulations:
            print()
            print("발견된 로봇이 없습니다.")
            return

        robot = next(iter(client.articulations.values()))

        print()
        print("=" * 60)
        print("선택된 로봇")
        print("=" * 60)
        print("로봇 이름:", robot.prefix)
        print("제어 모드:", value_text(robot.control_mode))

        print()
        print("=" * 60)
        print("관절 목록")
        print("=" * 60)

        for index, (name, joint) in enumerate(
            robot.joints.items(),
            start=1,
        ):
            print(f"[{index}] {name}")
            print(f"    MuJoCo ID: {joint.id}")
            print(f"    관절 유형 번호: {joint.jnt_type}")
            print(f"    위치 차원: {joint.qpos_dim}")
            print(f"    속도 차원: {joint.qvel_dim}")
            print(f"    허용 범위: {range_text(joint.range)}")

        print()
        print("=" * 60)
        print("액추에이터 목록")
        print("=" * 60)

        for index, (name, actuator) in enumerate(
            robot.actuators.items(),
            start=1,
        ):
            print(f"[{index}] {name}")
            print(f"    MuJoCo ID: {actuator.id}")
            print(f"    연결 관절: {actuator.joint}")
            print(f"    액추에이터 유형: {value_text(actuator.type)}")
            print(f"    전달 유형: {value_text(actuator.trn_type)}")
            print(f"    제어 범위: {range_text(actuator.ctrlrange)}")
            print(f"    힘 범위: {range_text(actuator.forcerange)}")

        print()
        print("=" * 60)
        print("검사 완료")
        print("=" * 60)


if __name__ == "__main__":
    main()