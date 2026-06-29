"""Unit tests for Codex topic recovery prompt state."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import Message

from bot.codex import topic_recovery
from bot.codex.topic_recovery import TopicRecoveryPrompt, TopicRecoveryRequest, TopicRecoveryStore
from bot.utils.routing import TelegramRoute


def _message(
    text: str = "continue",
    *,
    bot: AsyncMock | None = None,
    chat_id: int = 100,
    user_id: int = 7,
    message_thread_id: int | None = 222,
) -> Message:
    payload = {
        "message_id": 1,
        "date": int(datetime.now().timestamp()),
        "chat": {"id": chat_id, "type": "supergroup"},
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


def test_key_for_route_requires_topic_id() -> None:
    store = TopicRecoveryStore()

    assert store.key_for_route(TelegramRoute(chat_id=100, message_thread_id=222)) == (100, 222)
    assert store.key_for_route(TelegramRoute(chat_id=100)) is None


def test_pop_request_removes_pending_request() -> None:
    store = TopicRecoveryStore()
    store.requests["request-1"] = TopicRecoveryRequest(
        chat_id=100,
        topic_id=222,
        prompt="continue",
        user_id=7,
    )

    request = store.pop_request("request-1")

    assert request is not None
    assert request.prompt == "continue"
    assert store.requests == {}


@pytest.mark.asyncio
async def test_send_prompt_replaces_previous_prompt_for_topic() -> None:
    bot = AsyncMock()
    bot.send_message.return_value = SimpleNamespace(message_id=100)
    store = TopicRecoveryStore()
    route = TelegramRoute(chat_id=100, message_thread_id=222)
    old_request_id = "old-request"
    store.requests[old_request_id] = TopicRecoveryRequest(
        chat_id=100,
        topic_id=222,
        prompt="old",
        user_id=7,
    )
    store.prompts[(100, 222)] = TopicRecoveryPrompt(
        request_id=old_request_id,
        message_id=99,
    )

    await store.send_prompt(
        _message("new prompt", bot=bot, message_thread_id=222),
        route,
        "new prompt",
    )

    bot.delete_message.assert_awaited_once_with(chat_id=100, message_id=99)
    bot.send_message.assert_awaited_once()
    _, kwargs = bot.send_message.await_args
    assert kwargs["chat_id"] == 100
    assert kwargs["message_thread_id"] == 222
    assert "Create a new Codex session" in kwargs["text"]
    assert old_request_id not in store.requests
    assert len(store.requests) == 1
    request = next(iter(store.requests.values()))
    assert request.prompt == "new prompt"
    assert store.prompts[(100, 222)].message_id == 100


@pytest.mark.asyncio
async def test_send_prompt_skips_when_message_has_no_topic() -> None:
    bot = AsyncMock()
    store = TopicRecoveryStore()

    await store.send_prompt(
        _message("new prompt", bot=bot, message_thread_id=None),
        TelegramRoute(chat_id=100),
        "new prompt",
    )

    bot.send_message.assert_not_awaited()
    assert store.requests == {}
    assert store.prompts == {}

def _callback(data: str, message: Message | None) -> SimpleNamespace:
    return SimpleNamespace(data=data, message=message, answer=AsyncMock())


def _recovery_deps(*, alive: bool = True) -> dict[str, object]:
    return {
        "codex_daemon": SimpleNamespace(is_alive=MagicMock(return_value=alive)),
        "bind_codex_thread_to_topic": AsyncMock(),
        "execute_codex_prompt": AsyncMock(),
        "codex_reply": AsyncMock(),
    }


@pytest.mark.asyncio
async def test_handle_topic_recovery_callback_cancel_removes_prompt_state() -> None:
    bot = AsyncMock()
    store = TopicRecoveryStore()
    request_id = "request-1"
    store.requests[request_id] = TopicRecoveryRequest(
        chat_id=100,
        topic_id=222,
        prompt="continue",
        user_id=7,
    )
    store.prompts[(100, 222)] = TopicRecoveryPrompt(request_id=request_id, message_id=99)
    callback_query = _callback(f"codex_topic_recover|{request_id}|cancel", _message(bot=bot))
    deps = _recovery_deps()

    await topic_recovery.handle_topic_recovery_callback(
        callback_query,
        SimpleNamespace(session=AsyncMock()),
        SimpleNamespace(session_manager=None),
        store=store,
        **deps,
    )

    callback_query.answer.assert_awaited_once_with("Cancelled.", show_alert=False)
    assert store.requests == {}
    assert store.prompts == {}
    deps["execute_codex_prompt"].assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_topic_recovery_callback_create_starts_session() -> None:
    bot = AsyncMock()
    store = TopicRecoveryStore()
    request_id = "request-1"
    store.requests[request_id] = TopicRecoveryRequest(
        chat_id=100,
        topic_id=222,
        prompt="continue",
        user_id=7,
    )
    store.prompts[(100, 222)] = TopicRecoveryPrompt(request_id=request_id, message_id=99)
    callback_query = _callback(f"codex_topic_recover|{request_id}|create", _message(bot=bot))
    context = SimpleNamespace(session=AsyncMock())
    session_manager = SimpleNamespace(set_topic_id=MagicMock())
    orchestrator = SimpleNamespace(
        session_manager=session_manager,
        codex_new_session=AsyncMock(return_value={"thread_id": "thread-new", "cwd": "C:/repo"}),
    )
    deps = _recovery_deps()

    await topic_recovery.handle_topic_recovery_callback(
        callback_query,
        context,
        orchestrator,
        store=store,
        **deps,
    )

    orchestrator.codex_new_session.assert_awaited_once()
    session_manager.set_topic_id.assert_called_once_with("thread-new", 222)
    deps["bind_codex_thread_to_topic"].assert_awaited_once_with(
        context_manager=context,
        chat_id=100,
        topic_id=222,
        thread_id="thread-new",
        user_id=7,
        cwd="C:/repo",
    )
    deps["execute_codex_prompt"].assert_awaited_once()
    callback_query.answer.assert_awaited_once_with("Created.", show_alert=False)
    assert store.requests == {}
    assert store.prompts == {}
