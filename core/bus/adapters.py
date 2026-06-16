"""Adapter functions for building Envelopes from various sources."""

from __future__ import annotations

from core.bus.envelope import DeliveryMode, Envelope, EnvelopeStatus, LockMode


def from_background_result(
    *,
    chat_id: int,
    result_text: str,
    topic_id: int | None = None,
    origin: str = "telegram",
    prompt_preview: str = "",
    is_error: bool = False,
    delivery: DeliveryMode = DeliveryMode.BROADCAST,
    lock_mode: LockMode = LockMode.HARD,
    needs_injection: bool = True,
    reply_to_message_id: int | None = None,
    thread_id: int | None = None,
) -> Envelope:
    """Build an Envelope from a background task result.

    Defaults to **BROADCAST** with injection enabled so that active LLM
    sessions can absorb the result inline.
    """
    return Envelope(
        origin=origin,
        chat_id=chat_id,
        topic_id=topic_id,
        prompt_preview=prompt_preview,
        result_text=result_text,
        status=EnvelopeStatus.PENDING,
        is_error=is_error,
        delivery=delivery,
        lock_mode=lock_mode,
        needs_injection=needs_injection,
        reply_to_message_id=reply_to_message_id,
        thread_id=thread_id,
    )


def from_cron_result(
    *,
    chat_id: int,
    result_text: str,
    topic_id: int | None = None,
    origin: str = "telegram",
    prompt_preview: str = "",
    is_error: bool = False,
    delivery: DeliveryMode = DeliveryMode.BROADCAST,
    lock_mode: LockMode = LockMode.SOFT,
    needs_injection: bool = False,
    reply_to_message_id: int | None = None,
    thread_id: int | None = None,
) -> Envelope:
    """Build an Envelope from a scheduled / cron task result.

    Defaults to **BROADCAST** with **SOFT** locking and injection disabled,
    since cron results are typically independent notifications.
    """
    return Envelope(
        origin=origin,
        chat_id=chat_id,
        topic_id=topic_id,
        prompt_preview=prompt_preview,
        result_text=result_text,
        status=EnvelopeStatus.PENDING,
        is_error=is_error,
        delivery=delivery,
        lock_mode=lock_mode,
        needs_injection=needs_injection,
        reply_to_message_id=reply_to_message_id,
        thread_id=thread_id,
    )


def from_task_result(
    *,
    chat_id: int,
    result_text: str,
    topic_id: int | None = None,
    origin: str = "telegram",
    prompt_preview: str = "",
    is_error: bool = False,
    delivery: DeliveryMode = DeliveryMode.UNICAST,
    lock_mode: LockMode = LockMode.HARD,
    needs_injection: bool = True,
    reply_to_message_id: int | None = None,
    thread_id: int | None = None,
) -> Envelope:
    """Build an Envelope from a generic task result.

    Defaults to **UNICAST** with injection enabled, suitable for
    targeted follow-ups to a specific conversation.
    """
    return Envelope(
        origin=origin,
        chat_id=chat_id,
        topic_id=topic_id,
        prompt_preview=prompt_preview,
        result_text=result_text,
        status=EnvelopeStatus.PENDING,
        is_error=is_error,
        delivery=delivery,
        lock_mode=lock_mode,
        needs_injection=needs_injection,
        reply_to_message_id=reply_to_message_id,
        thread_id=thread_id,
    )


def from_user_message(
    *,
    chat_id: int,
    prompt: str,
    topic_id: int | None = None,
    origin: str = "telegram",
    delivery: DeliveryMode = DeliveryMode.UNICAST,
    lock_mode: LockMode = LockMode.HARD,
    needs_injection: bool = False,
    reply_to_message_id: int | None = None,
    thread_id: int | None = None,
) -> Envelope:
    """Build an Envelope from an incoming user message.

    Defaults to **UNICAST** with injection disabled because user messages
    are normally handled by the orchestrator rather than injected.
    """
    preview = prompt[:200] + "..." if len(prompt) > 200 else prompt
    return Envelope(
        origin=origin,
        chat_id=chat_id,
        topic_id=topic_id,
        prompt=prompt,
        prompt_preview=preview,
        result_text="",
        status=EnvelopeStatus.PENDING,
        is_error=False,
        delivery=delivery,
        lock_mode=lock_mode,
        needs_injection=needs_injection,
        reply_to_message_id=reply_to_message_id,
        thread_id=thread_id,
    )
