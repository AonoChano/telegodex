from __future__ import annotations

import asyncio
import threading
from typing import Any

from .data import ProviderSessionData, SessionData
from .key import SessionKey


class LockPool:
    """Shared ``asyncio.Lock`` per ``(chat_id, topic_id)`` pair.

    Safe for concurrent use from a single event loop.
    """

    def __init__(self) -> None:
        self._locks: dict[tuple[int, int | None], asyncio.Lock] = {}
        self._mutex = threading.Lock()

    def get_lock(self, chat_id: int, topic_id: int | None = None) -> asyncio.Lock:
        """Return the lock for the given chat/topic, creating it if necessary."""
        key = (chat_id, topic_id)
        with self._mutex:
            lock = self._locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._locks[key] = lock
            return lock


class SessionManager:
    """Generic in-memory session manager keyed by ``SessionKey``.

    Holds two maps:
    - ``_sessions``: backward-compatible opaque session storage.
    - ``_session_data``: structured ``SessionData`` with provider-isolated
      buckets.
    """

    def __init__(self) -> None:
        self._sessions: dict[SessionKey, Any] = {}
        self._session_data: dict[SessionKey, SessionData] = {}
        self._lock_pool = LockPool()

    # ------------------------------------------------------------------
    # Opaque session storage (backward compatible)
    # ------------------------------------------------------------------

    def get_session(self, key: SessionKey) -> Any | None:
        """Return the session for *key* if one exists."""
        return self._sessions.get(key)

    def set_session(self, key: SessionKey, session: Any) -> None:
        """Store *session* under *key*."""
        self._sessions[key] = session

    def remove_session(self, key: SessionKey) -> Any | None:
        """Remove and return the session for *key*, or ``None``."""
        return self._sessions.pop(key, None)

    def get_lock(self, key: SessionKey) -> asyncio.Lock:
        """Return the shared lock for *key*'s chat/topic pair."""
        return self._lock_pool.get_lock(key.chat_id, key.topic_id)

    @property
    def lock_pool(self) -> LockPool:
        """Expose the internal lock pool for sharing with the MessageBus."""
        return self._lock_pool

    # ------------------------------------------------------------------
    # Provider-isolated session data
    # ------------------------------------------------------------------

    def get_session_data(self, key: SessionKey) -> SessionData | None:
        """Return the ``SessionData`` for *key*, or ``None``."""
        return self._session_data.get(key)

    def get_or_create_session_data(self, key: SessionKey) -> SessionData:
        """Return the ``SessionData`` for *key*, creating it if absent."""
        if key not in self._session_data:
            self._session_data[key] = SessionData()
        return self._session_data[key]

    def set_session_data(self, key: SessionKey, data: SessionData) -> None:
        """Store *data* under *key*."""
        self._session_data[key] = data

    def remove_session_data(self, key: SessionKey) -> SessionData | None:
        """Remove and return the ``SessionData`` for *key*, or ``None``."""
        return self._session_data.pop(key, None)

    def set_active_provider(self, key: SessionKey, provider_name: str) -> ProviderSessionData:
        """Set *provider_name* as the active provider for *key*.

        Returns the bucket for that provider (creating it only when the
        bucket has no prior state).
        """
        data = self.get_or_create_session_data(key)
        return data.set_active_provider(provider_name)

    def get_active_provider_session(self, key: SessionKey) -> ProviderSessionData | None:
        """Return the bucket for the active provider of *key*, or ``None``."""
        data = self._session_data.get(key)
        if data is None or data.active_provider is None:
            return None
        return data.provider_sessions.get(data.active_provider)

    def update_provider_stats(
        self,
        key: SessionKey,
        provider_name: str,
        *,
        message_count: int = 0,
        cost_usd: float = 0.0,
        tokens: int = 0,
    ) -> None:
        """Accumulate usage stats into the bucket for *provider_name*."""
        data = self.get_or_create_session_data(key)
        bucket = data.get_or_create_bucket(provider_name)
        bucket.message_count += message_count
        bucket.total_cost_usd += cost_usd
        bucket.total_tokens += tokens


# Shared global session manager used across handlers for provider buckets.
session_manager = SessionManager()
