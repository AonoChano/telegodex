"""Codex thread-session management.

Maps Telegram ``chat_id`` → Codex ``threadId``, persisted via
``storage.models.Conversation``.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from extensions.codex.daemon import CodexDaemon
from storage.models import Conversation


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


class CodexSessionManager:
    """Manages the ``chat_id → thread_id`` mapping.

    Parameters
    ----------
    daemon:
        The global ``CodexDaemon`` singleton.
    """

    def __init__(self, daemon: CodexDaemon) -> None:
        self._daemon = daemon
        # chat_id (int | str) → _SessionState
        self._sessions: dict[int | str, _SessionState] = {}
        # thread_id → chat_id reverse lookup for approval routing
        self._thread_to_chat: dict[str, int | str] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    async def get_or_create_session(
        self,
        db: AsyncSession,
        chat_id: int | str,
        user_id: int,
        cwd: str | None = None,
    ) -> _SessionState:
        """Return the session for *chat_id*, creating one if necessary.

        If *cwd* is ``None`` the daemon's current working directory is used.
        """
        async with self._lock:
            existing = self._sessions.get(chat_id)
            if existing is not None:
                return existing

            # Check database for persisted thread.
            stmt = select(Conversation).where(
                Conversation.user_id == user_id,
                Conversation.is_active == True,
            )
            result = await db.execute(stmt)
            conv = result.scalars().first()

            if conv and conv.codex_thread_id:
                # Resume existing thread.
                logger.info(
                    f"CodexSession: resuming thread {conv.codex_thread_id} "
                    f"for chat_id={chat_id}"
                )
                resp = await self._daemon.transport.send_request(
                    "thread/resume",
                    {"threadId": conv.codex_thread_id},
                )
                thread = resp["thread"]
                thread_id = thread["id"]
                session = _SessionState(
                    thread_id=thread_id,
                    cwd=resp.get("cwd", cwd),
                )
            else:
                # Start new thread.
                params: dict[str, Any] = {}
                if cwd:
                    params["cwd"] = cwd

                resp = await self._daemon.transport.send_request(
                    "thread/start", params
                )
                thread = resp["thread"]
                thread_id = thread["id"]
                logger.info(
                    f"CodexSession: started new thread {thread_id} "
                    f"for chat_id={chat_id}"
                )

                # Persist to database.
                if conv is None:
                    conv = Conversation(
                        user_id=user_id,
                        codex_thread_id=thread_id,
                        codex_thread_path=thread.get("path"),
                        is_active=True,
                    )
                    db.add(conv)
                else:
                    conv.codex_thread_id = thread_id
                    conv.codex_thread_path = thread.get("path")
                    conv.is_active = True
                await db.commit()

                session = _SessionState(
                    thread_id=thread_id,
                    cwd=resp.get("cwd", cwd),
                )

            self._thread_to_chat[thread_id] = chat_id
            self._sessions[chat_id] = session
            return session

    async def new_session(
        self,
        chat_id: int | str,
        cwd: str | None = None,
    ) -> _SessionState:
        """Force-create a new thread, discarding any existing session."""
        async with self._lock:
            old = self._sessions.pop(chat_id, None)
            if old is not None and old.active_turn_id:
                try:
                    await self._daemon.transport.send_request(
                        "turn/interrupt",
                        {"threadId": old.thread_id, "turnId": old.active_turn_id},
                    )
                except Exception:
                    pass

            params: dict[str, Any] = {}
            if cwd:
                params["cwd"] = cwd

            resp = await self._daemon.transport.send_request(
                "thread/start", params
            )
            thread_id = resp["thread"]["id"]
            logger.info(
                f"CodexSession: started new thread {thread_id} for chat_id={chat_id}"
            )

            session = _SessionState(
                thread_id=thread_id,
                cwd=resp.get("cwd", cwd),
            )
            self._thread_to_chat[thread_id] = chat_id
            self._sessions[chat_id] = session
            return session

    def get_session(self, chat_id: int | str) -> _SessionState | None:
        """Return the session for *chat_id* if one exists, or ``None``."""
        return self._sessions.get(chat_id)

    def reverse_lookup(self, thread_id: str) -> int | str | None:
        """Return the chat_id for a given Codex thread_id, or ``None``."""
        return self._thread_to_chat.get(thread_id)

    async def remove_session(self, chat_id: int | str) -> None:
        """Remove a session from memory (does not delete the Codex thread)."""
        async with self._lock:
            session = self._sessions.pop(chat_id, None)
            if session is not None:
                self._thread_to_chat.pop(session.thread_id, None)

    # ------------------------------------------------------------------
    # Turn management
    # ------------------------------------------------------------------

    async def start_turn(
        self,
        chat_id: int | str,
        user_input: str,
    ) -> _SessionState:
        """Start a new turn for *chat_id* with the given text input.

        Returns the session state; callers should then iterate notifications
        from the daemon transport.
        """
        session = self._sessions.get(chat_id)
        if session is None:
            raise RuntimeError(f"No active session for chat_id={chat_id}")

        # Reset turn state.
        session.turn_completed.clear()
        session.stream_buffer = ""
        session.active_turn_id = None

        resp = await self._daemon.transport.send_request(
            "turn/start",
            {
                "threadId": session.thread_id,
                "input": [{"type": "text", "text": user_input}],
            },
        )
        session.active_turn_id = resp["turn"]["id"]
        logger.debug(
            f"CodexSession: turn {session.active_turn_id} started "
            f"on thread {session.thread_id}"
        )
        return session

    async def cancel_turn(self, chat_id: int | str) -> None:
        """Interrupt the active turn for *chat_id*."""
        session = self._sessions.get(chat_id)
        if session is None or session.active_turn_id is None:
            return

        logger.info(
            f"CodexSession: interrupting turn {session.active_turn_id} "
            f"on thread {session.thread_id}"
        )
        try:
            await self._daemon.transport.send_request(
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
        chat_id: int | str,
        command: str,
    ) -> None:
        """Execute a shell command inside the session's thread context."""
        session = self._sessions.get(chat_id)
        if session is None:
            raise RuntimeError(f"No active session for chat_id={chat_id}")

        logger.info(
            f"CodexSession: shell command on thread {session.thread_id}: {command}"
        )
        await self._daemon.transport.send_request(
            "thread/shellCommand",
            {
                "threadId": session.thread_id,
                "command": command,
            },
        )

    async def stream_accumulate(
        self,
        chat_id: int | str,
        delta: str,
    ) -> str:
        """Append *delta* to the session stream buffer and return the full text."""
        session = self._sessions.get(chat_id)
        if session is None:
            return delta

        async with session.stream_lock:
            session.stream_buffer += delta
            return session.stream_buffer