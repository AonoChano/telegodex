from __future__ import annotations

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from storage.context_manager import ContextManager
from storage.models import Base, Conversation, Database


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

        assert "ix_conversations_user_chat_thread_active" in index_names
    finally:
        await database.close()
