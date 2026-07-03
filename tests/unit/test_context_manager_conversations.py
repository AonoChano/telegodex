from __future__ import annotations

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ai import MessageRole
from storage.context_manager import ContextManager
from storage.models import Base, Conversation, ConversationMessage, Database


@pytest.mark.asyncio
async def test_get_or_create_conversation_archives_duplicate_active_rows() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        old = Conversation(user_id=7, thread_id=None, topic_id=None, title="old", is_active=True)
        latest = Conversation(user_id=7, thread_id=None, topic_id=None, title="latest", is_active=True)
        session.add_all([old, latest])
        await session.commit()

        manager = ContextManager(session)
        conversation = await manager.get_or_create_conversation(7)

        assert conversation.id == latest.id

        result = await session.execute(
            select(Conversation)
            .where(Conversation.user_id == 7, Conversation.thread_id.is_(None))
            .order_by(Conversation.id)
        )
        rows = result.scalars().all()
        assert [row.is_active for row in rows] == [False, True]

    await engine.dispose()


@pytest.mark.asyncio
async def test_get_or_create_conversation_prefers_chat_scoped_rows() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        other_chat = Conversation(
            user_id=7,
            chat_id=100,
            thread_id=222,
            topic_id=222,
            title="other",
            is_active=True,
        )
        current_chat = Conversation(
            user_id=7,
            chat_id=200,
            thread_id=222,
            topic_id=222,
            title="current",
            is_active=True,
        )
        session.add_all([other_chat, current_chat])
        await session.commit()

        manager = ContextManager(session)
        conversation = await manager.get_or_create_conversation(7, thread_id=222, chat_id=200)

        assert conversation.id == current_chat.id
        assert conversation.chat_id == 200

    await engine.dispose()


@pytest.mark.asyncio
async def test_init_db_creates_chat_thread_active_index(tmp_path) -> None:
    db_path = tmp_path / "telegodex-test.db"
    database = Database(f"sqlite+aiosqlite:///{db_path.as_posix()}")

    try:
        await database.init_db()
        async with database.engine.connect() as conn:
            result = await conn.execute(text("PRAGMA index_list(conversations)"))
            index_names = {row[1] for row in result.fetchall()}

            result = await conn.execute(text("PRAGMA table_info(conversation_messages)"))
            column_names = {row[1] for row in result.fetchall()}

        assert "ix_conversations_user_chat_thread_active" in index_names
        assert {
            "prompt_tokens",
            "completion_tokens",
            "token_count_estimated",
            "tokenizer_name",
        }.issubset(column_names)
    finally:
        await database.close()


@pytest.mark.asyncio
async def test_token_usage_aggregates_by_conversation_user_and_model() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        conversation = Conversation(user_id=7, chat_id=200, thread_id=222, topic_id=222, title="current")
        other_conversation = Conversation(user_id=8, chat_id=300, thread_id=None, topic_id=None, title="other")
        session.add_all([conversation, other_conversation])
        await session.commit()

        manager = ContextManager(session)
        await manager.add_message(
            conversation.id,
            MessageRole.ASSISTANT,
            "exact response",
            provider="openai",
            model="gpt-test",
            tokens_used=15,
            prompt_tokens=10,
            completion_tokens=5,
            token_count_estimated=False,
            tokenizer_name="provider_usage",
        )
        await manager.add_message(
            conversation.id,
            MessageRole.ASSISTANT,
            "estimated response",
            provider="openai",
            model="gpt-test",
            tokens_used=20,
            prompt_tokens=12,
            completion_tokens=8,
            token_count_estimated=True,
            tokenizer_name="heuristic",
        )
        session.add(
            ConversationMessage(
                conversation_id=other_conversation.id,
                role="assistant",
                content="other user",
                provider="openai",
                model="gpt-test",
                tokens_used=100,
                prompt_tokens=60,
                completion_tokens=40,
                token_count_estimated=True,
            )
        )
        await session.commit()

        conversation_usage = await manager.get_conversation_token_usage(conversation.id)
        user_usage = await manager.get_user_token_usage(7)
        breakdown = await manager.get_user_token_usage_by_model(7)

        assert conversation_usage.total_tokens == 35
        assert conversation_usage.prompt_tokens == 22
        assert conversation_usage.completion_tokens == 13
        assert conversation_usage.counted_messages == 2
        assert conversation_usage.estimated_messages == 1
        assert user_usage == conversation_usage
        assert len(breakdown) == 1
        assert breakdown[0].provider == "openai"
        assert breakdown[0].model == "gpt-test"
        assert breakdown[0].total_tokens == 35
        assert breakdown[0].counted_messages == 2

    await engine.dispose()
