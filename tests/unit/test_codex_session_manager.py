"""Unit tests for Codex-specific session mapping helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.session import SessionKey
from extensions.codex.session import CodexSessionManager


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
