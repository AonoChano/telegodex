"""Unit tests for Codex turn final output lifecycle."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.types import Message

from bot.codex import turn_lifecycle
from bot.utils.routing import TelegramRoute
from core.session import SessionKey


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
    return Message.model_validate(payload).as_(bot or AsyncMock())


def _stop_message(chat_id: int = 100, message_id: int = 44) -> SimpleNamespace:
    return SimpleNamespace(chat=SimpleNamespace(id=chat_id), message_id=message_id)


@pytest.mark.asyncio
async def test_persist_final_output_uses_stream_and_deletes_status() -> None:
    bot = AsyncMock()
    message = _message(bot=bot)
    route = TelegramRoute.from_message(message)
    stream = SimpleNamespace(finalize=AsyncMock(return_value=True))
    codex_reply = AsyncMock()
    send_rich_message = AsyncMock()
    stop_msg = _stop_message()

    remaining = await turn_lifecycle.persist_final_output(
        bot=bot,
        bot_token="TOKEN",
        message=message,
        route=route,
        topic_id=None,
        final_text="final",
        stream=stream,
        stop_msg=stop_msg,
        codex_reply=codex_reply,
        send_rich_message_func=send_rich_message,
    )

    assert remaining is None
    stream.finalize.assert_awaited_once_with("final")
    send_rich_message.assert_not_awaited()
    codex_reply.assert_not_awaited()
    bot.delete_message.assert_awaited_once_with(chat_id=100, message_id=44)


@pytest.mark.asyncio
async def test_persist_final_output_uses_rich_message_without_stream() -> None:
    bot = AsyncMock()
    message = _message(bot=bot, message_thread_id=222)
    route = TelegramRoute.from_message(message)
    send_rich_message = AsyncMock(return_value=True)
    stop_msg = _stop_message()

    remaining = await turn_lifecycle.persist_final_output(
        bot=bot,
        bot_token="TOKEN",
        message=message,
        route=route,
        topic_id=222,
        final_text="final",
        stream=None,
        stop_msg=stop_msg,
        codex_reply=AsyncMock(),
        send_rich_message_func=send_rich_message,
    )

    assert remaining is None
    send_rich_message.assert_awaited_once_with(
        bot_token="TOKEN",
        chat_id=100,
        markdown_text="final",
        message_thread_id=222,
        direct_messages_topic_id=None,
        business_connection_id=None,
    )
    bot.delete_message.assert_awaited_once_with(chat_id=100, message_id=44)


@pytest.mark.asyncio
async def test_persist_final_output_falls_back_when_persist_fails() -> None:
    bot = AsyncMock()
    message = _message(bot=bot)
    route = TelegramRoute.from_message(message)
    codex_reply = AsyncMock()
    send_rich_message = AsyncMock(return_value=False)
    stop_msg = _stop_message()

    remaining = await turn_lifecycle.persist_final_output(
        bot=bot,
        bot_token="TOKEN",
        message=message,
        route=route,
        topic_id=None,
        final_text="final",
        stream=None,
        stop_msg=stop_msg,
        codex_reply=codex_reply,
        send_rich_message_func=send_rich_message,
    )

    assert remaining is stop_msg
    codex_reply.assert_awaited_once_with(message, "final", route, None)
    bot.delete_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_persist_final_output_keeps_status_when_delete_fails() -> None:
    bot = AsyncMock()
    bot.delete_message.side_effect = RuntimeError("delete failed")
    message = _message(bot=bot)
    route = TelegramRoute.from_message(message)
    stop_msg = _stop_message()

    remaining = await turn_lifecycle.persist_final_output(
        bot=bot,
        bot_token="TOKEN",
        message=message,
        route=route,
        topic_id=None,
        final_text="final",
        stream=SimpleNamespace(finalize=AsyncMock(return_value=True)),
        stop_msg=stop_msg,
        codex_reply=AsyncMock(),
        send_rich_message_func=AsyncMock(),
    )

    assert remaining is stop_msg
    bot.delete_message.assert_awaited_once_with(chat_id=100, message_id=44)

@pytest.mark.asyncio
async def test_cleanup_turn_deletes_status_and_removes_keyboard() -> None:
    bot = AsyncMock()
    toolbar = SimpleNamespace(remove_reply_keyboard=AsyncMock())
    session_key = SessionKey("telegram", 100, 222)

    await turn_lifecycle.cleanup_turn(
        bot=bot,
        toolbar_handler=toolbar,
        session_key=session_key,
        topic_id=222,
        stop_msg=_stop_message(),
    )

    bot.delete_message.assert_awaited_once_with(chat_id=100, message_id=44)
    toolbar.remove_reply_keyboard.assert_awaited_once_with(
        bot,
        session_key,
        message_thread_id=222,
    )


@pytest.mark.asyncio
async def test_cleanup_turn_tolerates_cleanup_failures() -> None:
    bot = AsyncMock()
    bot.delete_message.side_effect = RuntimeError("delete failed")
    toolbar = SimpleNamespace(remove_reply_keyboard=AsyncMock(side_effect=RuntimeError("keyboard failed")))
    session_key = SessionKey("telegram", 100)

    await turn_lifecycle.cleanup_turn(
        bot=bot,
        toolbar_handler=toolbar,
        session_key=session_key,
        topic_id=None,
        stop_msg=_stop_message(),
    )

    bot.delete_message.assert_awaited_once_with(chat_id=100, message_id=44)
    toolbar.remove_reply_keyboard.assert_awaited_once_with(
        bot,
        session_key,
        message_thread_id=None,
    )
