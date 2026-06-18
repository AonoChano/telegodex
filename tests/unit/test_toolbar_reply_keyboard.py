"""Unit tests for temporary ReplyKeyboard controls."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove

from bot.handlers import toolbar
from core.session import SessionKey
from tests.fake_telegram_client import FakeTelegramClient


class _FakeCodexSessionManager:
    def __init__(self) -> None:
        self.active: set[SessionKey] = set()
        self.cancel_turn = AsyncMock()

    def is_turn_active(self, session_key: SessionKey) -> bool:
        return session_key in self.active


@pytest.fixture(autouse=True)
def _reset_toolbar_state():
    toolbar._keyboard_states.clear()
    toolbar._keyboard_locks.clear()
    toolbar._last_replies.clear()
    toolbar._live_tasks.clear()
    toolbar._live_messages.clear()
    toolbar.set_session_manager(None)
    original_shell_provider = toolbar._shell_provider
    yield
    toolbar._keyboard_states.clear()
    toolbar._keyboard_locks.clear()
    toolbar._last_replies.clear()
    toolbar._live_tasks.clear()
    toolbar._live_messages.clear()
    toolbar.set_session_manager(None)
    toolbar._shell_provider = original_shell_provider


@pytest.mark.asyncio
async def test_send_reply_keyboard_is_idempotent_for_codex_turn() -> None:
    session_key = SessionKey.from_telegram_message(100, 222)
    manager = _FakeCodexSessionManager()
    manager.active.add(session_key)
    toolbar.set_session_manager(manager)
    bot = FakeTelegramClient()

    first = await toolbar.send_reply_keyboard(bot, session_key, message_thread_id=222)
    second = await toolbar.send_reply_keyboard(bot, session_key, message_thread_id=222)

    assert first is not None
    assert second is None
    assert bot.call_count("send_message") == 1
    _, args, kwargs = bot.get_calls("send_message")[0]
    assert args[0] == 100
    assert kwargs["message_thread_id"] == 222
    assert isinstance(kwargs["reply_markup"], ReplyKeyboardMarkup)
    assert "Codex active" in args[1]


@pytest.mark.asyncio
async def test_remove_reply_keyboard_is_idempotent() -> None:
    session_key = SessionKey.from_telegram_message(100, 222)
    manager = _FakeCodexSessionManager()
    manager.active.add(session_key)
    toolbar.set_session_manager(manager)
    bot = FakeTelegramClient()

    await toolbar.send_reply_keyboard(bot, session_key, message_thread_id=222)
    bot.clear()

    await toolbar.remove_reply_keyboard(bot, session_key, message_thread_id=222)
    await toolbar.remove_reply_keyboard(bot, session_key, message_thread_id=222)

    assert bot.call_count("send_message") == 1
    _, _, kwargs = bot.get_calls("send_message")[0]
    assert kwargs["message_thread_id"] == 222
    assert isinstance(kwargs["reply_markup"], ReplyKeyboardRemove)
