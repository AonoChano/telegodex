"""Codex turn setup helpers for Telegram UI state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger

from bot.codex.turn import CodexTurnActor
from bot.streaming import ReactionTracker
from bot.telegram_draft import DraftStream
from bot.utils.routing import TelegramRoute
from core.orchestrator import Orchestrator
from core.session import SessionKey


@dataclass
class PreparedCodexTurn:
    """Telegram UI objects created before a Codex streaming turn starts."""

    session_key: SessionKey
    topic_id: int | None
    stop_msg: Message | None
    stop_keyboard: InlineKeyboardMarkup
    stream: DraftStream | None
    actor: CodexTurnActor


async def prepare_codex_turn(
    *,
    message: Message,
    route: TelegramRoute,
    orchestrator: Orchestrator,
    bot_token: str,
    toolbar_handler: Any,
    status_edit_interval: float,
    draft_flush_chars: int,
    draft_flush_interval: float,
    stderr_late_grace: float,
    stderr_flush_grace: float,
) -> PreparedCodexTurn | None:
    """Create Telegram status UI, draft stream, and per-turn actor."""
    bot = message.bot
    if bot is None:
        logger.warning("_execute_codex_prompt: bot is None, returning")
        return None

    session_key = SessionKey.from_telegram_message(route.chat_id, route.message_thread_id)
    topic_id = route.message_thread_id

    await bot.send_chat_action(
        chat_id=route.chat_id,
        action="typing",
        message_thread_id=route.message_thread_id,
        business_connection_id=route.business_connection_id,
    )

    stop_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Stop generating",
                    callback_data=f"codex_stop|{session_key.to_string()}",
                )
            ]
        ]
    )
    stop_msg = None
    try:
        stop_msg = await bot.send_message(
            chat_id=route.chat_id,
            text="Codex is working...",
            reply_markup=stop_keyboard,
            message_thread_id=topic_id,
        )
    except Exception as exc:
        logger.debug(f"Codex: failed to send stop button: {exc}")

    try:
        await toolbar_handler.send_reply_keyboard(
            bot,
            session_key=session_key,
            message_thread_id=topic_id,
        )
    except Exception as exc:
        logger.debug(f"Codex: failed to send reply keyboard: {exc}")

    use_draft = message.chat.type == "private" or route.message_thread_id is not None
    stream = (
        DraftStream(
            bot_token=bot_token,
            chat_id=route.chat_id,
            message_thread_id=topic_id,
            direct_messages_topic_id=route.direct_messages_topic_id,
            business_connection_id=route.business_connection_id,
            use_rich=True,
        )
        if use_draft
        else None
    )

    reaction_tracker = None
    if stop_msg is not None:
        reaction_tracker = ReactionTracker(bot, stop_msg.chat.id, stop_msg.message_id)
        try:
            await reaction_tracker.set_state("thinking")
        except Exception as exc:
            logger.debug(f"Codex: failed to set initial reaction: {exc}")

    actor = CodexTurnActor(
        bot=bot,
        route=route,
        session_key=session_key,
        orchestrator=orchestrator,
        stop_msg=stop_msg,
        stop_keyboard=stop_keyboard,
        stream=stream,
        reaction_tracker=reaction_tracker,
        status_edit_interval=status_edit_interval,
        draft_flush_chars=draft_flush_chars,
        draft_flush_interval=draft_flush_interval,
        stderr_late_grace=stderr_late_grace,
        stderr_flush_grace=stderr_flush_grace,
    )
    return PreparedCodexTurn(
        session_key=session_key,
        topic_id=topic_id,
        stop_msg=stop_msg,
        stop_keyboard=stop_keyboard,
        stream=stream,
        actor=actor,
    )
