"""Final delivery helpers for normal chat responses."""

from __future__ import annotations

from aiogram.types import Message
from loguru import logger

from bot.telegram_draft import DraftStream
from bot.utils.markdown import format_markdown_v2
from bot.utils.rich_messages import send_rich_message
from bot.utils.routing import TelegramRoute


async def deliver_chat_response(
    *,
    message: Message,
    route: TelegramRoute,
    bot_token: str,
    stream: DraftStream | None,
    response_text: str,
) -> None:
    """Finalize one normal-chat response through Rich Message with safe fallbacks."""
    sent = False
    try:
        if stream is not None:
            sent = await stream.finalize(response_text)
        else:
            sent = await send_rich_message(
                bot_token=bot_token,
                chat_id=route.chat_id,
                markdown_text=response_text,
                message_thread_id=route.message_thread_id,
                direct_messages_topic_id=route.direct_messages_topic_id,
                business_connection_id=route.business_connection_id,
            )

        if sent:
            logger.info("Rich Message sent successfully")
        else:
            logger.warning("Rich Messages unavailable, falling back to MarkdownV2")
            formatted_content = format_markdown_v2(response_text)
            try:
                await message.answer(
                    formatted_content,
                    parse_mode="MarkdownV2",
                    **route.send_kwargs(),
                )
            except Exception:
                await message.answer(
                    response_text,
                    **route.send_kwargs(),
                )

    except Exception as format_error:
        logger.warning(f"Format failed, falling back to plain text: {format_error}")
        await message.answer(response_text, **route.send_kwargs())
