"""Unit tests for Telegram-facing Codex handlers."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ai.base import AIResponse
from bot.handlers import codex
from bot.utils.routing import TelegramRoute
from core.session import SessionKey
from storage.context_manager import ContextManager
from storage.models import Base, Conversation


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


@pytest.fixture(autouse=True)
def _reset_approval_ui_bridge() -> None:
    codex.approval_ui_bridge.set_bot(None)
    codex.approval_ui_bridge.orchestrator = None
    codex.approval_ui_bridge.db_session_factory = None


class _Scalars:
    def __init__(self, first, all_items=None):
        self._first = first
        self._all = [] if all_items is None else all_items

    def first(self):
        return self._first

    def all(self):
        return self._all


class _DbResult:
    def __init__(self, first, all_items=None):
        self._first = first
        self._all = [] if all_items is None else all_items

    def scalars(self):
        return _Scalars(self._first, self._all)


class _Context:
    def __init__(self, state: str = "not_codex", *, bound: bool | None = None) -> None:
        if bound is not None:
            state = "bound" if bound else "not_codex"
        self.session = AsyncMock()
        active = SimpleNamespace(id=1, topic_id=222) if state == "bound" else None
        historical = SimpleNamespace(id=2, topic_id=222) if state == "recoverable" else None
        conv = SimpleNamespace(
            id=3,
            user_id=7,
            chat_id=100,
            transport="telegram",
            topic_id=None,
            thread_id=None,
            codex_thread_id="thread-abcdef",
            cwd="C:/repo",
            is_active=True,
            provider_sessions=None,
        )
        self.bound_conversation = conv
        self.session.execute = AsyncMock(side_effect=[_DbResult(active), _DbResult(historical)])
        self.session.commit = AsyncMock()
        self.session.add = MagicMock()


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
async def test_codex_bound_topic_filter_catches_text_topic_candidates() -> None:
    message = _message("hello", message_thread_id=222)
    filter_ = codex.IsCodexBoundTopic()

    assert await filter_(message, _Context(state="not_codex")) is True
    assert await filter_(_message("hello")) is False


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
    bind = AsyncMock()
    monkeypatch.setattr(codex, "_bind_codex_thread_to_topic", bind)

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
    bind.assert_awaited_once_with(
        context_manager=context,
        chat_id=100,
        topic_id=222,
        thread_id="thread-abcdef",
        user_id=7,
        cwd="C:/repo",
    )

    method = bot.await_args.args[0]
    assert method.__class__.__name__ == "SendMessage"
    assert "Codex: thread-a" in method.text


@pytest.mark.asyncio
async def test_bind_codex_thread_to_topic_persists_storage_route() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        conv = Conversation(
            user_id=7,
            chat_id=100,
            transport="telegram",
            topic_id=None,
            thread_id=None,
            codex_thread_id="thread-abcdef",
            cwd="C:/old",
            is_active=True,
            provider_sessions={"codex": {"session_id": "thread-abcdef"}},
        )
        session.add(conv)
        await session.commit()

        context = ContextManager(session)
        await codex._bind_codex_thread_to_topic(
            context_manager=context,
            chat_id=100,
            topic_id=222,
            thread_id="thread-abcdef",
            user_id=7,
            cwd="C:/repo",
        )

        result = await session.execute(select(Conversation).where(Conversation.codex_thread_id == "thread-abcdef"))
        rebound = result.scalars().first()
        assert rebound is not None
        assert rebound.chat_id == 100
        assert rebound.thread_id == 222
        assert rebound.topic_id == 222
        assert rebound.transport == "telegram"
        assert rebound.cwd == "C:/repo"
        assert rebound.is_active is True
        assert rebound.provider_sessions["codex"]["session_id"] == "thread-abcdef"
        assert await codex._codex_topic_state(222, context, chat_id=100) == codex._CODEX_TOPIC_BOUND
        assert await codex._codex_topic_state(222, context, chat_id=101) == codex._CODEX_TOPIC_NOT_CODEX

    await engine.dispose()


@pytest.mark.asyncio
async def test_topic_message_routes_directly_to_codex(monkeypatch: pytest.MonkeyPatch) -> None:
    message = _message("continue the work", message_thread_id=222)
    context = _Context(bound=True)
    orchestrator = SimpleNamespace(ensure_transport_handlers=MagicMock())
    execute = AsyncMock()
    bind = AsyncMock()
    monkeypatch.setattr(codex.codex_daemon, "is_alive", lambda: True)
    monkeypatch.setattr(codex, "_execute_codex_prompt", execute)
    monkeypatch.setattr(codex, "_bind_codex_thread_to_topic", bind)
    monkeypatch.setattr(codex, "_ensure_global_orch", lambda orch: None)

    await codex.handle_codex_topic_message(message, context, orchestrator)

    orchestrator.ensure_transport_handlers.assert_called_once()
    execute.assert_awaited_once()
    args = execute.await_args.args
    assert args[0] is message
    assert args[1].message_thread_id == 222
    assert args[4] == "continue the work"


@pytest.mark.asyncio
async def test_non_codex_topic_handler_skips_to_ai_chat() -> None:
    message = _message("normal topic message", message_thread_id=222)
    context = _Context(state="not_codex")
    orchestrator = SimpleNamespace(ensure_transport_handlers=MagicMock())

    with pytest.raises(SkipHandler):
        await codex.handle_codex_topic_message(message, context, orchestrator)

    orchestrator.ensure_transport_handlers.assert_not_called()


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
async def test_codex_command_in_recoverable_topic_sends_create_or_cancel_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bot = AsyncMock()
    bot.send_message.return_value = SimpleNamespace(message_id=101)
    message = _message("/codex continue the work", bot=bot, message_thread_id=222)
    context = _Context(state="recoverable")
    orchestrator = SimpleNamespace(ensure_transport_handlers=MagicMock())
    monkeypatch.setattr(codex.codex_daemon, "is_alive", lambda: True)

    codex._topic_recovery_requests.clear()
    codex._topic_recovery_prompts.clear()
    try:
        await codex.cmd_codex_v2(message, context, orchestrator)

        orchestrator.ensure_transport_handlers.assert_not_called()
        bot.send_message.assert_awaited_once()
        _, kwargs = bot.send_message.await_args
        assert kwargs["chat_id"] == 100
        assert kwargs["message_thread_id"] == 222
        assert "Create a new Codex session" in kwargs["text"]
        request = next(iter(codex._topic_recovery_requests.values()))
        assert request.prompt == "continue the work"
    finally:
        codex._topic_recovery_requests.clear()
        codex._topic_recovery_prompts.clear()


@pytest.mark.asyncio
async def test_codex_command_with_bot_mention_shows_usage() -> None:
    bot = AsyncMock()
    message = _message("/codex@telegodexbot", bot=bot)
    context = _Context(state="not_codex")
    orchestrator = SimpleNamespace(ensure_transport_handlers=MagicMock())

    await codex.cmd_codex_v2(message, context, orchestrator)

    bot.assert_awaited_once()
    method = bot.await_args.args[0]
    assert "Usage:" in method.text
    orchestrator.ensure_transport_handlers.assert_not_called()


@pytest.mark.asyncio
async def test_execute_codex_prompt_pushes_render_updates_to_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = AsyncMock()
    bot.send_message.return_value = SimpleNamespace(chat=SimpleNamespace(id=100), message_id=44)
    message = _message("prompt", bot=bot, chat_type="private")
    route = TelegramRoute.from_message(message)
    context = SimpleNamespace(session=AsyncMock())
    remove_stderr_listener = MagicMock()
    rendered = "Hello\n\n<details><summary>Tool activity</summary>\n\n**Exec**\n\n```sh\npytest\n```\n\n</details>"
    pushed: list[str] = []
    finalized: list[str] = []

    class FakeDraftStream:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def push(self, text: str) -> bool:
            pushed.append(text)
            return True

        async def finalize(self, text: str) -> bool:
            finalized.append(text)
            return True

    session_manager = SimpleNamespace(
        active_turn_count=MagicMock(return_value=1),
        is_turn_active=MagicMock(return_value=True),
    )

    async def handle_message_streaming(**kwargs):
        callbacks = kwargs["callbacks"]
        await callbacks.on_render_update(rendered)
        await callbacks.on_text_delta("Hello", rendered)
        return rendered

    orchestrator = SimpleNamespace(
        session_manager=session_manager,
        handle_message_streaming=AsyncMock(side_effect=handle_message_streaming),
    )
    monkeypatch.setattr(codex, "_bot_token", lambda: "TOKEN")
    monkeypatch.setattr(codex, "DraftStream", FakeDraftStream)
    monkeypatch.setattr(codex.toolbar_handler, "send_reply_keyboard", AsyncMock())
    monkeypatch.setattr(codex.toolbar_handler, "remove_reply_keyboard", AsyncMock())
    monkeypatch.setattr(codex.toolbar_handler, "set_last_reply", MagicMock())
    monkeypatch.setattr(codex, "send_rich_message", AsyncMock(return_value=True))
    monkeypatch.setattr(codex.codex_daemon, "add_stderr_listener", MagicMock(return_value=remove_stderr_listener))

    await codex._execute_codex_prompt(message, route, context, orchestrator, "prompt", user_id_override=7)

    assert pushed == [rendered]
    assert finalized == [rendered]
    assert "<details><summary>Tool activity</summary>" in pushed[0]
    remove_stderr_listener.assert_called_once()


@pytest.mark.asyncio
async def test_execute_codex_prompt_updates_status_on_streaming_error(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = AsyncMock()
    bot.send_message.return_value = SimpleNamespace(chat=SimpleNamespace(id=100), message_id=44)
    message = _message("prompt", bot=bot)
    route = TelegramRoute.from_message(message)
    context = SimpleNamespace(session=AsyncMock())
    remove_stderr_listener = MagicMock()
    session_manager = SimpleNamespace(
        active_turn_count=MagicMock(return_value=1),
        is_turn_active=MagicMock(return_value=True),
    )

    async def handle_message_streaming(**kwargs):
        await kwargs["callbacks"].on_error("Unexpected status 403 Forbidden")
        return "Error: failed"

    orchestrator = SimpleNamespace(
        session_manager=session_manager,
        handle_message_streaming=AsyncMock(side_effect=handle_message_streaming),
    )
    monkeypatch.setattr(codex.toolbar_handler, "send_reply_keyboard", AsyncMock())
    monkeypatch.setattr(codex.toolbar_handler, "remove_reply_keyboard", AsyncMock())
    monkeypatch.setattr(codex, "send_rich_message", AsyncMock(return_value=True))
    monkeypatch.setattr(codex.codex_daemon, "add_stderr_listener", MagicMock(return_value=remove_stderr_listener))

    await codex._execute_codex_prompt(message, route, context, orchestrator, "prompt", user_id_override=7)

    bot.edit_message_text.assert_awaited()
    edited_texts = [call.kwargs["text"] for call in bot.edit_message_text.await_args_list]
    assert any("Unexpected status 403 Forbidden" in text for text in edited_texts)
    remove_stderr_listener.assert_called_once()


@pytest.mark.asyncio
async def test_execute_codex_prompt_updates_status_when_stderr_arrives_after_unknown_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bot = AsyncMock()
    bot.send_message.return_value = SimpleNamespace(chat=SimpleNamespace(id=100), message_id=44)
    message = _message("prompt", bot=bot, chat_type="private")
    route = TelegramRoute.from_message(message)
    context = SimpleNamespace(session=AsyncMock())
    remove_stderr_listener = MagicMock()
    stderr_listener = None
    raw_stderr = "Error: unexpected status 403 Forbidden: Only one Codex conversation can run at a time"
    session_manager = SimpleNamespace(
        active_turn_count=MagicMock(return_value=0),
        is_turn_active=MagicMock(return_value=False),
    )

    def add_stderr_listener(listener):
        nonlocal stderr_listener
        stderr_listener = listener
        return remove_stderr_listener

    async def handle_message_streaming(**kwargs):
        await kwargs["callbacks"].on_error("Unknown error")
        assert stderr_listener is not None
        await stderr_listener(raw_stderr)
        return "_ERROR: Unknown error_\n_ERROR: Unknown error_\n" + raw_stderr

    finalize = AsyncMock(return_value=True)
    orchestrator = SimpleNamespace(
        session_manager=session_manager,
        handle_message_streaming=AsyncMock(side_effect=handle_message_streaming),
    )
    monkeypatch.setattr(codex.toolbar_handler, "send_reply_keyboard", AsyncMock())
    monkeypatch.setattr(codex.toolbar_handler, "remove_reply_keyboard", AsyncMock())
    monkeypatch.setattr(codex.toolbar_handler, "set_last_reply", MagicMock())
    monkeypatch.setattr(codex.DraftStream, "finalize", finalize)
    monkeypatch.setattr(codex, "send_rich_message", AsyncMock(return_value=True))
    monkeypatch.setattr(codex.codex_daemon, "add_stderr_listener", MagicMock(side_effect=add_stderr_listener))
    monkeypatch.setattr(codex, "STDERR_FLUSH_GRACE_SECONDS", 0)

    await codex._execute_codex_prompt(message, route, context, orchestrator, "prompt", user_id_override=7)

    edited_texts = [call.kwargs["text"] for call in bot.edit_message_text.await_args_list]
    assert any("Unknown error" in text for text in edited_texts)
    assert any(raw_stderr in text and "Codex runtime detail" in text for text in edited_texts)
    final_text = finalize.await_args.args[0]
    assert final_text.count(raw_stderr) == 1
    assert "ERROR: Unknown error" not in final_text
    assert "Codex runtime detail" in final_text
    remove_stderr_listener.assert_called_once()


@pytest.mark.asyncio
async def test_execute_codex_prompt_formats_app_server_reconnecting_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bot = AsyncMock()
    bot.send_message.return_value = SimpleNamespace(chat=SimpleNamespace(id=100), message_id=44)
    message = _message("prompt", bot=bot, chat_type="private")
    route = TelegramRoute.from_message(message)
    context = SimpleNamespace(session=AsyncMock())
    remove_stderr_listener = MagicMock()
    runtime_detail = (
        "unexpected status 403 Forbidden: 当前公益站使用人数较多，本时段全站额度已用完，请12:00 后再试。"
        "（traceid: 60c481be-56e0-479b-8416-f4edbc60999d）, "
        "url: https://new.sharedchat.cc/codex/responses, cf-ray: a0e7dd11ca8419c9-KIX"
    )
    session_manager = SimpleNamespace(
        active_turn_count=MagicMock(return_value=1),
        is_turn_active=MagicMock(return_value=True),
    )

    async def handle_message_streaming(**kwargs):
        callbacks = kwargs["callbacks"]
        await callbacks.on_codex_error("Reconnecting... 4/5", runtime_detail, True)
        await callbacks.on_turn_completed(
            {"status": "failed", "error": {"message": "Unknown error"}},
            "**Error:** Unknown error",
        )
        return "**Error:** Unknown error"

    finalize = AsyncMock(return_value=True)
    orchestrator = SimpleNamespace(
        session_manager=session_manager,
        handle_message_streaming=AsyncMock(side_effect=handle_message_streaming),
    )
    monkeypatch.setattr(codex.toolbar_handler, "send_reply_keyboard", AsyncMock())
    monkeypatch.setattr(codex.toolbar_handler, "remove_reply_keyboard", AsyncMock())
    monkeypatch.setattr(codex.toolbar_handler, "set_last_reply", MagicMock())
    monkeypatch.setattr(codex.DraftStream, "finalize", finalize)
    monkeypatch.setattr(codex, "send_rich_message", AsyncMock(return_value=True))
    monkeypatch.setattr(codex.codex_daemon, "add_stderr_listener", MagicMock(return_value=remove_stderr_listener))
    monkeypatch.setattr(codex, "STDERR_FLUSH_GRACE_SECONDS", 0)

    await codex._execute_codex_prompt(message, route, context, orchestrator, "prompt", user_id_override=7)

    edited_texts = [call.kwargs["text"] for call in bot.edit_message_text.await_args_list]
    retry_text = next(text for text in edited_texts if "Codex Reconnecting..." in text)
    assert "Reconnecting... 4/5" in retry_text
    assert "unexpected status 403 Forbidden" in retry_text
    assert "traceid: 60c481be-56e0-479b-8416-f4edbc60999d" in retry_text
    assert "url: https://new.sharedchat.cc/codex/responses" in retry_text
    assert "cf-ray: a0e7dd11ca8419c9-KIX" in retry_text
    assert "Unknown error" not in retry_text

    final_status = edited_texts[-1]
    assert "Codex failed." in final_status
    assert "Unknown error" not in final_status

    final_text = finalize.await_args.args[0]
    assert "ERROR: Unknown error" not in final_text
    assert "**Error:** Unknown error" not in final_text
    assert "Codex runtime detail" in final_text
    assert runtime_detail in final_text
    remove_stderr_listener.assert_called_once()


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
    bind = AsyncMock()
    monkeypatch.setattr(codex.codex_daemon, "is_alive", lambda: True)
    monkeypatch.setattr(codex, "_execute_codex_prompt", execute)
    monkeypatch.setattr(codex, "_bind_codex_thread_to_topic", bind)
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
        bind.assert_awaited_once_with(
            context_manager=context,
            chat_id=100,
            topic_id=222,
            thread_id="thread-new",
            user_id=7,
            cwd="C:/repo",
        )
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


@pytest.mark.asyncio
async def test_cmd_shell_without_args_or_help_shows_usage() -> None:
    for text in ("/shell", "/shell -h", "/shell help", "/shell --help"):
        bot = AsyncMock()
        message = _message(text, bot=bot)

        await codex.cmd_shell(message, SimpleNamespace())

        bot.assert_awaited_once()
        method = bot.await_args.args[0]
        assert "Usage:" in method.text
        assert "/shell <natural language task>" in method.text
        assert "/shell !<command>" in method.text


@pytest.mark.asyncio
async def test_cmd_shell_natural_language_generates_command_proposal(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = AsyncMock()
    status_msg = SimpleNamespace(edit_text=AsyncMock())
    bot.return_value = status_msg
    message = _message("/shell show current directory", bot=bot)
    provider = SimpleNamespace(
        default_model="test-model",
        chat=AsyncMock(
            return_value=AIResponse(
                content='{"command":"Get-Location","explanation":"Shows cwd","risk":"Read-only"}',
                model="test-model",
            )
        ),
    )
    context = SimpleNamespace(
        get_or_create_user=AsyncMock(
            return_value=SimpleNamespace(preferred_provider="deepseek", preferred_model="deepseek-test")
        )
    )
    orchestrator = SimpleNamespace(
        set_approval_ui_sender=MagicMock(),
        providers=SimpleNamespace(get_provider=MagicMock(return_value=provider)),
        pending_shell_commands={},
    )
    monkeypatch.setattr(codex.approval_ui_bridge, "orchestrator", None)

    await codex.cmd_shell(message, orchestrator, context)

    context.get_or_create_user.assert_awaited_once_with(7)
    provider.chat.assert_awaited_once()
    assert len(orchestrator.pending_shell_commands) == 1
    pending = next(iter(orchestrator.pending_shell_commands.values()))
    assert pending["command"] == "Get-Location"
    status_msg.edit_text.assert_awaited_once()
    _, kwargs = status_msg.edit_text.await_args
    assert "reply_markup" in kwargs
    assert kwargs["reply_markup"].inline_keyboard[0][0].text == "Run"
    assert kwargs["parse_mode"] == "HTML"


@pytest.mark.asyncio
async def test_cmd_shell_natural_language_no_command_uses_html_without_buttons(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bot = AsyncMock()
    status_msg = SimpleNamespace(edit_text=AsyncMock())
    bot.return_value = status_msg
    message = _message("/shell delete all important files", bot=bot)
    provider = SimpleNamespace(
        default_model="test-model",
        chat=AsyncMock(
            return_value=AIResponse(
                content='{"command":"","explanation":"Too destructive","risk":"High"}',
                model="test-model",
            )
        ),
    )
    orchestrator = SimpleNamespace(
        set_approval_ui_sender=MagicMock(),
        providers=SimpleNamespace(get_provider=MagicMock(return_value=provider)),
        pending_shell_commands={},
    )
    monkeypatch.setattr(codex.approval_ui_bridge, "orchestrator", None)

    await codex.cmd_shell(message, orchestrator)

    assert orchestrator.pending_shell_commands == {}
    status_msg.edit_text.assert_awaited_once()
    _, kwargs = status_msg.edit_text.await_args
    assert kwargs["parse_mode"] == "HTML"
    assert "reply_markup" not in kwargs


@pytest.mark.asyncio
async def test_cmd_shell_raw_prefix_executes_directly(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = AsyncMock()
    message = _message("/shell !git status", bot=bot, message_thread_id=222)
    execute = AsyncMock()
    orchestrator = SimpleNamespace(
        set_approval_ui_sender=MagicMock(),
        shell_is_dangerous=MagicMock(return_value=False),
        pending_shell_commands={},
    )
    monkeypatch.setattr(codex.approval_ui_bridge, "orchestrator", None)
    monkeypatch.setattr(codex, "_execute_shell_telegram", execute)

    await codex.cmd_shell(message, orchestrator)

    execute.assert_awaited_once()
    assert execute.await_args.args[3] == "git status"
    assert execute.await_args.args[4] == SessionKey.from_telegram_message(100, 222)


@pytest.mark.asyncio
async def test_shell_ai_run_callback_executes_safe_command(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = AsyncMock()
    message = _message("proposal", bot=bot)
    route = TelegramRoute.from_message(message)
    session_key = SessionKey.from_telegram_message(100, None)
    execute = AsyncMock()
    orchestrator = SimpleNamespace(
        pending_shell_commands={
            "proposal-1": {
                "command": "Get-Location",
                "message": message,
                "route": route,
                "session_key": session_key,
            }
        },
        shell_is_dangerous=MagicMock(return_value=False),
    )
    callback_query = SimpleNamespace(
        data="shell_ai:proposal-1:run",
        message=message,
        answer=AsyncMock(),
    )
    monkeypatch.setattr(codex, "_execute_shell_telegram", execute)

    await codex.handle_shell_ai_callback(callback_query, orchestrator)

    callback_query.answer.assert_awaited_once_with("Executing...")
    execute.assert_awaited_once_with(message, route, orchestrator, "Get-Location", session_key)
    assert orchestrator.pending_shell_commands == {}


@pytest.mark.asyncio
async def test_shell_ai_run_callback_requires_second_confirmation_for_dangerous_command() -> None:
    bot = AsyncMock()
    message = _message("proposal", bot=bot)
    route = TelegramRoute.from_message(message)
    session_key = SessionKey.from_telegram_message(100, None)
    orchestrator = SimpleNamespace(
        pending_shell_commands={
            "proposal-1": {
                "command": "shutdown /s",
                "message": message,
                "route": route,
                "session_key": session_key,
            }
        },
        shell_is_dangerous=MagicMock(return_value=True),
    )
    callback_query = SimpleNamespace(
        data="shell_ai:proposal-1:run",
        message=message,
        answer=AsyncMock(),
    )

    await codex.handle_shell_ai_callback(callback_query, orchestrator)

    callback_query.answer.assert_awaited_once_with("Confirmation required")
    assert "proposal-1" not in orchestrator.pending_shell_commands
    assert len(orchestrator.pending_shell_commands) == 1
    pending = next(iter(orchestrator.pending_shell_commands.values()))
    assert pending["command"] == "shutdown /s"
