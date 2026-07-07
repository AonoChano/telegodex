"""Unit tests for Codex Telegram command routing helpers."""

from __future__ import annotations

from datetime import datetime

from aiogram.types import Message

from bot.codex import command_ui


def _message(text: str) -> Message:
    return Message.model_validate(
        {
            "message_id": 1,
            "date": int(datetime.now().timestamp()),
            "chat": {"id": 100, "type": "supergroup"},
            "from": {
                "id": 7,
                "is_bot": False,
                "first_name": "Test",
            },
            "text": text,
        }
    )


def test_command_args_accepts_plain_commands_and_bot_mentions() -> None:
    assert command_ui.command_args("/codex list files", "codex") == "list files"
    assert command_ui.command_args(" /codex   status ", "codex") == "status"
    assert command_ui.command_args("/codex@telegodexbot run tests", "codex") == "run tests"
    assert command_ui.command_args("/codex@telegodexbot", "codex") == ""


def test_command_args_returns_non_command_text_unchanged_except_outer_space() -> None:
    assert command_ui.command_args("  explain this repository  ", "codex") == "explain this repository"


def test_topic_prompt_text_uses_codex_command_rules() -> None:
    assert command_ui.topic_prompt_text(_message("/codex@bot hello")) == "hello"


def test_is_streaming_prompt_keeps_conversation_prompts_streaming() -> None:
    assert command_ui.is_streaming_prompt("list all Python files") is True
    assert command_ui.is_streaming_prompt("new feature idea") is True


def test_is_streaming_prompt_identifies_orchestrator_commands() -> None:
    for prompt in ["new", "status", "pwd", "threads", "archive", "cd C:/repo", "switch abc"]:
        assert command_ui.is_streaming_prompt(prompt) is False


def test_is_streaming_prompt_identifies_instruction_prefixes() -> None:
    assert command_ui.is_streaming_prompt("/status") is False
    assert command_ui.is_streaming_prompt("@README.md") is False
    assert command_ui.is_streaming_prompt("!git status") is True


def test_usage_text_contains_core_commands() -> None:
    assert "/codex &lt;prompt&gt;" in command_ui.CODEX_USAGE_HTML
    assert "/codex new" in command_ui.CODEX_USAGE_HTML


def test_usage_text_keeps_screenshot_outside_codex_commands() -> None:
    assert "/screenshot" not in command_ui.CODEX_USAGE_HTML
