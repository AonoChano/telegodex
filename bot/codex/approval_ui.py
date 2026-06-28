"""Telegram UI bridge for Codex approval requests."""

from __future__ import annotations

from typing import Any

from aiogram import Bot
from loguru import logger

from core.orchestrator import Orchestrator


class ApprovalUiBridge:
    """Send Codex app-server approval requests to the matching Telegram topic."""

    def __init__(self) -> None:
        self.bot: Bot | None = None
        self.orchestrator: Orchestrator | None = None
        self.db_session_factory: Any = None

    def set_bot(self, bot: Bot | None) -> None:
        self.bot = bot

    def set_db_session_factory(self, factory: Any) -> None:
        self.db_session_factory = factory

    def ensure_orchestrator(self, orchestrator: Orchestrator, db_session_factory: Any = None) -> None:
        """Cache the Orchestrator instance and wire the approval sender once."""
        if self.orchestrator is None:
            self.orchestrator = orchestrator
            orchestrator.set_approval_ui_sender(self.send)
        if db_session_factory is not None:
            self.db_session_factory = db_session_factory

    async def send(self, method: str, params: dict[str, Any]) -> None:
        """Send approval requests to Telegram.

        All early-return paths log a warning instead of failing silently: a
        silent skip causes the turn to auto-deny after the timeout with no
        visible clue.
        """
        if self.bot is None or self.orchestrator is None:
            logger.warning(f"approval UI skipped (no bot/orchestrator wired): method={method}")
            return
        sm = self.orchestrator.session_manager
        if sm is None:
            logger.warning(f"approval UI skipped (no session manager): method={method}")
            return
        thread_id = params.get("threadId", "")
        session_key = sm.reverse_lookup(thread_id)
        if session_key is None:
            session_key = await self._resolve_session_key_from_db(thread_id, sm)
        if session_key is None:
            logger.warning(f"approval UI skipped (thread {thread_id} not resolvable in memory or DB): method={method}")
            return

        approval_id = params.get("approvalId", params.get("itemId", "unknown"))
        text = self._format_approval_text(method, approval_id, params)
        if text is None:
            logger.warning(f"approval UI skipped (unsupported method): method={method}")
            return
        keyboard = self.orchestrator.approval_handler.build_approval_keyboard(approval_id, params)
        topic_id = sm.get_topic_id(thread_id) or session_key.topic_id

        try:
            await self.bot.send_message(
                chat_id=session_key.chat_id,
                text=text,
                reply_markup=keyboard,
                message_thread_id=topic_id,
                parse_mode="Markdown",
            )
        except Exception as exc:
            logger.warning(f"Codex: approval Markdown send failed, retrying as plain text: {exc}")
            try:
                await self.bot.send_message(
                    chat_id=session_key.chat_id,
                    text=text,
                    reply_markup=keyboard,
                    message_thread_id=topic_id,
                )
            except Exception as exc2:
                logger.warning(f"Codex: failed to send approval message to {session_key}: {exc2}")

    async def _resolve_session_key_from_db(self, thread_id: str, session_manager: Any) -> Any:
        if self.db_session_factory is None:
            return None
        try:
            async for db in self.db_session_factory():
                return await session_manager.reverse_lookup_db_fallback(thread_id, db)
        except Exception:
            logger.exception(f"approval UI DB fallback failed for thread={thread_id}")
        return None

    def _format_approval_text(self, method: str, approval_id: str, params: dict[str, Any]) -> str | None:
        if self.orchestrator is None:
            return None
        approval_handler = self.orchestrator.approval_handler
        if method == "item/commandExecution/requestApproval":
            return approval_handler.format_command_approval_markdown(approval_id, params)
        if method == "item/fileChange/requestApproval":
            return approval_handler.format_file_change_approval_markdown(approval_id, params)
        if method == "item/permissions/requestApproval":
            return approval_handler.format_permissions_approval_markdown(approval_id, params)
        return None


approval_ui_bridge = ApprovalUiBridge()
