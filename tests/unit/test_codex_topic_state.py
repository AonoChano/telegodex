"""Unit tests for Codex topic storage helpers."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.codex import topic_state
from storage.context_manager import ContextManager
from storage.models import Base, Conversation

pytestmark = pytest.mark.asyncio


async def _session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def test_bind_codex_thread_to_topic_persists_storage_route() -> None:
    engine, session_factory = await _session_factory()
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
        await topic_state.bind_codex_thread_to_topic(
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
        assert await topic_state.codex_topic_state(222, context, chat_id=100) == topic_state.CODEX_TOPIC_BOUND
        assert await topic_state.codex_topic_state(222, context, chat_id=101) == topic_state.CODEX_TOPIC_NOT_CODEX

    await engine.dispose()


async def test_codex_topic_state_distinguishes_recoverable_inactive_topic() -> None:
    engine, session_factory = await _session_factory()
    async with session_factory() as session:
        conv = Conversation(
            user_id=7,
            chat_id=100,
            transport="telegram",
            topic_id=222,
            thread_id=222,
            codex_thread_id="thread-abcdef",
            is_active=False,
        )
        session.add(conv)
        await session.commit()

        context = ContextManager(session)
        assert await topic_state.codex_topic_state(222, context, chat_id=100) == topic_state.CODEX_TOPIC_RECOVERABLE
        assert await topic_state.is_codex_bound_topic(222, context, chat_id=100) is False
        assert await topic_state.codex_topic_state(333, context, chat_id=100) == topic_state.CODEX_TOPIC_NOT_CODEX

    await engine.dispose()

