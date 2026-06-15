"""Telegram routing helpers for threaded private chats and direct messages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiogram.types import Message


def _extra(message: Message, key: str) -> Any:
    extra = getattr(message, "model_extra", None) or {}
    return extra.get(key)


def _field(obj: Any, key: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


@dataclass(frozen=True)
class TelegramRoute:
    """Fields needed to send a response into the same Telegram surface."""

    chat_id: int | str
    message_thread_id: int | None = None
    direct_messages_topic_id: int | None = None
    business_connection_id: str | None = None

    @classmethod
    def from_message(cls, message: Message) -> "TelegramRoute":
        direct_topic = getattr(message, "direct_messages_topic", None)
        if direct_topic is None:
            direct_topic = _extra(message, "direct_messages_topic")

        direct_topic_id = _field(direct_topic, "topic_id")
        return cls(
            chat_id=message.chat.id,
            message_thread_id=getattr(message, "message_thread_id", None),
            direct_messages_topic_id=direct_topic_id,
            business_connection_id=getattr(message, "business_connection_id", None),
        )

    @property
    def storage_thread_id(self) -> int | None:
        """Return the conversation key used by the current storage schema."""
        if self.message_thread_id is not None:
            return self.message_thread_id
        if self.direct_messages_topic_id is not None:
            return -self.direct_messages_topic_id
        return None

    def send_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        if self.business_connection_id is not None:
            kwargs["business_connection_id"] = self.business_connection_id
        if self.direct_messages_topic_id is not None:
            kwargs["direct_messages_topic_id"] = self.direct_messages_topic_id
        # NOTE: message_thread_id is intentionally excluded here.
        # aiogram's Message.answer() and Message.reply() auto-include it
        # for topic messages. Passing it again causes duplicate keyword error.
        return kwargs

    def draft_thread_id(self) -> int | None:
        """Draft APIs accept message_thread_id only."""
        return self.message_thread_id
