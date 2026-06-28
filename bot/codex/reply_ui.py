"""Telegram reply helpers for Codex UI flows."""

from __future__ import annotations

from typing import Any

from aiogram.types import Message

from bot.telegram_draft import shorten_plain_telegram_text
from bot.utils.routing import TelegramRoute


def codex_send_kwargs(route: TelegramRoute, topic_id: int | None) -> dict[str, Any]:
    """Build send kwargs, adding ``message_thread_id`` when a forum topic exists."""
    kwargs = dict(route.send_kwargs())
    if topic_id is not None:
        kwargs["message_thread_id"] = topic_id
    return kwargs


async def codex_reply(
    message: Message,
    text: str,
    route: TelegramRoute,
    topic_id: int | None,
    **kwargs: Any,
) -> None:
    """Send a plain fallback reply routed to the requested Codex topic."""
    merged = codex_send_kwargs(route, topic_id)
    merged.update(kwargs)
    bot = message.bot
    if bot is None:
        return
    await bot.send_message(
        chat_id=route.chat_id,
        text=shorten_plain_telegram_text(text),
        **merged,
    )
