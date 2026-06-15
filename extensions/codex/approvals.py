"""Codex approval handler — converts app-server approval requests to Telegram inline buttons.

Each approval request gets a unique ``approval_id`` that maps to an
``asyncio.Event``.  The Telegram callback handler resolves the event with the
user's decision.  A 60-second timeout automatically denies unanswered requests.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from config import settings


@dataclass
class _PendingApproval:
    """Internal tracker for an in-progress approval."""

    request_id: str | int
    event: asyncio.Event = field(default_factory=asyncio.Event)
    decision: str | None = None  # "acceptOnce" | "acceptForSession" | "deny"
    params: dict[str, Any] = field(default_factory=dict)


class ApprovalHandler:
    """Handles app-server approval requests and maps them to Telegram callbacks.

    Parameters
    ----------
    transport:
        The ``JsonRpcTransport`` used to send responses back to the app-server.
    """

    def __init__(self, transport_getter: Any = None) -> None:
        # We store a getter to avoid import cycles with daemon.
        self._transport_getter = transport_getter
        self._pending: dict[str | int, _PendingApproval] = {}
        self._timeout: float = float(settings.codex_approval_timeout)

    async def handle_server_request(
        self,
        method: str,
        params: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Process an incoming server request.

        If it's an approval request, start the timeout and return ``None``
        (the response will be sent later via :meth:`resolve`).

        Returns a result dict for non-approval requests, or ``None`` for
        deferred approval responses.
        """
        if method == "item/commandExecution/requestApproval":
            return await self._handle_command_approval(params)
        elif method == "item/fileChange/requestApproval":
            return await self._handle_file_change_approval(params)
        return None  # Unknown server request → let transport send error

    async def _handle_command_approval(
        self, params: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Handle a command execution approval request.

        Returns ``None`` to defer the response until user interaction.
        """
        approval_id = params.get("approvalId", params.get("itemId", "unknown"))
        command = params.get("command", "unknown command")
        cwd = params.get("cwd", "")

        logger.info(
            f"ApprovalHandler: command approval "
            f"id={approval_id} cmd={command}"
        )

        pending = _PendingApproval(
            request_id=approval_id,
            params=params,
        )
        self._pending[approval_id] = pending

        # Start timeout.
        timeout_task = asyncio.create_task(self._auto_deny_after(approval_id))

        # Wait for user decision (set by Telegram callback).
        try:
            await pending.event.wait()
        finally:
            timeout_task.cancel()
            try:
                await timeout_task
            except asyncio.CancelledError:
                pass

        # Build response.
        decision = pending.decision or "deny"
        del self._pending[approval_id]
        return {"decision": decision}

    async def _handle_file_change_approval(
        self, params: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Handle a file change approval request."""
        approval_id = params.get("approvalId", params.get("itemId", "unknown"))
        path = params.get("path", "unknown file")

        logger.info(
            f"ApprovalHandler: file change approval "
            f"id={approval_id} path={path}"
        )

        pending = _PendingApproval(
            request_id=approval_id,
            params=params,
        )
        self._pending[approval_id] = pending

        timeout_task = asyncio.create_task(self._auto_deny_after(approval_id))

        try:
            await pending.event.wait()
        finally:
            timeout_task.cancel()
            try:
                await timeout_task
            except asyncio.CancelledError:
                pass

        decision = pending.decision or "deny"
        del self._pending[approval_id]
        return {"decision": decision}

    async def resolve(
        self,
        approval_id: str | int,
        decision: str,
    ) -> bool:
        """Resolve a pending approval with a user decision.

        Returns ``True`` if the approval was found, ``False`` if it already
        timed out.
        """
        pending = self._pending.get(approval_id)
        if pending is None:
            logger.warning(
                f"ApprovalHandler: resolve called for unknown/timed-out "
                f"approval {approval_id}"
            )
            return False

        pending.decision = decision
        pending.event.set()
        return True

    async def _auto_deny_after(self, approval_id: str | int) -> None:
        """Auto-deny an approval after the configured timeout."""
        await asyncio.sleep(self._timeout)
        pending = self._pending.pop(approval_id, None)
        if pending is not None and not pending.event.is_set():
            logger.warning(
                f"ApprovalHandler: auto-denying approval {approval_id} "
                f"(timeout {self._timeout}s)"
            )
            pending.decision = "deny"
            pending.event.set()

    # ------------------------------------------------------------------
    # Formatters — build Telegram inline keyboard markup for approval msgs
    # ------------------------------------------------------------------

    @staticmethod
    def format_command_approval_markdown(
        approval_id: str | int,
        params: dict[str, Any],
    ) -> str:
        """Format a command approval as Rich Markdown for a Telegram message."""
        command = params.get("command", "unknown")
        cwd = params.get("cwd", "")
        reason = params.get("reason", "")

        lines = [
            "**Codex wants to execute a command:**",
            "",
            f"```sh\n{command}\n```",
        ]
        if cwd:
            lines.append(f"Working directory: `{cwd}`")
        if reason:
            lines.append(f"Reason: {reason}")

        return "\n".join(lines)

    @staticmethod
    def format_file_change_approval_markdown(
        approval_id: str | int,
        params: dict[str, Any],
    ) -> str:
        """Format a file change approval as Rich Markdown."""
        path = params.get("path", "unknown")
        diff = params.get("diff", "")

        lines = [
            "**Codex wants to modify a file:**",
            "",
            f"Path: `{path}`",
        ]
        if diff:
            lines.append(f"```diff\n{diff}\n```")

        return "\n".join(lines)

    @staticmethod
    def build_approval_keyboard(approval_id: str | int) -> dict[str, Any]:
        """Build an inline keyboard with Approve/Deny buttons."""
        return {
            "inline_keyboard": [
                [
                    {
                        "text": "Approve",
                        "callback_data": f"codex_approval:{approval_id}:acceptOnce",
                    },
                    {
                        "text": "Approve (Session)",
                        "callback_data": f"codex_approval:{approval_id}:acceptForSession",
                    },
                    {
                        "text": "Deny",
                        "callback_data": f"codex_approval:{approval_id}:deny",
                    },
                ]
            ]
        }