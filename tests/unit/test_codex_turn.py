"""Unit tests for per-turn Codex Telegram state."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.types import InlineKeyboardMarkup, Message

from bot.codex.turn import CodexTurnActor
from bot.utils.routing import TelegramRoute
from core.session import SessionKey


def _message(
    text: str = "status",
    *,
    bot: AsyncMock | None = None,
    chat_id: int = 100,
    message_id: int = 44,
) -> Message:
    payload = {
        "message_id": message_id,
        "date": int(datetime.now().timestamp()),
        "chat": {"id": chat_id, "type": "private"},
        "from": {
            "id": 7,
            "is_bot": False,
            "first_name": "Test",
        },
        "text": text,
    }
    return Message.model_validate(payload).as_(bot or AsyncMock())


class _Clock:
    def __init__(self, value: float = 0.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


def _actor(
    *,
    bot: AsyncMock | None = None,
    clock: _Clock | None = None,
    stop_msg: Message | None = None,
    stream: AsyncMock | None = None,
) -> CodexTurnActor:
    bot = bot or AsyncMock()
    clock = clock or _Clock()
    stop_msg = stop_msg if stop_msg is not None else _message(bot=bot)
    return CodexTurnActor(
        bot=bot,
        route=TelegramRoute(chat_id=100),
        session_key=SessionKey.from_telegram_message(100, None),
        orchestrator=SimpleNamespace(session_manager=None),
        stop_msg=stop_msg,
        stop_keyboard=InlineKeyboardMarkup(inline_keyboard=[]),
        stream=stream,
        reaction_tracker=None,
        clock=clock,
    )


@pytest.mark.asyncio
async def test_edit_status_skips_duplicate_text() -> None:
    bot = AsyncMock()
    actor = _actor(bot=bot)

    await actor.edit_status("Codex is working...")

    bot.edit_message_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_edit_status_throttles_non_forced_updates() -> None:
    bot = AsyncMock()
    clock = _Clock(1.0)
    actor = _actor(bot=bot, clock=clock)

    await actor.edit_status("First update")

    bot.edit_message_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_edit_status_allows_update_after_interval() -> None:
    bot = AsyncMock()
    clock = _Clock(3.0)
    actor = _actor(bot=bot, clock=clock)

    await actor.edit_status("First update")

    bot.edit_message_text.assert_awaited_once()
    _, kwargs = bot.edit_message_text.await_args
    assert kwargs["text"] == "First update"
    assert actor.last_status_text == "First update"
    assert actor.last_status_edit == 3.0


@pytest.mark.asyncio
async def test_edit_status_force_bypasses_throttle() -> None:
    bot = AsyncMock()
    clock = _Clock(0.1)
    actor = _actor(bot=bot, clock=clock)

    await actor.edit_status("Forced update", force=True, parse_mode="HTML")

    bot.edit_message_text.assert_awaited_once()
    _, kwargs = bot.edit_message_text.await_args
    assert kwargs["text"] == "Forced update"
    assert kwargs["parse_mode"] == "HTML"


@pytest.mark.asyncio
async def test_push_render_update_throttles_small_draft_changes() -> None:
    clock = _Clock(1.0)
    stream = AsyncMock()
    stream.push.return_value = True
    actor = _actor(clock=clock, stream=stream)

    await actor.push_render_update("hello")
    await actor.push_render_update("hello!")

    assert stream.push.await_count == 1


@pytest.mark.asyncio
async def test_push_render_update_flushes_after_interval() -> None:
    clock = _Clock(1.0)
    stream = AsyncMock()
    stream.push.return_value = True
    actor = _actor(clock=clock, stream=stream)

    await actor.push_render_update("hello")
    clock.value = 3.0
    await actor.push_render_update("hello!")

    assert stream.push.await_count == 2
