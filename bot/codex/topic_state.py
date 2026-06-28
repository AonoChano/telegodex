"""Storage helpers for Codex-bound Telegram topics."""

from __future__ import annotations

from typing import Any

from loguru import logger
from sqlalchemy import or_, select

from core.session import ProviderSessionData
from storage.models import Conversation

CODEX_TOPIC_BOUND = "bound"
CODEX_TOPIC_RECOVERABLE = "recoverable"
CODEX_TOPIC_NOT_CODEX = "not_codex"


async def bind_codex_thread_to_topic(
    *,
    context_manager: Any,
    chat_id: int | str,
    topic_id: int,
    thread_id: str,
    user_id: int,
    cwd: str | None = None,
) -> None:
    """Persist that a Codex app-server thread belongs to a Telegram topic."""
    db = context_manager.session
    result = await db.execute(
        select(Conversation).where(
            Conversation.chat_id == int(chat_id),
            Conversation.codex_thread_id == thread_id,
        )
    )
    conv = result.scalars().first()
    if conv is None:
        logger.warning(
            "Codex topic bind: missing conversation for chat_id={} thread_id={}; creating binding row",
            chat_id,
            thread_id,
        )
        conv = Conversation(
            user_id=user_id,
            chat_id=int(chat_id),
            codex_thread_id=thread_id,
            cwd=None if cwd == "default" else cwd,
        )
        db.add(conv)

    conv.user_id = user_id
    conv.chat_id = int(chat_id)
    conv.transport = "telegram"
    conv.topic_id = topic_id
    conv.thread_id = topic_id
    conv.codex_thread_id = thread_id
    if cwd is not None and cwd != "default":
        conv.cwd = cwd
    conv.is_active = True
    provider_sessions = dict(conv.provider_sessions or {})
    provider_sessions["codex"] = ProviderSessionData(session_id=thread_id).to_dict()
    conv.provider_sessions = provider_sessions
    await db.commit()


async def is_codex_bound_topic(
    thread_id: int,
    context_manager: Any,
    chat_id: int | str | None = None,
) -> bool:
    """Check whether a Telegram thread is bound to a Codex session."""
    return await codex_topic_state(thread_id, context_manager, chat_id=chat_id) == CODEX_TOPIC_BOUND


async def codex_topic_state(
    thread_id: int,
    context_manager: Any,
    chat_id: int | str | None = None,
) -> str:
    """Classify a Telegram topic for Codex routing."""
    db = context_manager.session
    scope = [
        or_(
            Conversation.thread_id == thread_id,
            Conversation.topic_id == thread_id,
        ),
        Conversation.codex_thread_id.isnot(None),
    ]
    if chat_id is not None:
        scope.append(Conversation.chat_id == int(chat_id))
    stmt = select(Conversation).where(
        *scope,
        Conversation.is_active.is_(True),
    )
    result = await db.execute(stmt)
    conv = result.scalars().first()
    if conv is not None:
        logger.debug(f"Codex topic check: chat_id={chat_id}, thread_id={thread_id}, state=bound, conv=id={conv.id}")
        return CODEX_TOPIC_BOUND

    stmt = select(Conversation).where(*scope)
    result = await db.execute(stmt)
    conv = result.scalars().first()
    if conv is not None:
        logger.debug(
            f"Codex topic check: chat_id={chat_id}, thread_id={thread_id}, state=recoverable, conv=id={conv.id}"
        )
        return CODEX_TOPIC_RECOVERABLE

    logger.debug(f"Codex topic check: chat_id={chat_id}, thread_id={thread_id}, state=not_codex")
    return CODEX_TOPIC_NOT_CODEX
