"""Codex thread-session management.

Maps Telegram ``SessionKey`` → Codex ``threadId``, persisted via
``storage.models.Conversation``.
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass, field
from typing import Any

from loguru import logger
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import ProviderSessionData, SessionKey, SessionManager
from extensions.codex.daemon import CodexDaemon
from extensions.codex.jsonrpc import JsonRpcTransport
from storage.models import Conversation

_CODEX_PROVIDER = "codex"


def _get_codex_bucket(conv: Conversation | None) -> ProviderSessionData | None:
    """Extract the Codex bucket from *conv*'s provider_sessions JSON."""
    if conv is None or not conv.provider_sessions:
        return None
    bucket_data = conv.provider_sessions.get(_CODEX_PROVIDER)
    if bucket_data is None:
        return None
    return ProviderSessionData.from_dict(bucket_data)


def _set_codex_bucket(conv: Conversation, bucket: ProviderSessionData) -> None:
    """Write the Codex bucket into *conv*'s provider_sessions JSON."""
    if conv.provider_sessions is None:
        conv.provider_sessions = {}
    conv.provider_sessions[_CODEX_PROVIDER] = bucket.to_dict()


@dataclass
class _SessionState:
    """Runtime state for one active Telegram ↔ Codex session."""

    thread_id: str
    cwd: str | None = None
    active_turn_id: str | None = None
    turn_completed: asyncio.Event = field(default_factory=asyncio.Event)

    # Accumulated text during streaming.
    stream_buffer: str = ""
    stream_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    # Track whether this session was resumed from the database.
    was_resumed: bool = False


def _session_key_filter(session_key: SessionKey):
    """Build a SQLAlchemy filter for *session_key* with backward compatibility.

    Matches new schema (transport + topic_id) or falls back to old schema
    (transport IS NULL, topic_id IS NULL, thread_id matches).
    """
    chat_match = Conversation.chat_id == session_key.chat_id
    new_match = and_(
        chat_match,
        Conversation.transport == session_key.transport,
        Conversation.topic_id == session_key.topic_id,
    )
    old_topic_match = (
        Conversation.thread_id == session_key.topic_id
        if session_key.topic_id is not None
        else Conversation.thread_id.is_(None)
    )
    old_match = and_(
        chat_match,
        Conversation.transport.is_(None),
        Conversation.topic_id.is_(None),
        old_topic_match,
    )
    return or_(new_match, old_match)


class CodexSessionManager(SessionManager):
    """Manages the ``SessionKey → thread_id`` mapping.

    Parameters
    ----------
    daemon:
        The global ``CodexDaemon`` singleton.
    """

    def __init__(self, daemon: CodexDaemon) -> None:
        super().__init__()
        self._daemon = daemon
        self._sessions: dict[SessionKey, _SessionState] = {}
        # thread_id → SessionKey reverse lookup for approval routing
        self._thread_to_session_key: dict[str, SessionKey] = {}
        # thread_id → Telegram forum topic_id (message_thread_id)
        self._thread_to_topic: dict[str, int | None] = {}
        # SessionKey → resume metadata for UX notifications
        self._resume_info: dict[SessionKey, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    def _transport(self) -> JsonRpcTransport:
        """Return the daemon transport, raising if unavailable."""
        transport = self._daemon.transport
        if transport is None:
            raise RuntimeError("Codex daemon transport is not available")
        return transport

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    async def get_or_create_session(
        self,
        db: AsyncSession,
        session_key: SessionKey,
        user_id: int,
        cwd: str | None = None,
    ) -> _SessionState:
        """Return the session for *session_key*, creating one if necessary.

        If *cwd* is ``None`` the persisted cwd (or daemon cwd) is used.
        """
        async with self._lock:
            existing = self._sessions.get(session_key)
            if existing is not None:
                return existing

            # Check database for persisted thread in this chat.
            stmt = select(Conversation).where(
                _session_key_filter(session_key),
                Conversation.is_active.is_(True),
            )
            result = await db.execute(stmt)
            conv = result.scalars().first()

            # Resolve thread_id from provider bucket first, then legacy column.
            bucket = _get_codex_bucket(conv)
            persisted_thread_id = bucket.session_id if bucket else None
            if not persisted_thread_id and conv:
                persisted_thread_id = conv.codex_thread_id

            if persisted_thread_id:
                # Try to resume existing thread.
                logger.info(f"CodexSession: resuming thread {persisted_thread_id} for {session_key}")
                try:
                    resp = await self._transport().send_request(
                        "thread/resume",
                        {"threadId": persisted_thread_id},
                    )
                    thread = resp["thread"]
                    thread_id = thread["id"]
                    session = _SessionState(
                        thread_id=thread_id,
                        cwd=resp.get("cwd", conv.cwd if conv else None),
                        was_resumed=True,
                    )
                    self._resume_info[session_key] = {
                        "thread_id": thread_id,
                        "resumed_at": conv.updated_at.isoformat() if conv and conv.updated_at else None,
                    }
                except Exception as resume_error:
                    # Resume failed (thread not found, expired, etc.)
                    # Fall back to creating a new thread.
                    logger.warning(
                        f"CodexSession: failed to resume thread {persisted_thread_id}: {resume_error}. "
                        f"Creating new thread instead."
                    )
                    persisted_thread_id = None  # Signal to create new thread below

            if not persisted_thread_id:
                # Start new thread.
                effective_cwd = cwd or (conv.cwd if conv else None)
                params: dict[str, Any] = {}
                if effective_cwd:
                    params["cwd"] = effective_cwd

                resp = await self._transport().send_request("thread/start", params)
                thread = resp["thread"]
                thread_id = thread["id"]
                logger.info(f"CodexSession: started new thread {thread_id} for {session_key}")

                # Persist to database.
                if conv is None:
                    conv = Conversation(
                        user_id=user_id,
                        chat_id=session_key.chat_id,
                        transport=session_key.transport,
                        topic_id=session_key.topic_id,
                        thread_id=session_key.topic_id,
                        codex_thread_id=thread_id,
                        codex_thread_path=thread.get("path"),
                        cwd=resp.get("cwd", effective_cwd),
                        is_active=True,
                    )
                    db.add(conv)
                else:
                    conv.codex_thread_id = thread_id
                    conv.codex_thread_path = thread.get("path")
                    conv.cwd = resp.get("cwd", effective_cwd)
                    conv.transport = session_key.transport
                    conv.topic_id = session_key.topic_id
                    conv.thread_id = session_key.topic_id
                    conv.is_active = True

                # Write provider bucket.
                _set_codex_bucket(
                    conv,
                    ProviderSessionData(session_id=thread_id),
                )
                await db.commit()

                self._resume_info.pop(session_key, None)
                session = _SessionState(
                    thread_id=thread_id,
                    cwd=resp.get("cwd", effective_cwd),
                )

            self._thread_to_session_key[thread_id] = session_key
            old_session = self._sessions.get(session_key)
            if old_session is not None:
                self._thread_to_topic.pop(old_session.thread_id, None)
            self._sessions[session_key] = session
            return session

    async def new_session(
        self,
        db: AsyncSession,
        session_key: SessionKey,
        user_id: int,
        cwd: str | None = None,
    ) -> _SessionState:
        """Force-create a new thread, discarding any existing session."""
        async with self._lock:
            old = self._sessions.pop(session_key, None)
            if old is not None:
                self._thread_to_session_key.pop(old.thread_id, None)
                self._thread_to_topic.pop(old.thread_id, None)
                if old.active_turn_id:
                    with contextlib.suppress(Exception):
                        await self._transport().send_request(
                            "turn/interrupt",
                            {"threadId": old.thread_id, "turnId": old.active_turn_id},
                        )

            # Archive any existing active conversation for this chat.
            stmt = select(Conversation).where(
                _session_key_filter(session_key),
                Conversation.is_active.is_(True),
            )
            result = await db.execute(stmt)
            for conv in result.scalars().all():
                conv.is_active = False

            effective_cwd = cwd
            if not effective_cwd:
                # Try to inherit cwd from the most recent conversation.
                stmt = (
                    select(Conversation)
                    .where(
                        Conversation.chat_id == session_key.chat_id,
                    )
                    .order_by(Conversation.updated_at.desc())
                )
                result = await db.execute(stmt)
                recent = result.scalars().first()
                if recent:
                    effective_cwd = recent.cwd

            params: dict[str, Any] = {}
            if effective_cwd:
                params["cwd"] = effective_cwd

            resp = await self._transport().send_request("thread/start", params)
            thread_id = resp["thread"]["id"]
            logger.info(f"CodexSession: started new thread {thread_id} for {session_key}")

            # Persist new conversation.
            conv = Conversation(
                user_id=user_id,
                chat_id=session_key.chat_id,
                transport=session_key.transport,
                topic_id=session_key.topic_id,
                thread_id=session_key.topic_id,
                codex_thread_id=thread_id,
                codex_thread_path=resp["thread"].get("path"),
                cwd=resp.get("cwd", effective_cwd),
                is_active=True,
            )
            db.add(conv)

            # Write provider bucket.
            _set_codex_bucket(
                conv,
                ProviderSessionData(session_id=thread_id),
            )
            await db.commit()

            self._resume_info.pop(session_key, None)
            session = _SessionState(
                thread_id=thread_id,
                cwd=resp.get("cwd", effective_cwd),
            )
            self._thread_to_session_key[thread_id] = session_key
            self._sessions[session_key] = session
            return session

    def get_session(self, session_key: SessionKey) -> _SessionState | None:  # type: ignore[override]
        """Return the session for *session_key* if one exists, or ``None``."""
        return self._sessions.get(session_key)

    def reverse_lookup(self, thread_id: str) -> SessionKey | None:
        """Return the SessionKey for a given Codex thread_id, or ``None``."""
        return self._thread_to_session_key.get(thread_id)

    def set_topic_id(self, thread_id: str, topic_id: int | None) -> None:
        """Map a Codex thread to its Telegram forum topic_id."""
        self._thread_to_topic[thread_id] = topic_id

    def update_session_key(self, old_key: SessionKey, new_key: SessionKey) -> bool:
        """Update the SessionKey for an existing session.

        This is used when a Codex session is created in the main chat (topic_id=None)
        and then moved to a forum topic (topic_id=N).

        Returns True if the session was found and updated, False otherwise.
        """
        session = self._sessions.pop(old_key, None)
        if session is None:
            return False

        # Update the session with the new key
        self._sessions[new_key] = session

        # Update reverse lookup
        self._thread_to_session_key[session.thread_id] = new_key

        # Update resume info if present
        resume_info = self._resume_info.pop(old_key, None)
        if resume_info is not None:
            self._resume_info[new_key] = resume_info

        return True

    def get_topic_id(self, thread_id: str) -> int | None:
        """Return the Telegram topic_id for a Codex thread, or ``None``."""
        return self._thread_to_topic.get(thread_id)

    def is_turn_active(self, session_key: SessionKey) -> bool:
        """Return ``True`` if a turn is currently running for *session_key*."""
        session = self._sessions.get(session_key)
        if session is None:
            return False
        return session.active_turn_id is not None and not session.turn_completed.is_set()

    def active_turn_count(self) -> int:
        """Return the number of currently running turns."""
        return sum(
            1
            for session in self._sessions.values()
            if session.active_turn_id is not None and not session.turn_completed.is_set()
        )

    def get_resume_info(self, session_key: SessionKey) -> dict[str, Any] | None:
        """Return resume metadata for *session_key*, or ``None``."""
        return self._resume_info.get(session_key)

    async def remove_session(self, session_key: SessionKey) -> None:
        """Remove a session from memory (does not delete the Codex thread)."""
        async with self._lock:
            session = self._sessions.pop(session_key, None)
            if session is not None:
                self._thread_to_session_key.pop(session.thread_id, None)
                self._thread_to_topic.pop(session.thread_id, None)
                self._resume_info.pop(session_key, None)

    async def list_threads(
        self,
        db: AsyncSession,
        session_key: SessionKey,
    ) -> list[dict[str, Any]]:
        """Return all persisted conversations for *session_key*'s chat, newest first."""
        stmt = (
            select(Conversation)
            .where(
                Conversation.chat_id == session_key.chat_id,
            )
            .order_by(Conversation.updated_at.desc())
        )
        result = await db.execute(stmt)
        rows = []
        for conv in result.scalars().all():
            rows.append(
                {
                    "id": conv.id,
                    "codex_thread_id": conv.codex_thread_id,
                    "cwd": conv.cwd,
                    "is_active": conv.is_active,
                    "created_at": conv.created_at.isoformat() if conv.created_at else None,
                    "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
                }
            )
        return rows

    async def archive_thread(
        self,
        db: AsyncSession,
        session_key: SessionKey,
    ) -> bool:
        """Archive the active conversation for *session_key*. Returns ``True`` if found."""
        async with self._lock:
            session = self._sessions.pop(session_key, None)
            if session is not None:
                self._thread_to_session_key.pop(session.thread_id, None)
                self._thread_to_topic.pop(session.thread_id, None)
                self._resume_info.pop(session_key, None)

            stmt = select(Conversation).where(
                _session_key_filter(session_key),
                Conversation.is_active.is_(True),
            )
            result = await db.execute(stmt)
            conv = result.scalars().first()
            if conv is None:
                return False
            conv.is_active = False
            await db.commit()
            return True

    async def activate_thread(
        self,
        db: AsyncSession,
        session_key: SessionKey,
        conversation_id: int,
    ) -> bool:
        """Activate a specific conversation and deactivate others for *session_key*."""
        async with self._lock:
            # Deactivate all in this chat.
            stmt = select(Conversation).where(
                _session_key_filter(session_key),
                Conversation.is_active.is_(True),
            )
            result = await db.execute(stmt)
            for conv in result.scalars().all():
                conv.is_active = False

            # Activate target.
            stmt = select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.chat_id == session_key.chat_id,
            )
            result = await db.execute(stmt)
            target_conv = result.scalars().first()
            if target_conv is None:
                await db.commit()
                return False

            target_conv.is_active = True
            await db.commit()

            # Evict in-memory session so next get_or_create loads the switched thread.
            self._sessions.pop(session_key, None)
            self._resume_info.pop(session_key, None)
            return True

    async def set_cwd(
        self,
        db: AsyncSession,
        session_key: SessionKey,
        cwd: str,
    ) -> None:
        """Update cwd for the active conversation and in-memory session."""
        async with self._lock:
            session = self._sessions.get(session_key)
            if session is not None:
                session.cwd = cwd

            stmt = select(Conversation).where(
                _session_key_filter(session_key),
                Conversation.is_active.is_(True),
            )
            result = await db.execute(stmt)
            conv = result.scalars().first()
            if conv is not None:
                conv.cwd = cwd
                await db.commit()

    # ------------------------------------------------------------------
    # Turn management
    # ------------------------------------------------------------------

    async def start_turn(
        self,
        session_key: SessionKey,
        user_input: str,
    ) -> _SessionState:
        """Start a new turn for *session_key* with the given text input.

        Returns the session state; callers should then iterate notifications
        from the daemon transport.
        """
        session = self._sessions.get(session_key)
        if session is None:
            raise RuntimeError(f"No active session for {session_key}")

        # Reset turn state.
        session.turn_completed.clear()
        session.stream_buffer = ""
        session.active_turn_id = None

        resp = await self._transport().send_request(
            "turn/start",
            {
                "threadId": session.thread_id,
                "input": [{"type": "text", "text": user_input}],
            },
        )
        session.active_turn_id = resp["turn"]["id"]
        logger.debug(f"CodexSession: turn {session.active_turn_id} started on thread {session.thread_id}")
        return session

    async def cancel_turn(self, session_key: SessionKey) -> None:
        """Interrupt the active turn for *session_key*."""
        session = self._sessions.get(session_key)
        if session is None or session.active_turn_id is None:
            return

        logger.info(f"CodexSession: interrupting turn {session.active_turn_id} on thread {session.thread_id}")
        try:
            await self._transport().send_request(
                "turn/interrupt",
                {
                    "threadId": session.thread_id,
                    "turnId": session.active_turn_id,
                },
            )
        except Exception as exc:
            logger.warning(f"CodexSession: turn/interrupt failed: {exc}")
        finally:
            session.active_turn_id = None
            session.turn_completed.set()

    async def execute_shell(
        self,
        session_key: SessionKey,
        command: str,
    ) -> None:
        """Execute a shell command inside the session's thread context."""
        session = self._sessions.get(session_key)
        if session is None:
            raise RuntimeError(f"No active session for {session_key}")

        logger.info(f"CodexSession: shell command on thread {session.thread_id}: {command}")
        await self._transport().send_request(
            "thread/shellCommand",
            {
                "threadId": session.thread_id,
                "command": command,
            },
        )

    async def stream_accumulate(
        self,
        session_key: SessionKey,
        delta: str,
    ) -> str:
        """Append *delta* to the session stream buffer and return the full text."""
        session = self._sessions.get(session_key)
        if session is None:
            return delta

        async with session.stream_lock:
            session.stream_buffer += delta
            return session.stream_buffer
