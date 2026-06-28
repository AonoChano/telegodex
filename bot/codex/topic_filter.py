"""Telegram filters for Codex-bound forum topics."""

from __future__ import annotations

from typing import Any

from aiogram.filters import BaseFilter
from aiogram.types import Message
from loguru import logger


class IsCodexBoundTopic(BaseFilter):
    """Filter candidate text messages in Telegram forum topics."""

    async def __call__(self, message: Message, context_manager: Any | None = None) -> bool:
        if message.message_thread_id is None:
            logger.debug("IsCodexBoundTopic: message_thread_id is None, skipping")
            return False
        if message.text is None:
            logger.debug("IsCodexBoundTopic: text is None, skipping")
            return False
        return not message.text.strip().startswith("/codex")
