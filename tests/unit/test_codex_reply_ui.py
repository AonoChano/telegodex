"""Unit tests for Codex reply helpers."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from aiogram.types import Message

from bot.codex import reply_ui
from bot.utils.routing import TelegramRoute


def _message(text: str, *, bot: AsyncMock | None = None) -> Message:
    message = Message.model_validate(
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
    return message.as_(bot or AsyncMock())


def test_codex_send_kwargs_uses_route_kwargs_when_no_override() -> None:
    route = TelegramRoute(chat_id=100, message_thread_id=222)

    assert reply_ui.codex_send_kwargs(route, None) == route.send_kwargs()


def test_codex_send_kwargs_overrides_topic_id_when_provided() -> None:
    route = TelegramRoute(chat_id=100, message_thread_id=111)

    assert reply_ui.codex_send_kwargs(route, 222) == {"message_thread_id": 222}


@pytest.mark.asyncio
async def test_codex_reply_sends_shortened_text_to_requested_topic() -> None:
    bot = AsyncMock()
    message = _message("prompt", bot=bot)
    route = TelegramRoute(chat_id=100, message_thread_id=111)
    long_text = "x" * 5000

    await reply_ui.codex_reply(message, long_text, route, 222, parse_mode="Markdown")

    bot.send_message.assert_awaited_once()
    _, kwargs = bot.send_message.await_args
    assert kwargs["chat_id"] == 100
    assert kwargs["message_thread_id"] == 222
    assert kwargs["parse_mode"] == "Markdown"
    assert len(kwargs["text"]) < len(long_text)
    assert kwargs["text"] != long_text
