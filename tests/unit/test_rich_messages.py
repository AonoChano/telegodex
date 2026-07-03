"""Unit tests for Telegram Rich Message helpers."""

from __future__ import annotations

from typing import Any

import pytest
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.utils import rich_messages


def test_build_edit_rich_markdown_payload_serializes_keyboard() -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Next", callback_data="help:toc:2")]
        ]
    )

    payload = rich_messages.build_edit_rich_markdown_payload(
        100,
        42,
        "## Page 2",
        business_connection_id="biz-1",
        reply_markup=keyboard,
    )

    assert payload == {
        "chat_id": 100,
        "message_id": 42,
        "rich_message": {"markdown": "## Page 2"},
        "business_connection_id": "biz-1",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "Next", "callback_data": "help:toc:2"}]
            ]
        },
    }


@pytest.mark.asyncio
async def test_edit_rich_message_posts_edit_message_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    async def fake_post(
        _token: str,
        method: str,
        payload: dict[str, Any],
    ) -> tuple[bool, str, Any]:
        calls.append((method, payload))
        return True, "", {"message_id": 42}

    monkeypatch.setattr(rich_messages, "_post_bot_method", fake_post)

    assert await rich_messages.edit_rich_message(
        "TOKEN",
        100,
        42,
        "content",
    ) is True

    assert calls == [
        (
            "editMessageText",
            {
                "chat_id": 100,
                "message_id": 42,
                "rich_message": {"markdown": "content"},
            },
        )
    ]