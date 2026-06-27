from __future__ import annotations

from core.orchestrator.chat_tools import (
    build_telegodex_capability_prompt,
    build_tool_result_message,
    next_permission_mode,
    parse_chat_tool_request,
    permission_mode_label,
)


def test_permission_mode_labels_and_cycle() -> None:
    assert permission_mode_label(None) == "用户确认"
    assert next_permission_mode("confirm") == "full"
    assert next_permission_mode("full") == "chat"
    assert next_permission_mode("chat") == "confirm"


def test_capability_prompt_blocks_tools_in_chat_mode() -> None:
    prompt = build_telegodex_capability_prompt("chat")

    assert "Telegodex" in prompt
    assert "Tool use is disabled" in prompt
    assert "仅对话" in prompt


def test_parse_chat_tool_request_requires_telegodex_tool_key() -> None:
    assert parse_chat_tool_request('{"command":"Get-Location"}') is None

    request = parse_chat_tool_request(
        '```json\n{"telegodex_tool":"shell","command":"Get-Location","reason":"check cwd","risk":"read-only"}\n```'
    )

    assert request is not None
    assert request.tool == "shell"
    assert request.command == "Get-Location"
    assert request.reason == "check cwd"


def test_build_tool_result_message_formats_stdout_and_stderr() -> None:
    request = parse_chat_tool_request('{"telegodex_tool":"shell","command":"Get-ChildItem"}')
    assert request is not None

    msg = build_tool_result_message(
        request,
        {"returncode": 1, "stdout": "out", "stderr": "err", "timeout": False},
    )

    assert "command: Get-ChildItem" in msg.content
    assert "exit_code: 1" in msg.content
    assert "stdout:\nout" in msg.content
    assert "stderr:\nerr" in msg.content


def test_capability_prompt_maps_browser_and_app_requests_to_shell_tools() -> None:
    prompt = build_telegodex_capability_prompt("confirm")

    assert "Do not say you cannot open websites" in prompt
    assert "Start-Process https://www.bilibili.com" in prompt
    assert "Start-Process notepad" in prompt
    assert "Never invent a demo command" in prompt
