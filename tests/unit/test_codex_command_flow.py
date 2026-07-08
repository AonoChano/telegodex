"""Unit tests for the Telegram /codex command flow."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import Message

from bot.codex import command_flow
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


def _deps(*, alive: bool = True, topic_state: str = "bound") -> dict[str, object]:
    return {
        "approval_ui_bridge": SimpleNamespace(set_bot=MagicMock()),
        "codex_daemon": SimpleNamespace(is_alive=MagicMock(return_value=alive)),
        "codex_topic_state": AsyncMock(return_value=topic_state),
        "send_topic_recovery_prompt": AsyncMock(),
        "ensure_global_orch": MagicMock(),
        "execute_codex_prompt": AsyncMock(),
        "handle_codex_new": AsyncMock(),
        "handle_codex_resume": AsyncMock(),
        "codex_topic_bound": "bound",
        "codex_topic_recoverable": "recoverable",
    }


@pytest.mark.asyncio
async def test_handle_codex_command_shows_usage_without_prompt() -> None:
    bot = AsyncMock()
    message = _message("/codex@telegodexbot", bot=bot)
    context = SimpleNamespace(session=AsyncMock())
    orchestrator = SimpleNamespace(ensure_transport_handlers=MagicMock())
    deps = _deps()

    await command_flow.handle_codex_command(message, context, orchestrator, **deps)

    bot.assert_awaited_once()
    method = bot.await_args.args[0]
    assert "Usage:" in method.text
    deps["codex_daemon"].is_alive.assert_not_called()
    orchestrator.ensure_transport_handlers.assert_not_called()


@pytest.mark.asyncio
async def test_handle_codex_command_rejects_streaming_prompt_in_all() -> None:
    bot = AsyncMock()
    message = _message("/codex list files", bot=bot)
    context = SimpleNamespace(session=AsyncMock())
    orchestrator = SimpleNamespace(ensure_transport_handlers=MagicMock())
    deps = _deps()

    await command_flow.handle_codex_command(message, context, orchestrator, **deps)

    deps["approval_ui_bridge"].set_bot.assert_called_once_with(bot)
    deps["codex_daemon"].is_alive.assert_not_called()
    orchestrator.ensure_transport_handlers.assert_not_called()
    deps["ensure_global_orch"].assert_not_called()
    deps["execute_codex_prompt"].assert_not_awaited()
    bot.assert_awaited_once()
    method = bot.await_args.args[0]
    assert "Open a Codex topic first" in method.text


@pytest.mark.asyncio
async def test_handle_codex_command_routes_new_to_topic_creation() -> None:
    bot = AsyncMock()
    message = _message("/codex new", bot=bot)
    context = SimpleNamespace(session=AsyncMock())
    orchestrator = SimpleNamespace(ensure_transport_handlers=MagicMock())
    deps = _deps()

    await command_flow.handle_codex_command(message, context, orchestrator, **deps)

    deps["handle_codex_new"].assert_awaited_once()
    args = deps["handle_codex_new"].await_args.args
    assert args[4] == SessionKey.from_telegram_message(100, None)
    deps["execute_codex_prompt"].assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_codex_command_routes_resume_to_topic_creation() -> None:
    bot = AsyncMock()
    message = _message("/codex resume 019f3f2b-fa28-7042-8d44-36f69db443f0", bot=bot)
    context = SimpleNamespace(session=AsyncMock())
    orchestrator = SimpleNamespace(ensure_transport_handlers=MagicMock())
    deps = _deps()

    await command_flow.handle_codex_command(message, context, orchestrator, **deps)

    deps["handle_codex_resume"].assert_awaited_once()
    args = deps["handle_codex_resume"].await_args.args
    assert args[4] == SessionKey.from_telegram_message(100, None)
    assert args[6] == "019f3f2b-fa28-7042-8d44-36f69db443f0"
    deps["execute_codex_prompt"].assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_codex_command_new_from_topic_does_not_reuse_topic_key() -> None:
    bot = AsyncMock()
    message = _message("/codex new", bot=bot, message_thread_id=222)
    context = SimpleNamespace(session=AsyncMock())
    orchestrator = SimpleNamespace(ensure_transport_handlers=MagicMock())
    deps = _deps(topic_state="bound")

    await command_flow.handle_codex_command(message, context, orchestrator, **deps)

    deps["handle_codex_new"].assert_awaited_once()
    args = deps["handle_codex_new"].await_args.args
    assert args[4] == SessionKey.from_telegram_message(100, None)


@pytest.mark.asyncio
async def test_handle_codex_command_resume_from_unbound_topic_opens_new_topic() -> None:
    bot = AsyncMock()
    message = _message("/codex resume thread-abc", bot=bot, message_thread_id=222)
    context = SimpleNamespace(session=AsyncMock())
    orchestrator = SimpleNamespace(ensure_transport_handlers=MagicMock())
    deps = _deps(topic_state="not_codex")

    await command_flow.handle_codex_command(message, context, orchestrator, **deps)

    deps["handle_codex_resume"].assert_awaited_once()
    args = deps["handle_codex_resume"].await_args.args
    assert args[4] == SessionKey.from_telegram_message(100, None)
    assert args[6] == "thread-abc"
    deps["send_topic_recovery_prompt"].assert_not_awaited()