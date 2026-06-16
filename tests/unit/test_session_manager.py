"""Unit tests for core.session.manager.SessionManager."""

from __future__ import annotations

import pytest

from core.session import SessionKey, session_manager
from core.session.data import ProviderSessionData, SessionData
from core.session.manager import LockPool, SessionManager


class TestSessionKey:
    """Cover ``SessionKey`` serialization and factory methods."""

    def test_to_string_without_topic(self) -> None:
        key = SessionKey(transport="telegram", chat_id=42)
        assert key.to_string() == "telegram:42"

    def test_to_string_with_topic(self) -> None:
        key = SessionKey(transport="telegram", chat_id=42, topic_id=7)
        assert key.to_string() == "telegram:42:7"

    def test_from_string_old_flat_chat_id(self) -> None:
        key = SessionKey.from_string("123")
        assert key.transport == "telegram"
        assert key.chat_id == 123
        assert key.topic_id is None

    def test_from_string_old_chat_topic(self) -> None:
        key = SessionKey.from_string("123:456")
        assert key.transport == "telegram"
        assert key.chat_id == 123
        assert key.topic_id == 456

    def test_from_string_new_format_no_topic(self) -> None:
        key = SessionKey.from_string("telegram:123")
        assert key.chat_id == 123
        assert key.topic_id is None

    def test_from_string_new_format_with_topic(self) -> None:
        key = SessionKey.from_string("telegram:123:456")
        assert key.chat_id == 123
        assert key.topic_id == 456

    def test_from_string_invalid(self) -> None:
        with pytest.raises(ValueError):
            SessionKey.from_string("a:b:c:d")

    def test_from_telegram_message(self) -> None:
        key = SessionKey.from_telegram_message(123, message_thread_id=456)
        assert key == SessionKey("telegram", 123, 456)


class TestLockPool:
    """Cover ``LockPool`` shared-lock semantics."""

    @pytest.mark.asyncio
    async def test_same_key_returns_same_lock(self) -> None:
        pool = LockPool()
        lock1 = pool.get_lock(1, 2)
        lock2 = pool.get_lock(1, 2)
        assert lock1 is lock2

    @pytest.mark.asyncio
    async def test_different_keys_return_different_locks(self) -> None:
        pool = LockPool()
        lock1 = pool.get_lock(1, 2)
        lock2 = pool.get_lock(1, 3)
        assert lock1 is not lock2


class TestSessionManagerBasic:
    """Cover opaque session storage."""

    def test_get_set_remove_session(self) -> None:
        mgr = SessionManager()
        key = SessionKey("telegram", 1)
        assert mgr.get_session(key) is None

        mgr.set_session(key, {"foo": "bar"})
        assert mgr.get_session(key) == {"foo": "bar"}

        removed = mgr.remove_session(key)
        assert removed == {"foo": "bar"}
        assert mgr.get_session(key) is None

    def test_get_lock(self) -> None:
        mgr = SessionManager()
        key = SessionKey("telegram", 1, 2)
        lock = mgr.get_lock(key)
        assert lock is mgr.get_lock(key)


class TestSessionManagerProviderBuckets:
    """Cover provider-isolated session data and switching."""

    def test_get_or_create_session_data(self) -> None:
        mgr = SessionManager()
        key = SessionKey("telegram", 1)
        data = mgr.get_or_create_session_data(key)
        assert isinstance(data, SessionData)
        assert mgr.get_session_data(key) is data

    def test_set_active_provider_creates_bucket(self) -> None:
        mgr = SessionManager()
        key = SessionKey("telegram", 1)
        bucket = mgr.set_active_provider(key, "openai")
        assert isinstance(bucket, ProviderSessionData)
        assert mgr.get_or_create_session_data(key).active_provider == "openai"

    def test_switch_provider_preserves_old_bucket(self) -> None:
        mgr = SessionManager()
        key = SessionKey("telegram", 1)

        openai_bucket = mgr.set_active_provider(key, "openai")
        openai_bucket.session_id = "conv-openai"

        anthropic_bucket = mgr.set_active_provider(key, "anthropic")
        anthropic_bucket.session_id = "conv-anthropic"

        data = mgr.get_session_data(key)
        assert data.provider_sessions["openai"].session_id == "conv-openai"
        assert data.provider_sessions["anthropic"].session_id == "conv-anthropic"
        assert data.active_provider == "anthropic"

    def test_get_active_provider_session(self) -> None:
        mgr = SessionManager()
        key = SessionKey("telegram", 1)
        assert mgr.get_active_provider_session(key) is None

        mgr.set_active_provider(key, "openai")
        bucket = mgr.get_active_provider_session(key)
        assert bucket is not None
        assert isinstance(bucket, ProviderSessionData)

    def test_update_provider_stats(self) -> None:
        mgr = SessionManager()
        key = SessionKey("telegram", 1)
        mgr.update_provider_stats(
            key, "openai", message_count=2, cost_usd=0.05, tokens=500
        )
        bucket = mgr.get_or_create_session_data(key).get_or_create_bucket("openai")
        assert bucket.message_count == 2
        assert bucket.total_cost_usd == 0.05
        assert bucket.total_tokens == 500

        mgr.update_provider_stats(key, "openai", message_count=1, cost_usd=0.01, tokens=100)
        assert bucket.message_count == 3
        assert bucket.total_cost_usd == pytest.approx(0.06)
        assert bucket.total_tokens == 600

    def test_remove_session_data(self) -> None:
        mgr = SessionManager()
        key = SessionKey("telegram", 1)
        mgr.set_active_provider(key, "openai")
        removed = mgr.remove_session_data(key)
        assert isinstance(removed, SessionData)
        assert mgr.get_session_data(key) is None


class TestSessionDataSerialization:
    """Cover ``SessionData`` / ``ProviderSessionData`` round-trips."""

    def test_provider_session_data_roundtrip(self) -> None:
        original = ProviderSessionData(
            session_id="s1", message_count=3, total_cost_usd=0.02, total_tokens=200
        )
        restored = ProviderSessionData.from_dict(original.to_dict())
        assert restored == original

    def test_session_data_roundtrip(self) -> None:
        data = SessionData()
        data.set_active_provider("openai")
        data.get_or_create_bucket("openai").session_id = "abc"
        data.get_or_create_bucket("anthropic").session_id = "def"

        restored = SessionData.from_dict(data.to_dict())
        assert restored.active_provider == "openai"
        assert restored.provider_sessions["openai"].session_id == "abc"
        assert restored.provider_sessions["anthropic"].session_id == "def"

    def test_from_dict_none(self) -> None:
        assert SessionData.from_dict(None) == SessionData()
