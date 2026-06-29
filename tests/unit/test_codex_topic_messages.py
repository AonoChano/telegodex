"""Unit tests for Codex-bound topic message flow."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.types import Message

from bot.codex import topic_messages


def _message(
    text: str,
    *,
    bot: AsyncMock | None = None,
    chat_id: int = 100,
    user_id: int = 7,
    message_thread_id: int | None = 222,
) -> Message:
    payload = {
        "message_id": 1,
        "date": int(datetime.now().timestamp()),
        "chat": {"id": chat_id, "type": "supergroup"},
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
    return Message.model_validate(payload).as_(bot or AsyncMock())


def _deps(*, state: str = "bound", alive: bool = True) -> dict[str, object]:
    return {
        "codex_topic_state": AsyncMock(return_value=state),
        "send_topic_recovery_prompt": AsyncMock(),
        "codex_daemon": SimpleNamespace(is_alive=MagicMock(return_value=alive)),
        "codex_reply": AsyncMock(),
        "ensure_global_orch": MagicMock(),
        "execute_codex_prompt": AsyncMock(),
        "codex_topic_bound": "bound",
        "codex_topic_recoverable": "recoverable",
    }


@pytest.mark.asyncio
async def test_handle_topic_message_routes_bound_topic_to_codex() -> None:
    message = _message("continue the work", message_thread_id=222)
    context = SimpleNamespace(session=AsyncMock())
    orchestrator = SimpleNamespace(ensure_transport_handlers=MagicMock())
    deps = _deps(state="bound", alive=True)

    await topic_messages.handle_topic_message(message, context, orchestrator, **deps)

    deps["codex_topic_state"].assert_awaited_once_with(222, context, chat_id=100)
    orchestrator.ensure_transport_handlers.assert_called_once()
    deps["ensure_global_orch"].assert_called_once_with(orchestrator)
    deps["execute_codex_prompt"].assert_awaited_once()
    args = deps["execute_codex_prompt"].await_args.args
    assert args[0] is message
    assert args[1].message_thread_id == 222
    assert args[4] == "continue the work"


@pytest.mark.asyncio
async def test_handle_topic_message_recoverable_topic_sends_prompt() -> None:
    message = _message("continue the work", message_thread_id=222)
    context = SimpleNamespace(session=AsyncMock())
    orchestrator = SimpleNamespace(ensure_transport_handlers=MagicMock())
    deps = _deps(state="recoverable")

    await topic_messages.handle_topic_message(message, context, orchestrator, **deps)

    deps["send_topic_recovery_prompt"].assert_awaited_once()
    orchestrator.ensure_transport_handlers.assert_not_called()
    deps["execute_codex_prompt"].assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_topic_message_skips_unbound_topic() -> None:
    message = _message("normal topic message", message_thread_id=222)
    context = SimpleNamespace(session=AsyncMock())
    orchestrator = SimpleNamespace(ensure_transport_handlers=MagicMock())
    deps = _deps(state="not_codex")

    with pytest.raises(SkipHandler):
        await topic_messages.handle_topic_message(message, context, orchestrator, **deps)

    orchestrator.ensure_transport_handlers.assert_not_called()
    deps["execute_codex_prompt"].assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_topic_message_skips_empty_prompt() -> None:
    message = _message("   ", message_thread_id=222)
    context = SimpleNamespace(session=AsyncMock())
    orchestrator = SimpleNamespace(ensure_transport_handlers=MagicMock())
    deps = _deps()

    with pytest.raises(SkipHandler):
        await topic_messages.handle_topic_message(message, context, orchestrator, **deps)

    deps["codex_topic_state"].assert_not_awaited()
