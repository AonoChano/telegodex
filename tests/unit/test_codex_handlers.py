"""Unit tests for Telegram-facing Codex handlers."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import Message

from bot.handlers import codex
from bot.utils.routing import TelegramRoute
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


class _Context:
    def __init__(self, state: str = "not_codex", *, bound: bool | None = None) -> None:
        if bound is not None:
            state = "bound" if bound else "not_codex"
        self.session = AsyncMock()
        active = SimpleNamespace(id=1, topic_id=222) if state == "bound" else None
        historical = SimpleNamespace(id=2, topic_id=222) if state == "recoverable" else None
        self.session.execute = AsyncMock(side_effect=[_DbResult(active), _DbResult(historical)])
        self.session.commit = AsyncMock()


class _SessionManager:
    def __init__(self) -> None:
        self.set_topic_id_calls: list[tuple[str, int | None]] = []
        self.update_session_key_calls: list[tuple[SessionKey, SessionKey]] = []

    def set_topic_id(self, thread_id: str, topic_id: int | None) -> None:
        self.set_topic_id_calls.append((thread_id, topic_id))

    def update_session_key(self, old_key: SessionKey, new_key: SessionKey) -> bool:
        self.update_session_key_calls.append((old_key, new_key))
        return True


@pytest.mark.asyncio
async def test_codex_bound_topic_filter_checks_database_binding() -> None:
    message = _message("hello", message_thread_id=222)
    filter_ = codex.IsCodexBoundTopic()

    assert await filter_(message, _Context(state="not_codex")) is False
    assert await filter_(message, _Context(state="recoverable")) is True
    assert await filter_(message, _Context(bound=True)) is True


@pytest.mark.asyncio
async def test_codex_bound_topic_filter_skips_codex_commands() -> None:
    message = _message("/codex status", message_thread_id=222)

    assert await codex.IsCodexBoundTopic()(message, _Context(bound=True)) is False


@pytest.mark.asyncio
async def test_handle_codex_new_creates_topic_and_rebinds_session(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = AsyncMock()
    bot.create_forum_topic.return_value = SimpleNamespace(message_thread_id=222)
    message = _message("/codex new", bot=bot)
    route = TelegramRoute.from_message(message)
    context = _Context(bound=False)
    session_manager = _SessionManager()
    orchestrator = SimpleNamespace(
        session_manager=session_manager,
        codex_new_session=AsyncMock(return_value={"thread_id": "thread-abcdef", "cwd": "C:/repo"}),
    )
    session_key = SessionKey.from_telegram_message(route.chat_id, None)

    await codex._handle_codex_new(
        message,
        route,
        context,
        orchestrator,
        session_key,
        user_id=7,
    )

    orchestrator.codex_new_session.assert_awaited_once_with(session_key, context.session, 7)
    bot.create_forum_topic.assert_awaited_once_with(chat_id=100, name="Codex: thread-a")
    bot.send_message.assert_awaited_once()
    _, welcome_kwargs = bot.send_message.await_args
    assert welcome_kwargs["chat_id"] == 100
    assert welcome_kwargs["message_thread_id"] == 222
    assert "thread-abcdef" in welcome_kwargs["text"]
    assert session_manager.set_topic_id_calls == [("thread-abcdef", 222)]
    assert session_manager.update_session_key_calls == [
        (
            SessionKey.from_telegram_message(100, None),
            SessionKey.from_telegram_message(100, 222),
        )
    ]
    context.session.execute.assert_awaited_once()
    assert context.session.commit.await_count == 1

    method = bot.await_args.args[0]
    assert method.__class__.__name__ == "SendMessage"
    assert "Codex: thread-a" in method.text


@pytest.mark.asyncio
async def test_topic_message_routes_directly_to_codex(monkeypatch: pytest.MonkeyPatch) -> None:
    message = _message("continue the work", message_thread_id=222)
    context = _Context(bound=True)
    orchestrator = SimpleNamespace(ensure_transport_handlers=MagicMock())
    execute = AsyncMock()
    monkeypatch.setattr(codex.codex_daemon, "is_alive", lambda: True)
    monkeypatch.setattr(codex, "_execute_codex_prompt", execute)
    monkeypatch.setattr(codex, "_ensure_global_orch", lambda orch: None)

    await codex.handle_codex_topic_message(message, context, orchestrator)

    orchestrator.ensure_transport_handlers.assert_called_once()
    execute.assert_awaited_once()
    args = execute.await_args.args
    assert args[0] is message
    assert args[1].message_thread_id == 222
    assert args[4] == "continue the work"


@pytest.mark.asyncio
async def test_recoverable_topic_message_sends_create_or_cancel_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bot = AsyncMock()
    bot.send_message.return_value = SimpleNamespace(message_id=99)
    message = _message("continue the work", bot=bot, message_thread_id=222)
    context = _Context(state="recoverable")
    orchestrator = SimpleNamespace(ensure_transport_handlers=MagicMock())
    execute = AsyncMock()
    monkeypatch.setattr(codex.codex_daemon, "is_alive", lambda: True)
    monkeypatch.setattr(codex, "_execute_codex_prompt", execute)

    codex._topic_recovery_requests.clear()
    codex._topic_recovery_prompts.clear()
    try:
        await codex.handle_codex_topic_message(message, context, orchestrator)

        orchestrator.ensure_transport_handlers.assert_not_called()
        execute.assert_not_awaited()
        bot.send_message.assert_awaited_once()
        _, kwargs = bot.send_message.await_args
        assert kwargs["chat_id"] == 100
        assert kwargs["message_thread_id"] == 222
        assert "Create a new Codex session" in kwargs["text"]
        assert len(codex._topic_recovery_requests) == 1
        assert codex._topic_recovery_prompts[(100, 222)].message_id == 99
    finally:
        codex._topic_recovery_requests.clear()
        codex._topic_recovery_prompts.clear()


@pytest.mark.asyncio
async def test_recoverable_topic_message_replaces_previous_prompt() -> None:
    bot = AsyncMock()
    bot.send_message.return_value = SimpleNamespace(message_id=100)
    route = TelegramRoute(chat_id=100, message_thread_id=222)
    old_request_id = "old-request"
    codex._topic_recovery_requests[old_request_id] = codex._TopicRecoveryRequest(
        chat_id=100,
        topic_id=222,
        prompt="old",
        user_id=7,
    )
    codex._topic_recovery_prompts[(100, 222)] = codex._TopicRecoveryPrompt(
        request_id=old_request_id,
        message_id=99,
    )
    try:
        await codex._send_topic_recovery_prompt(
            _message("new prompt", bot=bot, message_thread_id=222),
            route,
            "new prompt",
        )

        bot.delete_message.assert_awaited_once_with(chat_id=100, message_id=99)
        bot.send_message.assert_awaited_once()
        assert old_request_id not in codex._topic_recovery_requests
        assert len(codex._topic_recovery_requests) == 1
        assert codex._topic_recovery_prompts[(100, 222)].message_id == 100
    finally:
        codex._topic_recovery_requests.clear()
        codex._topic_recovery_prompts.clear()


@pytest.mark.asyncio
async def test_topic_recovery_create_starts_session_in_current_topic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request_id = "request-1"
    bot = AsyncMock()
    message = _message("recovery prompt", bot=bot, message_thread_id=222)
    callback_query = SimpleNamespace(
        data=f"codex_topic_recover|{request_id}|create",
        message=message,
        answer=AsyncMock(),
    )
    context = _Context(state="not_codex")
    session_manager = _SessionManager()
    orchestrator = SimpleNamespace(
        session_manager=session_manager,
        codex_new_session=AsyncMock(return_value={"thread_id": "thread-new", "cwd": "C:/repo"}),
    )
    execute = AsyncMock()
    monkeypatch.setattr(codex.codex_daemon, "is_alive", lambda: True)
    monkeypatch.setattr(codex, "_execute_codex_prompt", execute)
    codex._topic_recovery_requests[request_id] = codex._TopicRecoveryRequest(
        chat_id=100,
        topic_id=222,
        prompt="run this",
        user_id=7,
    )
    codex._topic_recovery_prompts[(100, 222)] = codex._TopicRecoveryPrompt(
        request_id=request_id,
        message_id=99,
    )
    try:
        await codex.handle_codex_topic_recovery_callback(
            callback_query,
            context,
            orchestrator,
        )

        orchestrator.codex_new_session.assert_awaited_once_with(
            SessionKey.from_telegram_message(100, 222),
            context.session,
            7,
        )
        assert session_manager.set_topic_id_calls == [("thread-new", 222)]
        execute.assert_awaited_once()
        args = execute.await_args.args
        kwargs = execute.await_args.kwargs
        assert args[1].message_thread_id == 222
        assert args[4] == "run this"
        assert kwargs["user_id_override"] == 7
        assert request_id not in codex._topic_recovery_requests
        assert (100, 222) not in codex._topic_recovery_prompts
    finally:
        codex._topic_recovery_requests.clear()
        codex._topic_recovery_prompts.clear()
