"""Unit tests for the Telegram /codex command flow."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import Message

from bot.codex import command_flow


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


def _deps(*, alive: bool = True) -> dict[str, object]:
    return {
        "approval_ui_bridge": SimpleNamespace(set_bot=MagicMock()),
        "codex_daemon": SimpleNamespace(is_alive=MagicMock(return_value=alive)),
        "codex_topic_state": AsyncMock(return_value="bound"),
        "send_topic_recovery_prompt": AsyncMock(),
        "ensure_global_orch": MagicMock(),
        "execute_codex_prompt": AsyncMock(),
        "handle_codex_new": AsyncMock(),
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
async def test_handle_codex_command_routes_streaming_prompt() -> None:
    bot = AsyncMock()
    message = _message("/codex list files", bot=bot)
    context = SimpleNamespace(session=AsyncMock())
    orchestrator = SimpleNamespace(ensure_transport_handlers=MagicMock())
    deps = _deps()

    await command_flow.handle_codex_command(message, context, orchestrator, **deps)

    deps["approval_ui_bridge"].set_bot.assert_called_once_with(bot)
    deps["codex_daemon"].is_alive.assert_called_once()
    orchestrator.ensure_transport_handlers.assert_called_once()
    deps["ensure_global_orch"].assert_called_once_with(orchestrator)
    deps["execute_codex_prompt"].assert_awaited_once()
    args = deps["execute_codex_prompt"].await_args.args
    assert args[0] is message
    assert args[2] is context
    assert args[3] is orchestrator
    assert args[4] == "list files"
