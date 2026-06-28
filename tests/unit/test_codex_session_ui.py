"""Unit tests for Codex session topic UI helpers."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.types import Message

from bot.codex import session_ui
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


class _SessionManager:
    def __init__(self) -> None:
        self.set_topic_id_calls: list[tuple[str, int | None]] = []
        self.update_session_key_calls: list[tuple[SessionKey, SessionKey]] = []

    def set_topic_id(self, thread_id: str, topic_id: int | None) -> None:
        self.set_topic_id_calls.append((thread_id, topic_id))

    def update_session_key(self, old_key: SessionKey, new_key: SessionKey) -> bool:
        self.update_session_key_calls.append((old_key, new_key))
        return True


@pytest.mark.asyncio
async def test_handle_codex_new_creates_topic_and_rebinds_session() -> None:
    bot = AsyncMock()
    bot.create_forum_topic.return_value = SimpleNamespace(message_thread_id=222)
    message = _message("/codex new", bot=bot)
    route = TelegramRoute.from_message(message)
    context = SimpleNamespace(session=AsyncMock())
    session_manager = _SessionManager()
    orchestrator = SimpleNamespace(
        session_manager=session_manager,
        codex_new_session=AsyncMock(return_value={"thread_id": "thread-abcdef", "cwd": "C:/repo"}),
    )
    session_key = SessionKey.from_telegram_message(route.chat_id, None)
    bind = AsyncMock()

    await session_ui.handle_codex_new(
        message,
        route,
        context,
        orchestrator,
        session_key,
        user_id=7,
        bind_codex_thread_to_topic=bind,
    )

    orchestrator.codex_new_session.assert_awaited_once_with(session_key, context.session, 7)
    bot.create_forum_topic.assert_awaited_once_with(chat_id=100, name="Codex: thread-a")
    bot.send_message.assert_awaited_once()
    _, welcome_kwargs = bot.send_message.await_args
    assert welcome_kwargs["chat_id"] == 100
    assert welcome_kwargs["message_thread_id"] == 222
    assert "thread-abcdef" in welcome_kwargs["text"]
    assert session_manager.set_topic_id_calls == [("thread-abcdef", 222)]
    assert session_manager.update_session_key_calls == [
        (
            SessionKey.from_telegram_message(100, None),
            SessionKey.from_telegram_message(100, 222),
        )
    ]
    bind.assert_awaited_once_with(
        context_manager=context,
        chat_id=100,
        topic_id=222,
        thread_id="thread-abcdef",
        user_id=7,
        cwd="C:/repo",
    )

    method = bot.await_args.args[0]
    assert method.__class__.__name__ == "SendMessage"
    assert "Codex: thread-a" in method.text

