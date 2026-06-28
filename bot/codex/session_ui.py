"""Telegram UI helpers for Codex session topics."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.types import Message
from loguru import logger

from bot.codex.topic_state import bind_codex_thread_to_topic as default_bind_codex_thread_to_topic
from bot.utils.routing import TelegramRoute
from core.orchestrator import Orchestrator
from core.session import SessionKey

BindCodexThreadToTopic = Callable[..., Awaitable[None]]


async def handle_codex_new(
    message: Message,
    route: TelegramRoute,
    context_manager: Any,
    orchestrator: Orchestrator,
    session_key: SessionKey,
    user_id: int,
    *,
    bind_codex_thread_to_topic: BindCodexThreadToTopic = default_bind_codex_thread_to_topic,
) -> None:
    """Create a fresh Codex session and bind it to a new forum topic."""
    bot = message.bot
    if bot is None:
        await message.answer(
            "Bot instance unavailable.",
            **route.send_kwargs(),
        )
        return

    try:
        info = await orchestrator.codex_new_session(session_key, context_manager.session, user_id)
        thread_id = info["thread_id"]
        cwd = info.get("cwd", "default")

        short_thread = thread_id[:8]
        topic_name = f"Codex: {short_thread}"
        forum_topic = await bot.create_forum_topic(
            chat_id=route.chat_id,
            name=topic_name,
        )
        topic_id = forum_topic.message_thread_id

        session_manager = orchestrator.session_manager
        if session_manager is not None:
            session_manager.set_topic_id(thread_id, topic_id)
            old_key = SessionKey.from_telegram_message(route.chat_id, None)
            new_key = SessionKey.from_telegram_message(route.chat_id, topic_id)
            updated = session_manager.update_session_key(old_key, new_key)
            logger.info(
                f"handle_codex_new: updated session key mapping: old={old_key}, new={new_key}, success={updated}"
            )

        await bind_codex_thread_to_topic(
            context_manager=context_manager,
            chat_id=route.chat_id,
            topic_id=topic_id,
            thread_id=thread_id,
            user_id=user_id,
            cwd=cwd,
        )

        await bot.send_message(
            chat_id=route.chat_id,
            message_thread_id=topic_id,
            text=(
                "**New Codex Session**\n\n"
                f"Thread: `{thread_id}`\n"
                f"CWD: `{cwd}`\n\n"
                "Send your prompts here directly (no `/codex` prefix needed)."
            ),
            parse_mode="Markdown",
        )

        await message.answer(
            f"✅ Created new Codex session in topic **{topic_name}**.",
            parse_mode="Markdown",
            **route.send_kwargs(),
        )
    except Exception as exc:
        logger.exception("Failed to create Codex session with forum topic")
        await message.answer(
            f"❌ Failed to create new session: {exc}",
            **route.send_kwargs(),
        )
