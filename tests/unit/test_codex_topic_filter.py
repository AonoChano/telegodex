"""Unit tests for Codex Telegram topic filters."""

from __future__ import annotations

from datetime import datetime

import pytest
from aiogram.types import Message

from bot.codex.topic_filter import IsCodexBoundTopic


def _message(text: str | None, *, message_thread_id: int | None = None) -> Message:
    payload = {
        "message_id": 1,
        "date": int(datetime.now().timestamp()),
        "chat": {"id": 100, "type": "supergroup"},
        "from": {
            "id": 7,
            "is_bot": False,
            "first_name": "Test",
        },
    }
    if text is not None:
        payload["text"] = text
    if message_thread_id is not None:
        payload["message_thread_id"] = message_thread_id
        payload["is_topic_message"] = True
    return Message.model_validate(payload)


@pytest.mark.asyncio
async def test_codex_bound_topic_filter_accepts_plain_topic_text() -> None:
    assert await IsCodexBoundTopic()(_message("continue", message_thread_id=222)) is True


@pytest.mark.asyncio
async def test_codex_bound_topic_filter_rejects_main_chat_text() -> None:
    assert await IsCodexBoundTopic()(_message("continue")) is False


@pytest.mark.asyncio
async def test_codex_bound_topic_filter_rejects_missing_text() -> None:
    assert await IsCodexBoundTopic()(_message(None, message_thread_id=222)) is False


@pytest.mark.asyncio
async def test_codex_bound_topic_filter_rejects_explicit_codex_commands() -> None:
    assert await IsCodexBoundTopic()(_message("/codex status", message_thread_id=222)) is False
