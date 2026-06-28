"""Codex turn state and Telegram status callbacks."""

from __future__ import annotations

import asyncio
import html
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, Message
from loguru import logger

from bot.codex import formatting as fmt
from bot.streaming import ReactionTracker
from bot.telegram_draft import DraftStream
from bot.utils.routing import TelegramRoute
from core.orchestrator import Orchestrator, StreamingCallbacks
from core.session import SessionKey


@dataclass
class CodexTurnActor:
    """Own per-turn status edits, stream previews, and runtime detail capture."""

    bot: Bot
    route: TelegramRoute
    session_key: SessionKey
    orchestrator: Orchestrator
    stop_msg: Message | None
    stop_keyboard: InlineKeyboardMarkup
    stream: DraftStream | None
    reaction_tracker: ReactionTracker | None
    status_edit_interval: float = 2.0
    draft_flush_chars: int = 200
    draft_flush_interval: float = 1.2
    stderr_late_grace: float = 2.0
    stderr_flush_grace: float = 0.25
    clock: Callable[[], float] = time.monotonic
    latest_rendered: str = ""
    runtime_detail_collector: list[str] = field(default_factory=list)
    turn_problem_seen: bool = False
    last_problem_status: str = ""
    last_problem_at: float = 0.0
    last_flush_len: int = 0
    last_flush_at: float = 0.0
    last_status_edit: float = 0.0
    last_status_text: str = "Codex is working..."

    async def edit_status(self, text: str, *, force: bool = False, parse_mode: str | None = None) -> None:
        """Edit the live stop/status message, with throttling for noisy updates."""
        if self.stop_msg is None:
            return
        safe_text = fmt.trim_status_text(text)
        now = self.clock()
        if not force and safe_text == self.last_status_text:
            return
        if not force and now - self.last_status_edit < self.status_edit_interval:
            return
        self.last_status_edit = now
        self.last_status_text = safe_text
        try:
            await self.bot.edit_message_text(
                chat_id=self.stop_msg.chat.id,
                message_id=self.stop_msg.message_id,
                text=safe_text,
                reply_markup=self.stop_keyboard,
                parse_mode=parse_mode,
            )
        except Exception as exc:
            logger.debug(f"Codex: failed to edit status message: {exc}")

    def build_callbacks(self) -> StreamingCallbacks:
        return StreamingCallbacks(
            on_text_delta=self.on_text_delta,
            on_reasoning_delta=self.on_reasoning_delta,
            on_command_output_delta=self.on_command_output_delta,
            on_item_started=self.on_item_started,
            on_turn_completed=self.on_turn_completed,
            on_codex_error=self.on_codex_error,
            on_error=self.on_error,
            on_render_update=self.on_render_update,
        )

    async def on_daemon_stderr(self, text: str) -> None:
        if not fmt.is_codex_retry_status_line(text):
            return
        can_show_live = self._single_active_turn()
        can_attach_to_recent_error = self._problem_is_recent()
        if not can_show_live and not can_attach_to_recent_error:
            logger.debug(f"Codex: stderr status kept in logs because it cannot be safely attributed: {text}")
            return
        # Preserve the raw line so the final message can echo it back verbatim
        # instead of the generic "Unknown error" from turn/completed.
        fmt.append_unique_runtime_detail(self.runtime_detail_collector, text)
        if can_attach_to_recent_error:
            await self.edit_problem_status_with_runtime_detail()
        else:
            await self.edit_status(f"Codex connection issue. Retrying...\n{text}", force=True)

    async def prepare_final_text(self, final_text: str) -> str:
        """Attach collected runtime details to the final Telegram message."""
        if self.turn_problem_seen:
            await asyncio.sleep(self.stderr_flush_grace)
        stderr_block = fmt.format_collected_stderr(self.runtime_detail_collector)
        final_text = fmt.clean_codex_error_text(final_text, stderr_block)
        return fmt.append_codex_stderr_detail(final_text, stderr_block)

    def _single_active_turn(self) -> bool:
        sm = self.orchestrator.session_manager
        if sm is None:
            return False
        active_count = getattr(sm, "active_turn_count", lambda: 0)()
        return active_count == 1 and sm.is_turn_active(self.session_key)

    def _problem_is_recent(self) -> bool:
        return self.turn_problem_seen and (self.clock() - self.last_problem_at) <= self.stderr_late_grace

    async def edit_problem_status_with_runtime_detail(self) -> None:
        stderr_block = fmt.format_collected_stderr(self.runtime_detail_collector)
        status_text = self.last_problem_status or "Codex error.\nUnknown error"
        if stderr_block:
            status_text += f"\n\nCodex runtime detail:\n{stderr_block}"
        await self.edit_status(status_text, force=True)

    async def push_render_update(self, rendered: str, *, force: bool = False) -> None:
        if not rendered:
            return
        self.latest_rendered = rendered
        if self.stream is None:
            return
        now = self.clock()
        should_flush = (
            force
            or self.last_flush_at == 0.0
            or abs(len(rendered) - self.last_flush_len) >= self.draft_flush_chars
            or now - self.last_flush_at >= self.draft_flush_interval
        )
        if not should_flush:
            return
        if await self.stream.push(rendered):
            self.last_flush_len = len(rendered)
            self.last_flush_at = now

    async def on_render_update(self, rendered: str) -> None:
        await self.push_render_update(rendered)

    async def on_text_delta(self, delta: str, accumulated: str) -> None:
        if self.reaction_tracker is not None:
            await self.reaction_tracker.set_state("editing")
        await self.edit_status("Codex is writing a response...")
        if accumulated and accumulated != self.latest_rendered:
            await self.push_render_update(accumulated)

    async def on_reasoning_delta(self, delta: str, accumulated: str) -> None:
        if self.reaction_tracker is not None:
            await self.reaction_tracker.on_codex_event("item/reasoning/summaryTextDelta")
        preview = fmt.trim_status_text(accumulated, 360)
        if preview:
            await self.edit_status(
                f"Codex is thinking...\n<i>{html.escape(preview)}</i>",
                parse_mode="HTML",
            )
        else:
            await self.edit_status("Codex is thinking...")

    async def on_command_output_delta(self, delta: str, accumulated: str) -> None:
        if self.reaction_tracker is not None:
            await self.reaction_tracker.on_codex_event("item/commandExecution/outputDelta")
        await self.edit_status(
            fmt.format_command_status(output_preview=accumulated),
            parse_mode="HTML",
        )

    async def on_item_started(self, item_type: str, item: dict[str, Any]) -> None:
        if self.reaction_tracker is not None:
            await self.reaction_tracker.on_codex_event("item/started", item_type)
        if item_type == "commandExecution":
            command = item.get("command", "")
            await self.edit_status(
                fmt.format_command_status(command=command),
                force=True,
                parse_mode="HTML",
            )
        elif item_type == "reasoning":
            await self.edit_status("Codex is thinking...", force=True)

    async def on_turn_completed(self, turn: dict[str, Any], final_text: str) -> None:
        status = turn.get("status", "")
        if self.reaction_tracker is not None:
            if status == "failed":
                await self.reaction_tracker.clear()
            else:
                await self.reaction_tracker.set_state("done")
        if status == "failed":
            error = turn.get("error", {})
            error_msg = error.get("message", "Unknown error")
            additional_details = error.get("additionalDetails") or error.get("additional_details")
            fmt.append_unique_runtime_detail(self.runtime_detail_collector, additional_details)
            self.turn_problem_seen = True
            if fmt.is_generic_unknown_error_line(f"Error: {error_msg}") and (
                self.last_problem_status or self.runtime_detail_collector
            ):
                if not self.last_problem_status:
                    self.last_problem_status = "Codex failed."
                self.last_problem_at = self.clock()
                await self.edit_problem_status_with_runtime_detail()
                return
            self.last_problem_status = f"Codex failed.\n{error_msg}"
            self.last_problem_at = self.clock()
            await self.edit_problem_status_with_runtime_detail()
        elif status == "interrupted":
            await self.edit_status("Codex was interrupted.", force=True)
        else:
            await self.edit_status("Codex completed.", force=True)

    async def on_codex_error(self, error_message: str, additional_details: str | None, will_retry: bool) -> None:
        fmt.append_unique_runtime_detail(self.runtime_detail_collector, additional_details)
        if will_retry:
            await self.edit_status(fmt.format_codex_retry_status(error_message, additional_details), force=True)
            return
        if self.reaction_tracker is not None:
            await self.reaction_tracker.clear()
        self.turn_problem_seen = True
        self.last_problem_status = f"Codex error.\n{error_message}"
        self.last_problem_at = self.clock()
        await self.edit_problem_status_with_runtime_detail()

    async def on_error(self, error_message: str) -> None:
        if self.reaction_tracker is not None:
            await self.reaction_tracker.clear()
        self.turn_problem_seen = True
        self.last_problem_status = f"Codex error.\n{error_message}"
        self.last_problem_at = self.clock()
        await self.edit_problem_status_with_runtime_detail()
