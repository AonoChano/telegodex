"""Unit tests for Codex screenshot command handling."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from aiogram.types import Message

from bot.codex import screenshot_ui


def _message(
    text: str = "/screenshot",
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


@pytest.mark.asyncio
async def test_handle_screenshot_command_preserves_topic_route(monkeypatch: pytest.MonkeyPatch) -> None:
    message = _message(message_thread_id=222)
    send_screenshot_to_chat = AsyncMock()
    monkeypatch.setattr(screenshot_ui, "send_screenshot_to_chat", send_screenshot_to_chat)

    await screenshot_ui.handle_screenshot_command(message)

    send_screenshot_to_chat.assert_awaited_once()
    args = send_screenshot_to_chat.await_args.args
    assert args[0] is message
    assert args[1].chat_id == 100
    assert args[1].message_thread_id == 222
