"""Unit tests for help page replacement behavior."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.handlers import help as help_handler


class MessageStub:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(id=100)
        self.message_id = 42
        self.message_thread_id = 222
        self.business_connection_id = "biz-1"
        self.direct_messages_topic = None
        self.model_extra = {}
        self.edit_text = AsyncMock()
        self.delete = AsyncMock()


class BotStub:
    token = "TOKEN"

    def __init__(self) -> None:
        self.send_message = AsyncMock()


def _callback() -> SimpleNamespace:
    return SimpleNamespace(message=MessageStub(), bot=BotStub())


def _keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Next", callback_data="help:toc:2")]
        ]
    )


@pytest.mark.asyncio
async def test_help_replacement_edits_rich_message_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    callback = _callback()
    edit_rich = AsyncMock(return_value=True)
    send_rich = AsyncMock(return_value=True)
    monkeypatch.setattr(help_handler, "edit_rich_message", edit_rich)
    monkeypatch.setattr(help_handler, "send_rich_message", send_rich)

    assert await help_handler._replace_help_message_content(
        callback,
        "## Page 2",
        _keyboard(),
    ) is True

    edit_rich.assert_awaited_once()
    assert edit_rich.await_args.kwargs["chat_id"] == 100
    assert edit_rich.await_args.kwargs["message_id"] == 42
    assert edit_rich.await_args.kwargs["business_connection_id"] == "biz-1"
    send_rich.assert_not_awaited()
    callback.message.edit_text.assert_not_awaited()
    callback.message.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_help_replacement_resends_rich_before_plain_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    callback = _callback()
    edit_rich = AsyncMock(return_value=False)
    send_rich = AsyncMock(return_value=True)
    monkeypatch.setattr(help_handler, "edit_rich_message", edit_rich)
    monkeypatch.setattr(help_handler, "send_rich_message", send_rich)

    assert await help_handler._replace_help_message_content(
        callback,
        "## Page 2",
        _keyboard(),
    ) is True

    edit_rich.assert_awaited_once()
    send_rich.assert_awaited_once()
    assert send_rich.await_args.kwargs["message_thread_id"] == 222
    assert send_rich.await_args.kwargs["business_connection_id"] == "biz-1"
    callback.message.delete.assert_awaited_once()
    callback.message.edit_text.assert_not_awaited()
    callback.bot.send_message.assert_not_awaited()



@pytest.mark.asyncio
async def test_help_replacement_uses_plain_edit_only_after_rich_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    callback = _callback()
    edit_rich = AsyncMock(return_value=False)
    send_rich = AsyncMock(return_value=False)
    monkeypatch.setattr(help_handler, "edit_rich_message", edit_rich)
    monkeypatch.setattr(help_handler, "send_rich_message", send_rich)

    assert await help_handler._replace_help_message_content(
        callback,
        "plain page",
        _keyboard(),
    ) is True

    edit_rich.assert_awaited_once()
    send_rich.assert_awaited_once()
    callback.message.edit_text.assert_awaited_once()
    callback.bot.send_message.assert_not_awaited()
    callback.message.delete.assert_not_awaited()
