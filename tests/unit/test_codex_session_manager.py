"""Unit tests for Codex-specific session mapping helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.session import SessionKey
from extensions.codex.session import CodexSessionManager
from storage.models import Base, Conversation


def test_update_session_key_moves_runtime_mappings() -> None:
    """A session created in the main chat can be rebound to a forum topic."""
    manager = CodexSessionManager(SimpleNamespace(transport=None))
    old_key = SessionKey.from_telegram_message(100, None)
    new_key = SessionKey.from_telegram_message(100, 222)

    session = SimpleNamespace(thread_id="thread-123")
    manager._sessions[old_key] = session
    manager._thread_to_session_key[session.thread_id] = old_key
    manager._resume_info[old_key] = {
        "thread_id": session.thread_id,
        "resumed_at": "2026-06-18T00:00:00",
    }

    assert manager.update_session_key(old_key, new_key) is True

    assert manager.get_session(old_key) is None
    assert manager.get_session(new_key) is session
    assert manager.reverse_lookup(session.thread_id) == new_key
    assert manager.get_resume_info(old_key) is None
    assert manager.get_resume_info(new_key) == {
        "thread_id": session.thread_id,
        "resumed_at": "2026-06-18T00:00:00",
    }


def test_update_session_key_returns_false_for_missing_session() -> None:
    manager = CodexSessionManager(SimpleNamespace(transport=None))
    old_key = SessionKey.from_telegram_message(100, None)
    new_key = SessionKey.from_telegram_message(100, 222)

    assert manager.update_session_key(old_key, new_key) is False


@pytest.mark.asyncio
async def test_reverse_lookup_db_fallback_recovers_unloaded_thread() -> None:
    """A thread persisted in DB but not in memory must still resolve.

    Reproduces the approval-button root cause: after a bot restart or daemon
    reconnect, the app-server may replay an approval request for a thread
    whose SessionKey is not yet in ``_thread_to_session_key``. Without a DB
    fallback the approval UI is silently skipped and the turn auto-denies.
    """
    manager = CodexSessionManager(SimpleNamespace(transport=None))

    conv = SimpleNamespace(
        chat_id=4242,
        transport="telegram",
        topic_id=99,
        thread_id=99,
        codex_thread_id="thread-abc",
        is_active=True,
    )
    db = MagicMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=conv))))
    )

    key = await manager.reverse_lookup_db_fallback("thread-abc", db)
    assert key is not None
    assert key.chat_id == 4242
    assert key.topic_id == 99
    # Cached for subsequent sync lookups.
    assert manager.reverse_lookup("thread-abc") == key


@pytest.mark.asyncio
async def test_reverse_lookup_db_fallback_returns_none_when_not_found() -> None:
    manager = CodexSessionManager(SimpleNamespace(transport=None))
    db = MagicMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None))))
    )

    assert await manager.reverse_lookup_db_fallback("missing", db) is None


@pytest.mark.asyncio
async def test_reverse_lookup_db_fallback_rejects_missing_chat_id() -> None:
    manager = CodexSessionManager(SimpleNamespace(transport=None))
    conv = SimpleNamespace(
        chat_id=None,
        transport="telegram",
        topic_id=99,
        thread_id=99,
        codex_thread_id="thread-abc",
        is_active=True,
    )
    db = MagicMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=conv))))
    )

    assert await manager.reverse_lookup_db_fallback("thread-abc", db) is None


@pytest.mark.asyncio
async def test_resume_session_archives_previous_topic_binding() -> None:
    transport = SimpleNamespace(
        send_request=AsyncMock(
            return_value={
                "thread": {
                    "id": "thread-abc",
                    "cwd": "C:/repo",
                    "path": "C:/sessions/thread-abc.jsonl",
                },
                "cwd": "C:/repo",
            }
        )
    )
    manager = CodexSessionManager(SimpleNamespace(transport=transport))
    old_key = SessionKey.from_telegram_message(100, 222)
    old_runtime_session = SimpleNamespace(thread_id="thread-abc")
    manager._sessions[old_key] = old_runtime_session
    manager._thread_to_session_key["thread-abc"] = old_key
    manager._thread_to_topic["thread-abc"] = 222
    manager._resume_info[old_key] = {
        "thread_id": "thread-abc",
        "resumed_at": "2026-07-14T00:00:00",
    }
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        old_binding = Conversation(
            user_id=7,
            chat_id=100,
            transport="telegram",
            topic_id=222,
            thread_id=222,
            codex_thread_id="thread-abc",
            cwd="C:/repo",
            is_active=True,
            provider_sessions={"codex": {"session_id": "thread-abc"}},
        )
        session.add(old_binding)
        await session.commit()

        main_key = SessionKey.from_telegram_message(100, None)
        resumed, _ = await manager.resume_session(session, main_key, 7, "thread-abc")

        result = await session.execute(
            select(Conversation)
            .where(
                Conversation.chat_id == 100,
                Conversation.codex_thread_id == "thread-abc",
            )
            .order_by(Conversation.id)
        )
        old_row, pending_row = result.scalars().all()
        assert resumed.thread_id == "thread-abc"
        assert old_row.topic_id == 222
        assert old_row.is_active is False
        assert pending_row.topic_id is None
        assert pending_row.thread_id is None
        assert pending_row.is_active is True
        assert manager.get_session(old_key) is None
        assert manager.get_resume_info(old_key) is None
        assert manager.get_topic_id("thread-abc") is None
        assert manager.reverse_lookup("thread-abc") == main_key
        transport.send_request.assert_awaited_once_with(
            "thread/resume",
            {"threadId": "thread-abc"},
        )

    await engine.dispose()
