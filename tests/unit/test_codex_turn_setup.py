"""Unit tests for Codex Telegram turn setup."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.types import Message
from loguru import logger

from bot.codex import turn_setup
from bot.utils.routing import TelegramRoute


def _message(
    text: str = "prompt",
    *,
    bot: AsyncMock | None = None,
    chat_id: int = 100,
    chat_type: str = "private",
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


class _FakeDraftStream:
    instances: list[_FakeDraftStream] = []

    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs
        self.__class__.instances.append(self)

    async def push(self, text: str) -> bool:
        return True

    async def finalize(self, text: str) -> bool:
        return True


class _FakeReactionTracker:
    instances: list[_FakeReactionTracker] = []

    def __init__(self, bot, chat_id: int, message_id: int) -> None:
        self.bot = bot
        self.chat_id = chat_id
        self.message_id = message_id
        self.states: list[str] = []
        self.__class__.instances.append(self)

    async def set_state(self, state: str) -> None:
        self.states.append(state)


@pytest.fixture(autouse=True)
def _reset_fakes() -> None:
    _FakeDraftStream.instances.clear()
    _FakeReactionTracker.instances.clear()


@pytest.mark.asyncio
async def test_prepare_codex_turn_creates_private_chat_draft_and_status(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = AsyncMock()
    bot.send_message.return_value = SimpleNamespace(chat=SimpleNamespace(id=100), message_id=44)
    message = _message(bot=bot, chat_type="private")
    route = TelegramRoute.from_message(message)
    toolbar = SimpleNamespace(send_reply_keyboard=AsyncMock())
    monkeypatch.setattr(turn_setup, "DraftStream", _FakeDraftStream)
    monkeypatch.setattr(turn_setup, "ReactionTracker", _FakeReactionTracker)

    prepared = await turn_setup.prepare_codex_turn(
        message=message,
        route=route,
        orchestrator=SimpleNamespace(session_manager=None),
        bot_token="TOKEN",
        toolbar_handler=toolbar,
        status_edit_interval=2.0,
        draft_flush_chars=200,
        draft_flush_interval=1.2,
        stderr_late_grace=2.0,
        stderr_flush_grace=0.25,
    )

    assert prepared is not None
    assert prepared.session_key.topic_id is None
    assert prepared.topic_id is None
    assert prepared.stop_msg is bot.send_message.return_value
    assert prepared.actor.stream is prepared.stream
    assert len(_FakeDraftStream.instances) == 1
    assert _FakeDraftStream.instances[0].kwargs == {
        "bot_token": "TOKEN",
        "chat_id": 100,
        "message_thread_id": None,
        "direct_messages_topic_id": None,
        "business_connection_id": None,
        "use_rich": True,
    }
    bot.send_chat_action.assert_awaited_once_with(
        chat_id=100,
        action="typing",
        message_thread_id=None,
        business_connection_id=None,
    )
    bot.send_message.assert_awaited_once()
    _, send_kwargs = bot.send_message.await_args
    assert send_kwargs["chat_id"] == 100
    assert send_kwargs["text"] == "Codex is working..."
    assert send_kwargs["message_thread_id"] is None
    assert send_kwargs["reply_markup"].inline_keyboard[0][0].text == "Stop generating"
    assert send_kwargs["reply_markup"].inline_keyboard[0][0].callback_data.startswith("codex_stop|")
    toolbar.send_reply_keyboard.assert_awaited_once_with(
        bot,
        session_key=prepared.session_key,
        message_thread_id=None,
    )
    assert _FakeReactionTracker.instances[0].states == ["thinking"]


@pytest.mark.asyncio
async def test_prepare_codex_turn_skips_draft_for_plain_group(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = AsyncMock()
    bot.send_message.return_value = SimpleNamespace(chat=SimpleNamespace(id=100), message_id=44)
    message = _message(bot=bot, chat_type="supergroup", message_thread_id=None)
    route = TelegramRoute.from_message(message)
    monkeypatch.setattr(turn_setup, "DraftStream", _FakeDraftStream)
    monkeypatch.setattr(turn_setup, "ReactionTracker", _FakeReactionTracker)

    prepared = await turn_setup.prepare_codex_turn(
        message=message,
        route=route,
        orchestrator=SimpleNamespace(session_manager=None),
        bot_token="TOKEN",
        toolbar_handler=SimpleNamespace(send_reply_keyboard=AsyncMock()),
        status_edit_interval=2.0,
        draft_flush_chars=200,
        draft_flush_interval=1.2,
        stderr_late_grace=2.0,
        stderr_flush_grace=0.25,
    )

    assert prepared is not None
    assert prepared.stream is None
    assert _FakeDraftStream.instances == []


@pytest.mark.asyncio
async def test_prepare_codex_turn_returns_none_without_bot() -> None:
    message = _message(bot=None)
    message = Message.model_validate(message.model_dump())
    route = TelegramRoute.from_message(message)
    log_messages: list[str] = []
    sink_id = logger.add(log_messages.append, format="{message}")

    try:
        prepared = await turn_setup.prepare_codex_turn(
            message=message,
            route=route,
            orchestrator=SimpleNamespace(session_manager=None),
            bot_token="TOKEN",
            toolbar_handler=SimpleNamespace(send_reply_keyboard=AsyncMock()),
            status_edit_interval=2.0,
            draft_flush_chars=200,
            draft_flush_interval=1.2,
            stderr_late_grace=2.0,
            stderr_flush_grace=0.25,
        )
    finally:
        logger.remove(sink_id)

    assert prepared is None
    log_text = "\n".join(log_messages)
    assert "prepare_codex_turn: bot is None" in log_text
    assert "_execute_codex_prompt: bot is None" not in log_text
