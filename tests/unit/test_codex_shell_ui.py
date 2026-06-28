"""Unit tests for Telegram shell UI helpers."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import Message

from ai.base import AIResponse
from bot.codex import shell_ui
from bot.utils.routing import TelegramRoute
from core.session import SessionKey


def _message(
    text: str,
    *,
    bot: AsyncMock | None = None,
    chat_id: int = 100,
    chat_type: str = "supergroup",
    user_id: int = 7,
    message_thread_id: int | None = None,
) -> Message:
    payload = {
        "message_id": 1,
        "date": int(datetime.now().timestamp()),
        "chat": {"id": chat_id, "type": chat_type},
        "from": {
            "id": user_id,
            "is_bot": False,
            "first_name": "Test",
        },
        "text": text,
    }
    if message_thread_id is not None:
        payload["message_thread_id"] = message_thread_id
        payload["is_topic_message"] = True
    message = Message.model_validate(payload)
    return message.as_(bot or AsyncMock())


@pytest.mark.asyncio
async def test_handle_shell_command_without_args_or_help_shows_usage() -> None:
    for text in ("/shell", "/shell -h", "/shell help", "/shell --help"):
        bot = AsyncMock()
        message = _message(text, bot=bot)

        await shell_ui.handle_shell_command(message, SimpleNamespace())

        bot.assert_awaited_once()
        method = bot.await_args.args[0]
        assert "Usage:" in method.text
        assert "/shell <natural language task>" in method.text
        assert "/shell !<command>" in method.text


@pytest.mark.asyncio
async def test_handle_shell_command_natural_language_generates_command_proposal() -> None:
    bot = AsyncMock()
    status_msg = SimpleNamespace(edit_text=AsyncMock())
    bot.return_value = status_msg
    message = _message("/shell show current directory", bot=bot)
    provider = SimpleNamespace(
        default_model="test-model",
        chat=AsyncMock(
            return_value=AIResponse(
                content='{"command":"Get-Location","explanation":"Shows cwd","risk":"Read-only"}',
                model="test-model",
            )
        ),
    )
    context = SimpleNamespace(
        get_or_create_user=AsyncMock(
            return_value=SimpleNamespace(preferred_provider="deepseek", preferred_model="deepseek-test")
        )
    )
    orchestrator = SimpleNamespace(
        providers=SimpleNamespace(get_provider=MagicMock(return_value=provider)),
        pending_shell_commands={},
    )

    await shell_ui.handle_shell_command(message, orchestrator, context)

    context.get_or_create_user.assert_awaited_once_with(7)
    provider.chat.assert_awaited_once()
    assert len(orchestrator.pending_shell_commands) == 1
    pending = next(iter(orchestrator.pending_shell_commands.values()))
    assert pending["command"] == "Get-Location"
    status_msg.edit_text.assert_awaited_once()
    _, kwargs = status_msg.edit_text.await_args
    assert "reply_markup" in kwargs
    assert kwargs["reply_markup"].inline_keyboard[0][0].text == "Run"
    assert kwargs["parse_mode"] == "HTML"


@pytest.mark.asyncio
async def test_handle_shell_command_natural_language_no_command_uses_html_without_buttons() -> None:
    bot = AsyncMock()
    status_msg = SimpleNamespace(edit_text=AsyncMock())
    bot.return_value = status_msg
    message = _message("/shell delete all important files", bot=bot)
    provider = SimpleNamespace(
        default_model="test-model",
        chat=AsyncMock(
            return_value=AIResponse(
                content='{"command":"","explanation":"Too destructive","risk":"High"}',
                model="test-model",
            )
        ),
    )
    orchestrator = SimpleNamespace(
        providers=SimpleNamespace(get_provider=MagicMock(return_value=provider)),
        pending_shell_commands={},
    )

    await shell_ui.handle_shell_command(message, orchestrator)

    assert orchestrator.pending_shell_commands == {}
    status_msg.edit_text.assert_awaited_once()
    _, kwargs = status_msg.edit_text.await_args
    assert kwargs["parse_mode"] == "HTML"
    assert "reply_markup" not in kwargs


@pytest.mark.asyncio
async def test_handle_shell_command_raw_prefix_executes_directly() -> None:
    bot = AsyncMock()
    message = _message("/shell !git status", bot=bot, message_thread_id=222)
    execute = AsyncMock()
    orchestrator = SimpleNamespace(
        shell_is_dangerous=MagicMock(return_value=False),
        pending_shell_commands={},
    )

    await shell_ui.handle_shell_command(message, orchestrator, execute_shell=execute)

    execute.assert_awaited_once()
    assert execute.await_args.args[3] == "git status"
    assert execute.await_args.args[4] == SessionKey.from_telegram_message(100, 222)


@pytest.mark.asyncio
async def test_shell_ai_run_callback_executes_safe_command() -> None:
    bot = AsyncMock()
    message = _message("proposal", bot=bot)
    route = TelegramRoute.from_message(message)
    session_key = SessionKey.from_telegram_message(100, None)
    execute = AsyncMock()
    orchestrator = SimpleNamespace(
        pending_shell_commands={
            "proposal-1": {
                "command": "Get-Location",
                "message": message,
                "route": route,
                "session_key": session_key,
            }
        },
        shell_is_dangerous=MagicMock(return_value=False),
    )
    callback_query = SimpleNamespace(
        data="shell_ai:proposal-1:run",
        message=message,
        answer=AsyncMock(),
    )

    await shell_ui.handle_shell_ai_callback(callback_query, orchestrator, execute_shell=execute)

    callback_query.answer.assert_awaited_once_with("Executing...")
    execute.assert_awaited_once_with(message, route, orchestrator, "Get-Location", session_key)
    assert orchestrator.pending_shell_commands == {}


@pytest.mark.asyncio
async def test_shell_ai_run_callback_requires_second_confirmation_for_dangerous_command() -> None:
    bot = AsyncMock()
    message = _message("proposal", bot=bot)
    route = TelegramRoute.from_message(message)
    session_key = SessionKey.from_telegram_message(100, None)
    orchestrator = SimpleNamespace(
        pending_shell_commands={
            "proposal-1": {
                "command": "shutdown /s",
                "message": message,
                "route": route,
                "session_key": session_key,
            }
        },
        shell_is_dangerous=MagicMock(return_value=True),
    )
    callback_query = SimpleNamespace(
        data="shell_ai:proposal-1:run",
        message=message,
        answer=AsyncMock(),
    )

    await shell_ui.handle_shell_ai_callback(callback_query, orchestrator)

    callback_query.answer.assert_awaited_once_with("Confirmation required")
    assert "proposal-1" not in orchestrator.pending_shell_commands
    assert len(orchestrator.pending_shell_commands) == 1
    pending = next(iter(orchestrator.pending_shell_commands.values()))
    assert pending["command"] == "shutdown /s"


@pytest.mark.asyncio
async def test_shell_approve_callback_confirm_executes_command() -> None:
    bot = AsyncMock()
    message = _message("approval", bot=bot)
    route = TelegramRoute.from_message(message)
    session_key = SessionKey.from_telegram_message(100, None)
    execute = AsyncMock()
    orchestrator = SimpleNamespace(
        pending_shell_commands={
            "approval-1": {
                "command": "Get-Location",
                "message": message,
                "route": route,
                "session_key": session_key,
            }
        },
    )
    callback_query = SimpleNamespace(
        data="shell_approve:approval-1:confirm",
        message=message,
        answer=AsyncMock(),
    )

    await shell_ui.handle_shell_approve_callback(callback_query, orchestrator, execute_shell=execute)

    callback_query.answer.assert_awaited_once_with("Executing...")
    execute.assert_awaited_once_with(message, route, orchestrator, "Get-Location", session_key)
    assert orchestrator.pending_shell_commands == {}


@pytest.mark.asyncio
async def test_shell_approve_callback_cancel_edits_request_without_execution() -> None:
    bot = AsyncMock()
    message = _message("approval", bot=bot)
    route = TelegramRoute.from_message(message)
    session_key = SessionKey.from_telegram_message(100, None)
    execute = AsyncMock()
    orchestrator = SimpleNamespace(
        pending_shell_commands={
            "approval-1": {
                "command": "Remove-Item important.txt",
                "message": message,
                "route": route,
                "session_key": session_key,
            }
        },
    )
    callback_query = SimpleNamespace(
        data="shell_approve:approval-1:cancel",
        message=message,
        answer=AsyncMock(),
    )

    await shell_ui.handle_shell_approve_callback(callback_query, orchestrator, execute_shell=execute)

    callback_query.answer.assert_awaited_once_with("Cancelled")
    execute.assert_not_awaited()
    assert orchestrator.pending_shell_commands == {}
