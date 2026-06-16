"""Integration tests for aiogram dispatcher message routing.

Patches the dispatcher and feeds mocked updates to verify handlers are reached
without calling real Telegram or AI APIs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram import Dispatcher
from aiogram.types import Message, Update

from ai.base import MessageRole
from bot.handlers import messages_router


def _make_mock_message(
    *,
    text: str,
    chat_type: str = "private",
    chat_id: int = 123456,
    user_id: int = 123456,
    entities: list[dict[str, Any]] | None = None,
) -> Message:
    """Build a real aiogram Message with all attributes handlers touch."""
    return Message.model_validate(
        {
            "message_id": 1,
            "date": int(datetime.now().timestamp()),
            "chat": {"id": chat_id, "type": chat_type},
            "from": {
                "id": user_id,
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser",
            },
            "text": text,
            "entities": entities or [],
        }
    )


def _make_update(message: Message) -> Update:
    """Build a real aiogram Update that the dispatcher will route as ``message``."""
    return Update(update_id=1, message=message)


@pytest.fixture
def dp():
    """Provide a Dispatcher with ``messages_router`` attached.

    The router is detached after the test so it can be re-attached cleanly.
    """
    dispatcher = Dispatcher()
    dispatcher.include_router(messages_router)
    yield dispatcher
    messages_router._parent_router = None


class TestHelpCommandRouting:
    """Verify ``/help`` reaches ``cmd_help`` through the dispatcher."""

    @pytest.mark.asyncio
    async def test_help_command_routed(self, dp: Dispatcher) -> None:
        bot = AsyncMock()
        message = _make_mock_message(
            text="/help",
            entities=[{"type": "bot_command", "offset": 0, "length": 5}],
        )
        update = _make_update(message)

        await dp.feed_update(bot, update)

        assert bot.called
        call_arg = bot.await_args[0][0]
        assert "帮助文档" in call_arg.text


class TestStartCommandRouting:
    """Verify ``/start`` reaches ``cmd_start`` with injected mocks."""

    @pytest.mark.asyncio
    async def test_start_command_routed(
        self, dp: Dispatcher, mock_context_manager: AsyncMock
    ) -> None:
        @dp.message.middleware()
        async def inject_deps(handler, event, data):
            data["context_manager"] = mock_context_manager
            data["ai_router"] = MagicMock()
            data["orchestrator"] = MagicMock()
            return await handler(event, data)

        bot = AsyncMock()
        message = _make_mock_message(
            text="/start",
            entities=[{"type": "bot_command", "offset": 0, "length": 6}],
        )
        update = _make_update(message)

        await dp.feed_update(bot, update)

        assert bot.called
        call_arg = bot.await_args[0][0]
        assert "Telegodex" in call_arg.text
        mock_context_manager.get_or_create_user.assert_awaited_once()


class TestTextMessageRouting:
    """Verify plain text reaches ``handle_message`` and produces a bot reply."""

    @pytest.mark.asyncio
    async def test_text_message_routed_with_ai_response(
        self,
        dp: Dispatcher,
        mock_context_manager: AsyncMock,
        mock_ai_provider: MagicMock,
    ) -> None:
        ai_router = MagicMock()
        ai_router.get_provider = MagicMock(return_value=mock_ai_provider)
        ai_router.get_default_provider = MagicMock(return_value=mock_ai_provider)
        ai_router.is_provider_available = MagicMock(return_value=True)

        @dp.message.middleware()
        async def inject_deps(handler, event, data):
            data["context_manager"] = mock_context_manager
            data["ai_router"] = ai_router
            data["orchestrator"] = MagicMock()
            return await handler(event, data)

        # Use group chat to skip draft-streaming complexity
        bot = AsyncMock()
        message = _make_mock_message(text="Hello bot", chat_type="group")
        update = _make_update(message)

        mock_settings = MagicMock()
        mock_settings.telegram_bot_token = "123:fake"
        mock_settings.max_tokens = 4096

        with patch("bot.handlers.messages.settings", mock_settings):
            with patch(
                "bot.handlers.messages.send_rich_message",
                AsyncMock(return_value=True),
            ) as mock_send_rich:
                await dp.feed_update(bot, update)

        # AI provider stream was invoked
        mock_ai_provider.chat_stream.assert_called_once()

        # User message + assistant response persisted
        calls = mock_context_manager.add_message.await_args_list
        assert len(calls) == 2
        assert calls[0].kwargs["role"] == MessageRole.USER
        assert calls[1].kwargs["role"] == MessageRole.ASSISTANT
        assert "Hello world" in calls[1].kwargs["content"]

        # Rich message was sent
        mock_send_rich.assert_awaited_once()
        _, kwargs = mock_send_rich.call_args
        assert "Hello world" in kwargs["markdown_text"]
