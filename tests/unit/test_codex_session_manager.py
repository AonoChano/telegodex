"""Unit tests for Codex-specific session mapping helpers."""

from __future__ import annotations

from types import SimpleNamespace

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
