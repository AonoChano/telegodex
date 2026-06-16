"""Envelope dataclass — unified async message container."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class DeliveryMode(Enum):
    """Message delivery strategy."""

    BROADCAST = auto()
    UNICAST = auto()


class LockMode(Enum):
    """Lock acquisition strategy during submit."""

    NONE = auto()
    SOFT = auto()
    HARD = auto()


class EnvelopeStatus(Enum):
    """Lifecycle status of an envelope."""

    PENDING = auto()
    PROCESSING = auto()
    DELIVERED = auto()
    FAILED = auto()


@dataclass
class Envelope:
    """Unified async message container for the MessageBus.

    Fields
    ------
    origin:
        Transport or subsystem name, e.g. ``"telegram"``.
    chat_id:
        Target chat identifier.
    topic_id:
        Optional forum topic / message thread id.
    prompt:
        Full input prompt (for user-initiated envelopes).
    prompt_preview:
        Truncated preview safe for logging or UI.
    result_text:
        Final output text to deliver.
    status:
        Current lifecycle status.
    is_error:
        Whether *result_text* represents an error.
    delivery:
        Desired delivery mode.
    lock_mode:
        How strictly to lock during processing.
    needs_injection:
        Whether the result should be injected into an active LLM session
        instead of delivered as a standalone message.
    reply_to_message_id:
        Telegram message to reply to (UNICAST path).
    thread_id:
        Telegram ``message_thread_id`` (BROADCAST / UNICAST path).
    envelope_id:
        Unique identifier assigned automatically.
    meta:
        Extension point for arbitrary transport metadata.
    """

    # Identity
    origin: str = ""
    chat_id: int = 0
    topic_id: int | None = None

    # Input
    prompt: str = ""
    prompt_preview: str = ""

    # Output
    result_text: str = ""
    status: EnvelopeStatus = field(default_factory=lambda: EnvelopeStatus.PENDING)
    is_error: bool = False

    # Routing flags
    delivery: DeliveryMode = field(default_factory=lambda: DeliveryMode.UNICAST)
    lock_mode: LockMode = field(default_factory=lambda: LockMode.HARD)
    needs_injection: bool = False

    # Telegram metadata
    reply_to_message_id: int | None = None
    thread_id: int | None = None

    # Internal
    envelope_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    meta: dict[str, Any] = field(default_factory=dict)

    def session_key_tuple(self) -> tuple[int, int | None]:
        """Return the ``(chat_id, topic_id)`` pair used by :class:`LockPool`."""
        return (self.chat_id, self.topic_id)
