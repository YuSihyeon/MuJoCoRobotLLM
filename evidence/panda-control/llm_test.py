import os
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel


MODEL_NAME = "gpt-5.4-mini"


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
당신은 Franka Emika Panda 로봇팔의 명령 해석기입니다.

사용자의 한국어 또는 영어 명령을 다음 동작만 사용해서 변환하세요.

- home: 기본 자세로 이동
- left: 로봇팔을 왼쪽 자세로 이동
- right: 로봇팔을 오른쪽 자세로 이동
- open: 그리퍼 열기
- close: 그리퍼 닫기
- stop: 아무 동작도 하지 않고 정지
- unknown: 지원하지 않거나 위험하거나 모호한 명령

규칙:
1. 반드시 정의된 동작만 사용하세요.
2. 직접적인 관절 각도나 힘 값을 만들지 마세요.
3. 한 문장에 여러 명령이 있으면 실행 순서대로 actions에 넣으세요.
4. 최대 5개 동작만 만드세요.
5. 위험하거나 지원하지 않는 동작은 unknown으로 처리하세요.
6. summary에는 계획을 짧은 한국어로 설명하세요.
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
        return False, "지원하지 않거나 모호한 명령입니다."

    return True, "안전 검사 통과"


def print_plan(plan):
    print()
    print("LLM이 생성한 계획")
    print("-" * 40)

    for index, action in enumerate(plan.actions, start=1):
        print(f"{index}. {action.name}")

    print("설명:", plan.summary)
    print("-" * 40)


def main():
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY가 설정되지 않았습니다.")
        print("PowerShell에서 API 키를 먼저 설정하세요.")
        return

    openai_client = OpenAI()

    print("=" * 60)
    print("Panda LLM 명령 해석 시험")
    print("=" * 60)
    print("이번 시험에서는 Panda가 실제로 움직이지 않습니다.")
    print("'종료'를 입력하면 프로그램이 끝납니다.")
    print()

    while True:
        user_text = input("사용자 명령> ").strip()

        if not user_text:
            continue

        if user_text in ["종료", "끝", "quit", "exit"]:
            print("프로그램을 종료합니다.")
            break

        try:
            print("LLM이 명령을 해석하고 있습니다...")

            plan = create_robot_plan(
                openai_client,
                user_text,
            )

            print_plan(plan)

            is_safe, message = validate_plan(plan)

            if is_safe:
                print("검사 결과:", message)
                print("※ 시험 모드이므로 로봇은 움직이지 않습니다.")
            else:
                print("검사 결과: 실행 거부")
                print("이유:", message)

            print()

        except Exception as error:
            print()
            print("OpenAI API 호출 중 오류가 발생했습니다.")
            print(type(error).__name__ + ":", error)
            print()


if __name__ == "__main__":
    main()