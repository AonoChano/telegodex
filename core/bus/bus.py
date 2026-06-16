"""MessageBus — central async message bus with lock-aware delivery."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from loguru import logger

from core.bus.envelope import DeliveryMode, Envelope, EnvelopeStatus, LockMode
from core.session import LockPool


class TransportAdapter(Protocol):
    """Protocol for transport-specific delivery implementations."""

    @property
    def transport_name(self) -> str:
        """Human-readable transport identifier."""
        ...

    async def deliver(self, envelope: Envelope) -> bool:
        """Deliver a **unicast** envelope. Returns ``True`` on success."""
        ...

    async def deliver_broadcast(self, envelope: Envelope) -> bool:
        """Deliver a **broadcast** envelope. Returns ``True`` on success."""
        ...


class SessionInjector(Protocol):
    """Protocol for injecting background results into active LLM sessions."""

    async def can_inject(self, chat_id: int, topic_id: int | None = None) -> bool:
        """Return whether an active session exists that can accept injection."""
        ...

    async def inject(self, envelope: Envelope) -> bool:
        """Inject *envelope* into the active session. Returns ``True`` on success."""
        ...


async def _maybe_await(
    fn: Callable[..., Any] | None, *args: Any
) -> None:
    """Call a sync or async callback, suppressing exceptions."""
    if fn is None:
        return
    try:
        result = fn(*args)
        if inspect.isawaitable(result):
            await result
    except Exception:
        pass


class MessageBus:
    """Central message bus.

    Submit flow::

        assign ID → optional audit → acquire lock → optional injection
        → pre_deliver hook → deliver (with cascade fallback)

    Delivery modes
    --------------
    - **BROADCAST** → ``deliver_broadcast``; cascades to ``deliver`` on failure.
    - **UNICAST**   → ``deliver``; cascades to ``deliver_broadcast`` on failure.
    """

    def __init__(
        self,
        lock_pool: LockPool,
        transport_adapters: dict[str, TransportAdapter] | None = None,
        session_injector: SessionInjector | None = None,
        *,
        audit_callback: Callable[[Envelope], Awaitable[None] | None] | None = None,
        pre_deliver_hook: Callable[[Envelope], Awaitable[None] | None] | None = None,
    ) -> None:
        self._lock_pool = lock_pool
        self._transports: dict[str, TransportAdapter] = transport_adapters or {}
        self._session_injector = session_injector
        self._audit_callback = audit_callback
        self._pre_deliver_hook = pre_deliver_hook

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_transport(self, name: str, adapter: TransportAdapter) -> None:
        """Register a transport adapter."""
        self._transports[name] = adapter

    def set_session_injector(self, injector: SessionInjector | None) -> None:
        """Set or replace the session injector."""
        self._session_injector = injector

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def submit(self, envelope: Envelope) -> Envelope:
        """Submit *envelope* for processing and delivery.

        The envelope is mutated in-place:
        - ``envelope_id`` is generated if absent.
        - ``status`` is updated to ``DELIVERED`` or ``FAILED``.
        """
        if not envelope.envelope_id:
            from uuid import uuid4

            envelope.envelope_id = str(uuid4())
        envelope.status = EnvelopeStatus.PROCESSING

        # Optional audit
        await _maybe_await(self._audit_callback, envelope)

        lock = self._lock_pool.get_lock(envelope.chat_id, envelope.topic_id)

        if envelope.lock_mode == LockMode.NONE:
            await self._process(envelope)
        else:
            async with lock:
                await self._process(envelope)

        return envelope

    # ------------------------------------------------------------------
    # Internal flow
    # ------------------------------------------------------------------

    async def _process(self, envelope: Envelope) -> None:
        """Process: optional injection → transport delivery."""
        delivered = False

        # 1) Try session injection if requested
        if envelope.needs_injection and self._session_injector is not None:
            try:
                if await self._session_injector.can_inject(
                    envelope.chat_id, envelope.topic_id
                ):
                    delivered = await self._session_injector.inject(envelope)
            except Exception as exc:
                logger.warning(f"MessageBus: injection failed for {envelope.envelope_id}: {exc}")

        # 2) Transport delivery if injection did not happen
        if not delivered:
            delivered = await self._deliver(envelope)

        envelope.status = (
            EnvelopeStatus.DELIVERED if delivered else EnvelopeStatus.FAILED
        )

    async def _deliver(self, envelope: Envelope) -> bool:
        """Deliver via transport with cascade fallback."""
        await _maybe_await(self._pre_deliver_hook, envelope)

        transport = self._transports.get(envelope.origin)
        if transport is None:
            logger.warning(
                f"MessageBus: no transport adapter for origin '{envelope.origin}'"
            )
            return False

        # Primary attempt based on requested mode
        if envelope.delivery == DeliveryMode.BROADCAST:
            success = await transport.deliver_broadcast(envelope)
            if not success:
                logger.debug(
                    f"MessageBus: BROADCAST failed for {envelope.envelope_id}, "
                    "cascading to UNICAST"
                )
                success = await transport.deliver(envelope)
        else:
            success = await transport.deliver(envelope)
            if not success:
                logger.debug(
                    f"MessageBus: UNICAST failed for {envelope.envelope_id}, "
                    "cascading to BROADCAST"
                )
                success = await transport.deliver_broadcast(envelope)

        return success
