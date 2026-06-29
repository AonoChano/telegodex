"""Codex turn finalization helpers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import Bot
from aiogram.types import Message
from loguru import logger

from bot.telegram_draft import DraftStream
from bot.utils.rich_messages import send_rich_message
from bot.utils.routing import TelegramRoute
from core.session import SessionKey

CodexReply = Callable[[Message, str, TelegramRoute, int | None], Awaitable[None]]
SendRichMessage = Callable[..., Awaitable[bool]]


async def persist_final_output(
    *,
    bot: Bot,
    bot_token: str,
    message: Message,
    route: TelegramRoute,
    topic_id: int | None,
    final_text: str,
    stream: DraftStream | None,
    stop_msg: Message | None,
    codex_reply: CodexReply,
    send_rich_message_func: SendRichMessage = send_rich_message,
) -> Message | None:
    """Persist final Codex output and delete the live status message on success."""
    if stream is not None:
        success = await stream.finalize(final_text)
    else:
        success = await send_rich_message_func(
            bot_token=bot_token,
            chat_id=route.chat_id,
            markdown_text=final_text,
            message_thread_id=topic_id,
            direct_messages_topic_id=route.direct_messages_topic_id,
            business_connection_id=route.business_connection_id,
        )
    if not success:
        await codex_reply(message, final_text, route, topic_id)
        return stop_msg

    if stop_msg is None:
        return None

    try:
        await bot.delete_message(
            chat_id=stop_msg.chat.id,
            message_id=stop_msg.message_id,
        )
        return None
    except Exception as exc:
        logger.debug(f"Codex: failed to delete status message after finalize: {exc}")
        return stop_msg


async def cleanup_turn(
    *,
    bot: Bot,
    toolbar_handler: Any,
    session_key: SessionKey,
    topic_id: int | None,
    stop_msg: Message | None,
) -> None:
    """Remove transient Telegram UI created for an active Codex turn."""
    if stop_msg is not None:
        try:
            await bot.delete_message(
                chat_id=stop_msg.chat.id,
                message_id=stop_msg.message_id,
            )
        except Exception as exc:
            logger.debug(f"Codex: failed to delete stop button: {exc}")

    try:
        await toolbar_handler.remove_reply_keyboard(bot, session_key, message_thread_id=topic_id)
    except Exception as exc:
        logger.debug(f"Codex: failed to remove reply keyboard: {exc}")
