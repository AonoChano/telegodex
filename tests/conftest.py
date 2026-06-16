"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.session import SessionKey, session_manager
from core.session.data import ProviderSessionData, SessionData


@pytest.fixture(autouse=True)
def _reset_global_session_manager():
    """Reset the global ``session_manager`` between tests."""
    session_manager._sessions.clear()
    session_manager._session_data.clear()
    session_manager._lock_pool._locks.clear()
    yield
    session_manager._sessions.clear()
    session_manager._session_data.clear()
    session_manager._lock_pool._locks.clear()


@pytest.fixture
def sample_session_key() -> SessionKey:
    return SessionKey(transport="telegram", chat_id=123456, topic_id=789)


@pytest.fixture
def sample_session_data() -> SessionData:
    data = SessionData()
    data.set_active_provider("openai")
    bucket = data.get_or_create_bucket("openai")
    bucket.session_id = "conv-42"
    bucket.message_count = 5
    bucket.total_cost_usd = 0.01
    bucket.total_tokens = 1000
    return data


@pytest.fixture
def mock_ai_provider() -> MagicMock:
    """Return a mock AI provider with a working ``chat_stream``."""
    provider = MagicMock()

    async def _chat_stream(*args: Any, **kwargs: Any) -> AsyncIterator[str]:
        yield "Hello"
        yield " world"

    chat_stream_mock = MagicMock()
    chat_stream_mock.side_effect = _chat_stream
    provider.chat_stream = chat_stream_mock
    provider.chat = AsyncMock(return_value=MagicMock(
        content="Hello world",
        model="gpt-4",
        usage=None,
    ))
    return provider


@pytest.fixture
def mock_context_manager() -> AsyncMock:
    """Return a mocked ``ContextManager`` with deterministic returns."""
    cm = AsyncMock()
    conversation = MagicMock()
    conversation.id = 42
    conversation.provider_sessions = None
    cm.get_or_create_conversation = AsyncMock(return_value=conversation)
    cm.get_or_create_user = AsyncMock(return_value=MagicMock(
        preferred_provider="openai",
        preferred_model="gpt-4",
        temperature="0.7",
    ))
    cm.add_message = AsyncMock()
    cm.get_conversation_history = AsyncMock(return_value=[])
    cm.session.commit = AsyncMock()
    return cm
