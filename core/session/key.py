from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SessionKey:
    """Unique identifier for a transport session.

    Fields
    ------
    transport:
        Transport name, e.g. ``"telegram"``.
    chat_id:
        The chat identifier within the transport.
    topic_id:
        Optional forum topic / message thread id.
    """

    transport: str
    chat_id: int
    topic_id: int | None = None

    def to_string(self) -> str:
        """Serialize to ``transport:chat_id`` or ``transport:chat_id:topic_id``."""
        if self.topic_id is not None:
            return f"{self.transport}:{self.chat_id}:{self.topic_id}"
        return f"{self.transport}:{self.chat_id}"

    @classmethod
    def from_string(cls, s: str) -> SessionKey:
        """Deserialize with backward compatibility for old flat keys.

        Supported formats:
        - ``123`` → old flat ``chat_id``
        - ``123:456`` → old ``chat_id:topic_id``
        - ``telegram:123`` → new format without topic
        - ``telegram:123:456`` → new format with topic
        """
        parts = s.split(":")
        if len(parts) == 1:
            return cls(transport="telegram", chat_id=int(parts[0]))
        elif len(parts) == 2:
            if parts[0] in ("telegram",):
                return cls(transport=parts[0], chat_id=int(parts[1]))
            return cls(transport="telegram", chat_id=int(parts[0]), topic_id=int(parts[1]))
        elif len(parts) == 3:
            return cls(transport=parts[0], chat_id=int(parts[1]), topic_id=int(parts[2]))
        raise ValueError(f"Invalid SessionKey string: {s}")

    @classmethod
    def from_telegram_message(
        cls, chat_id: int | str, message_thread_id: int | None = None
    ) -> SessionKey:
        """Build a SessionKey from a Telegram message context."""
        return cls(transport="telegram", chat_id=int(chat_id), topic_id=message_thread_id)
