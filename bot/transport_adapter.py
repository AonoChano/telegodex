"""Telegram TransportAdapter for the MessageBus."""

from __future__ import annotations

from typing import Any

from aiogram import Bot
from loguru import logger

from bot.utils.rich_messages import send_rich_message
from bot.utils.routing import TelegramRoute
from core.bus import Envelope, TransportAdapter


class TelegramTransport(TransportAdapter):
    """Deliver Envelopes to Telegram via Bot API.

    Uses ``sendRichMessage`` as the primary path and falls back to
    ``bot.send_message`` when Rich Messages are unavailable.
    """

    def __init__(self, bot: Bot | None = None) -> None:
        self._bot = bot

    @property
    def transport_name(self) -> str:
        return "telegram"

    def set_bot(self, bot: Bot | None) -> None:
        """Update the bot instance (called after bot startup)."""
        self._bot = bot

    def _bot_token(self) -> str:
        from config import settings

        token = settings.telegram_bot_token
        if hasattr(token, "get_secret_value"):
            token = token.get_secret_value()
        return token

    async def deliver(self, envelope: Envelope) -> bool:
        """Unicast delivery — respects ``reply_to_message_id``."""
        if self._bot is None:
            logger.warning("TelegramTransport: bot instance is not set")
            return False

        try:
            kwargs: dict[str, Any] = {}
            if envelope.thread_id is not None:
                kwargs["message_thread_id"] = envelope.thread_id
            if envelope.reply_to_message_id is not None:
                kwargs["reply_to_message_id"] = envelope.reply_to_message_id

            # Rich message primary
            sent = await send_rich_message(
                bot_token=self._bot_token(),
                chat_id=envelope.chat_id,
                markdown_text=envelope.result_text,
                message_thread_id=envelope.thread_id,
            )
            if sent:
                return True

            # Fallback to plain message
            await self._bot.send_message(
                chat_id=envelope.chat_id,
                text=envelope.result_text,
                **kwargs,
            )
            return True
        except Exception as exc:
            logger.warning(f"TelegramTransport deliver failed: {exc}")
            return False

    async def deliver_broadcast(self, envelope: Envelope) -> bool:
        """Broadcast delivery — sends without ``reply_to_message_id``."""
        if self._bot is None:
            logger.warning("TelegramTransport: bot instance is not set")
            return False

        try:
            kwargs: dict[str, Any] = {}
            if envelope.thread_id is not None:
                kwargs["message_thread_id"] = envelope.thread_id

            sent = await send_rich_message(
                bot_token=self._bot_token(),
                chat_id=envelope.chat_id,
                markdown_text=envelope.result_text,
                message_thread_id=envelope.thread_id,
            )
            if sent:
                return True

            await self._bot.send_message(
                chat_id=envelope.chat_id,
                text=envelope.result_text,
                **kwargs,
            )
            return True
        except Exception as exc:
            logger.warning(f"TelegramTransport deliver_broadcast failed: {exc}")
            return False
