"""Unit tests for Codex topic recovery prompt state."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.types import Message

from bot.codex.topic_recovery import TopicRecoveryPrompt, TopicRecoveryRequest, TopicRecoveryStore
from bot.utils.routing import TelegramRoute


def _message(
    text: str = "continue",
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


def test_key_for_route_requires_topic_id() -> None:
    store = TopicRecoveryStore()

    assert store.key_for_route(TelegramRoute(chat_id=100, message_thread_id=222)) == (100, 222)
    assert store.key_for_route(TelegramRoute(chat_id=100)) is None


def test_pop_request_removes_pending_request() -> None:
    store = TopicRecoveryStore()
    store.requests["request-1"] = TopicRecoveryRequest(
        chat_id=100,
        topic_id=222,
        prompt="continue",
        user_id=7,
    )

    request = store.pop_request("request-1")

    assert request is not None
    assert request.prompt == "continue"
    assert store.requests == {}


@pytest.mark.asyncio
async def test_send_prompt_replaces_previous_prompt_for_topic() -> None:
    bot = AsyncMock()
    bot.send_message.return_value = SimpleNamespace(message_id=100)
    store = TopicRecoveryStore()
    route = TelegramRoute(chat_id=100, message_thread_id=222)
    old_request_id = "old-request"
    store.requests[old_request_id] = TopicRecoveryRequest(
        chat_id=100,
        topic_id=222,
        prompt="old",
        user_id=7,
    )
    store.prompts[(100, 222)] = TopicRecoveryPrompt(
        request_id=old_request_id,
        message_id=99,
    )

    await store.send_prompt(
        _message("new prompt", bot=bot, message_thread_id=222),
        route,
        "new prompt",
    )

    bot.delete_message.assert_awaited_once_with(chat_id=100, message_id=99)
    bot.send_message.assert_awaited_once()
    _, kwargs = bot.send_message.await_args
    assert kwargs["chat_id"] == 100
    assert kwargs["message_thread_id"] == 222
    assert "Create a new Codex session" in kwargs["text"]
    assert old_request_id not in store.requests
    assert len(store.requests) == 1
    request = next(iter(store.requests.values()))
    assert request.prompt == "new prompt"
    assert store.prompts[(100, 222)].message_id == 100


@pytest.mark.asyncio
async def test_send_prompt_skips_when_message_has_no_topic() -> None:
    bot = AsyncMock()
    store = TopicRecoveryStore()

    await store.send_prompt(
        _message("new prompt", bot=bot, message_thread_id=None),
        TelegramRoute(chat_id=100),
        "new prompt",
    )

    bot.send_message.assert_not_awaited()
    assert store.requests == {}
    assert store.prompts == {}
