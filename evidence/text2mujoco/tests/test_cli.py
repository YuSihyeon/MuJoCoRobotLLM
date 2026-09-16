from __future__ import annotations

from text2mujoco.cli import build_parser


def test_cli_accepts_arm_chat_command() -> None:
    args = build_parser().parse_args(["arm-chat"])

    assert args.command == "arm-chat"


def test_cli_accepts_arm_prompt_command_with_headless_mode() -> None:
    args = build_parser().parse_args(
        ["arm-prompt", "--prompt", "move the cube slowly", "--headless"]
    )

    assert args.command == "arm-prompt"
    assert args.prompt == "move the cube slowly"
    assert args.headless is True
