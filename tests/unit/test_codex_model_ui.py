"""Unit tests for Telegram model switching helpers."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import Message

from bot.codex import model_ui
from core.session import SessionKey


def _message(
    text: str,
    *,
    bot: AsyncMock | None = None,
    chat_id: int = 100,
    chat_type: str = "supergroup",
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


@pytest.mark.asyncio
async def test_handle_model_command_without_args_shows_available_providers() -> None:
    bot = AsyncMock()
    message = _message("/model", bot=bot)
    orchestrator = SimpleNamespace(providers=SimpleNamespace(list_available=MagicMock(return_value=["deepseek", "zhipu"])))
    context = SimpleNamespace()

    await model_ui.handle_model_command(message, context, orchestrator)

    bot.assert_awaited_once()
    method = bot.await_args.args[0]
    assert "**Usage:** `/model <provider>`" in method.text
    assert "- `deepseek`" in method.text
    assert "- `zhipu`" in method.text
    assert method.parse_mode == "Markdown"


@pytest.mark.asyncio
async def test_handle_model_command_unknown_provider_replies_error() -> None:
    bot = AsyncMock()
    message = _message("/model missing", bot=bot)
    orchestrator = SimpleNamespace(providers=SimpleNamespace(list_available=MagicMock(return_value=["deepseek"])))
    context = SimpleNamespace()

    await model_ui.handle_model_command(message, context, orchestrator)

    bot.assert_awaited_once()
    method = bot.await_args.args[0]
    assert "Unknown provider" in method.text
    assert "`missing`" in method.text
    assert method.parse_mode == "Markdown"


@pytest.mark.asyncio
async def test_handle_model_command_switches_provider_and_saves_session_data() -> None:
    bot = AsyncMock()
    message = _message("/model Zhipu", bot=bot, message_thread_id=222)
    user = SimpleNamespace(preferred_provider="deepseek")
    conversation = SimpleNamespace(id=42)
    provider_conv = SimpleNamespace(id=77)
    old_bucket = SimpleNamespace(session_id=None)
    session_data = SimpleNamespace(get_or_create_bucket=MagicMock(return_value=old_bucket))
    context = SimpleNamespace(
        get_or_create_user=AsyncMock(return_value=user),
        get_or_create_conversation=AsyncMock(return_value=conversation),
        session=SimpleNamespace(commit=AsyncMock()),
    )
    orchestrator = SimpleNamespace(providers=SimpleNamespace(list_available=MagicMock(return_value=["deepseek", "zhipu"])))
    load_session_data = AsyncMock(return_value=session_data)
    resolve_provider_conversation = AsyncMock(return_value=provider_conv)
    save_session_data = AsyncMock()
    active_session_manager = SimpleNamespace(set_active_provider=MagicMock())

    await model_ui.handle_model_command(
        message,
        context,
        orchestrator,
        load_session_data=load_session_data,
        resolve_provider_conversation=resolve_provider_conversation,
        save_session_data=save_session_data,
        active_session_manager=active_session_manager,
    )

    session_key = SessionKey.from_telegram_message(100, 222)
    context.get_or_create_user.assert_awaited_once_with(7)
    context.get_or_create_conversation.assert_awaited_once_with(7, thread_id=222, chat_id=100)
    load_session_data.assert_awaited_once_with(conversation, session_key)
    session_data.get_or_create_bucket.assert_called_once_with("deepseek")
    assert old_bucket.session_id == "42"
    assert user.preferred_provider == "zhipu"
    active_session_manager.set_active_provider.assert_called_once_with(session_key, "zhipu")
    resolve_provider_conversation.assert_awaited_once_with(context, session_key, session_data, 7, 222, "zhipu")
    save_session_data.assert_awaited_once_with(provider_conv, session_key)
    context.session.commit.assert_awaited_once()
    bot.assert_awaited_once()
    method = bot.await_args.args[0]
    assert "Switched to `zhipu`" in method.text
    assert method.parse_mode == "MarkdownV2"
