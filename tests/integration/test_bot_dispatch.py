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
from bot.handlers import codex_router, messages_router


def _make_mock_message(
    *,
    text: str,
    chat_type: str = "private",
    chat_id: int = 123456,
    user_id: int = 123456,
    message_thread_id: int | None = None,
    entities: list[dict[str, Any]] | None = None,
) -> Message:
    """Build a real aiogram Message with all attributes handlers touch."""
    payload: dict[str, Any] = {
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
    if message_thread_id is not None:
        payload["message_thread_id"] = message_thread_id
        payload["is_topic_message"] = True
    return Message.model_validate(payload)


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
    async def test_start_command_routed(self, dp: Dispatcher, mock_context_manager: AsyncMock) -> None:
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

    @pytest.mark.asyncio
    async def test_start_command_lists_deepseek_provider(
        self,
        dp: Dispatcher,
        mock_context_manager: AsyncMock,
    ) -> None:
        ai_router = MagicMock()
        ai_router.list_available_providers = MagicMock(return_value=["deepseek"])
        ai_router.is_provider_available = MagicMock(return_value=False)

        @dp.message.middleware()
        async def inject_deps(handler, event, data):
            data["context_manager"] = mock_context_manager
            data["ai_router"] = ai_router
            data["orchestrator"] = MagicMock()
            return await handler(event, data)

        bot = AsyncMock()
        message = _make_mock_message(
            text="/start",
            entities=[{"type": "bot_command", "offset": 0, "length": 6}],
        )
        update = _make_update(message)

        await dp.feed_update(bot, update)

        call_arg = bot.await_args[0][0]
        assert "deepseek" in call_arg.text.lower()
        assert "无可用" not in call_arg.text


class TestSettingsCommandRouting:
    """Verify ``/settings`` opens the settings menu."""

    @pytest.mark.asyncio
    async def test_settings_command_routed(self, dp: Dispatcher) -> None:
        bot = AsyncMock()
        message = _make_mock_message(
            text="/settings",
            entities=[{"type": "bot_command", "offset": 0, "length": 9}],
        )
        update = _make_update(message)

        await dp.feed_update(bot, update)

        assert bot.called
        call_arg = bot.await_args[0][0]
        assert call_arg.text == "Settings"
        assert call_arg.reply_markup is not None

    @pytest.mark.asyncio
    async def test_legacy_settings_keyboard_button_opens_settings(
        self,
        dp: Dispatcher,
        mock_context_manager: AsyncMock,
    ) -> None:
        @dp.message.middleware()
        async def inject_deps(handler, event, data):
            data["context_manager"] = mock_context_manager
            data["ai_router"] = MagicMock()
            data["orchestrator"] = MagicMock()
            return await handler(event, data)

        bot = AsyncMock()
        message = _make_mock_message(text="⚙️ 设置")
        update = _make_update(message)

        await dp.feed_update(bot, update)

        assert bot.called
        call_arg = bot.await_args[0][0]
        assert call_arg.text == "Settings"
        assert call_arg.reply_markup is not None


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

        with (
            patch("bot.handlers.messages.settings", mock_settings),
            patch(
                "bot.handlers.messages.send_rich_message",
                AsyncMock(return_value=True),
            ) as mock_send_rich,
        ):
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

    @pytest.mark.asyncio
    async def test_terminal_provider_error_does_not_retry_non_streaming(
        self,
        dp: Dispatcher,
        mock_context_manager: AsyncMock,
    ) -> None:
        class ProviderPaymentError(Exception):
            status_code = 402
            body = {
                "error": {
                    "message": "Insufficient Balance",
                    "type": "unknown_error",
                    "code": "invalid_request_error",
                }
            }

        async def _failing_stream(*args: Any, **kwargs: Any):
            raise ProviderPaymentError("Error code: 402 - {'error': {'message': 'Insufficient Balance'}}")
            yield ""

        provider = MagicMock()
        provider.chat_stream = MagicMock(side_effect=_failing_stream)
        provider.chat = AsyncMock()

        ai_router = MagicMock()
        ai_router.get_provider = MagicMock(return_value=provider)
        ai_router.get_default_provider = MagicMock(return_value=provider)
        ai_router.is_provider_available = MagicMock(return_value=True)

        @dp.message.middleware()
        async def inject_deps(handler, event, data):
            data["context_manager"] = mock_context_manager
            data["ai_router"] = ai_router
            data["orchestrator"] = MagicMock()
            return await handler(event, data)

        bot = AsyncMock()
        message = _make_mock_message(text="测试", chat_type="group")
        update = _make_update(message)

        mock_settings = MagicMock()
        mock_settings.telegram_bot_token = "123:fake"
        mock_settings.max_tokens = 4096

        with patch("bot.handlers.messages.settings", mock_settings):
            await dp.feed_update(bot, update)

        provider.chat_stream.assert_called_once()
        provider.chat.assert_not_awaited()

        call_arg = bot.await_args[0][0]
        assert "AI 服务商请求失败" in call_arg.text
        assert "余额或额度不足" in call_arg.text
        assert "Insufficient Balance" not in call_arg.text


class TestCodexTopicFallthrough:
    """Verify non-Codex topics still reach the normal AI chat handler."""

    @pytest.mark.asyncio
    async def test_bound_forum_topic_routes_to_codex_not_ai(
        self,
        mock_context_manager: AsyncMock,
        mock_ai_provider: MagicMock,
    ) -> None:
        dispatcher = Dispatcher()
        dispatcher.include_router(codex_router)
        dispatcher.include_router(messages_router)

        orchestrator = MagicMock()
        orchestrator.ensure_transport_handlers = MagicMock()

        @dispatcher.message.middleware()
        async def inject_deps(handler, event, data):
            data["context_manager"] = mock_context_manager
            data["ai_router"] = ai_router
            data["orchestrator"] = orchestrator
            return await handler(event, data)

        ai_router = MagicMock()
        ai_router.get_provider = MagicMock(return_value=mock_ai_provider)
        ai_router.get_default_provider = MagicMock(return_value=mock_ai_provider)
        ai_router.is_provider_available = MagicMock(return_value=True)

        class _Scalars:
            def __init__(self, first):
                self._first = first

            def first(self):
                return self._first

        class _DbResult:
            def __init__(self, first):
                self._first = first

            def scalars(self):
                return _Scalars(self._first)

        mock_context_manager.session.execute = AsyncMock(
            return_value=_DbResult(MagicMock(id=17, topic_id=222, is_active=True))
        )

        bot = AsyncMock()
        message = _make_mock_message(
            text="continue in codex topic",
            chat_type="supergroup",
            message_thread_id=222,
        )
        update = _make_update(message)

        with (
            patch("bot.handlers.codex.codex_daemon.is_alive", return_value=True),
            patch("bot.handlers.codex._ensure_global_orch", MagicMock()),
            patch("bot.handlers.codex._execute_codex_prompt", AsyncMock()) as execute,
        ):
            await dispatcher.feed_update(bot, update)

        execute.assert_awaited_once()
        mock_ai_provider.chat_stream.assert_not_called()

        codex_router._parent_router = None
        messages_router._parent_router = None

    @pytest.mark.asyncio
    async def test_unbound_forum_topic_reaches_ai_handler(
        self,
        mock_context_manager: AsyncMock,
        mock_ai_provider: MagicMock,
    ) -> None:
        dispatcher = Dispatcher()
        dispatcher.include_router(codex_router)
        dispatcher.include_router(messages_router)

        @dispatcher.message.middleware()
        async def inject_deps(handler, event, data):
            data["context_manager"] = mock_context_manager
            data["ai_router"] = ai_router
            data["orchestrator"] = MagicMock()
            return await handler(event, data)

        ai_router = MagicMock()
        ai_router.get_provider = MagicMock(return_value=mock_ai_provider)
        ai_router.get_default_provider = MagicMock(return_value=mock_ai_provider)
        ai_router.is_provider_available = MagicMock(return_value=True)

        class _Scalars:
            def first(self):
                return None

        class _DbResult:
            def scalars(self):
                return _Scalars()

        mock_context_manager.session.execute = AsyncMock(return_value=_DbResult())

        bot = AsyncMock()
        message = _make_mock_message(
            text="normal topic message",
            chat_type="supergroup",
            message_thread_id=222,
        )
        update = _make_update(message)

        mock_settings = MagicMock()
        mock_settings.telegram_bot_token = "123:fake"
        mock_settings.max_tokens = 4096

        with (
            patch("bot.handlers.messages.settings", mock_settings),
            patch(
                "bot.handlers.messages.send_rich_message",
                AsyncMock(return_value=True),
            ) as mock_send_rich,
        ):
            await dispatcher.feed_update(bot, update)

        mock_ai_provider.chat_stream.assert_called_once()
        mock_send_rich.assert_awaited_once()
        _, kwargs = mock_send_rich.call_args
        assert kwargs["message_thread_id"] == 222
        assert "Hello world" in kwargs["markdown_text"]

        codex_router._parent_router = None
        messages_router._parent_router = None
