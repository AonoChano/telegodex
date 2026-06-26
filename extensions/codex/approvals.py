"""Codex approval handler — converts app-server approval requests to Telegram inline buttons.

Each approval request gets a unique ``approval_id`` that maps to an
``asyncio.Event``.  The Telegram callback handler resolves the event with the
user's decision.  A 60-second timeout automatically denies unanswered requests.
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import json
import secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from loguru import logger

from config import settings


@dataclass
class _PendingApproval:
    """Internal tracker for an in-progress approval."""

    request_id: str | int
    event: asyncio.Event = field(default_factory=asyncio.Event)
    decision: Any | None = None
    params: dict[str, Any] = field(default_factory=dict)
    response_mode: str = "decision"


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
        # Cache of items by item_id for looking up diffs during approval.
        self._item_cache: dict[str, dict[str, Any]] = {}
        self._callback_tokens: dict[str, tuple[str | int, Any]] = {}
        self._approval_callback_tokens: dict[str | int, set[str]] = {}

    async def handle_server_request(
        self,
        method: str,
        params: dict[str, Any],
        on_pending: Callable[[str | int, dict[str, Any]], Any] | None = None,
    ) -> dict[str, Any] | None:
        """Process an incoming server request.

        If it's an approval request, start the timeout and return ``None``
        (the response will be sent later via :meth:`resolve`).

        Returns a result dict for non-approval requests, or ``None`` for
        deferred approval responses.
        """
        if method == "item/commandExecution/requestApproval":
            return await self._handle_command_approval(params, on_pending)
        elif method == "item/fileChange/requestApproval":
            return await self._handle_file_change_approval(params, on_pending)
        elif method == "item/permissions/requestApproval":
            return await self._handle_permissions_approval(params, on_pending)
        return None  # Unknown server request → let transport send error

    async def _handle_command_approval(
        self,
        params: dict[str, Any],
        on_pending: Callable[[str | int, dict[str, Any]], Any] | None = None,
    ) -> dict[str, Any] | None:
        """Handle a command execution approval request.

        Returns ``None`` to defer the response until user interaction.
        """
        approval_id = params.get("approvalId", params.get("itemId", "unknown"))
        command = params.get("command", "unknown command")

        logger.info(f"ApprovalHandler: command approval id={approval_id} cmd={command}")

        pending = _PendingApproval(
            request_id=approval_id,
            params=params,
        )
        self._pending[approval_id] = pending
        return await self._wait_for_decision(approval_id, pending, on_pending)

    async def _handle_file_change_approval(
        self,
        params: dict[str, Any],
        on_pending: Callable[[str | int, dict[str, Any]], Any] | None = None,
    ) -> dict[str, Any] | None:
        """Handle a file change approval request."""
        approval_id = params.get("approvalId", params.get("itemId", "unknown"))
        path = params.get("path", "unknown file")

        logger.info(f"ApprovalHandler: file change approval id={approval_id} path={path}")

        pending = _PendingApproval(
            request_id=approval_id,
            params=params,
        )
        self._pending[approval_id] = pending
        return await self._wait_for_decision(approval_id, pending, on_pending)

    async def _handle_permissions_approval(
        self,
        params: dict[str, Any],
        on_pending: Callable[[str | int, dict[str, Any]], Any] | None = None,
    ) -> dict[str, Any] | None:
        """Handle an additional-permissions approval request."""
        approval_id = params.get("approvalId", params.get("itemId", "unknown"))
        cwd = params.get("cwd", "")

        logger.info(f"ApprovalHandler: permissions approval id={approval_id} cwd={cwd}")

        pending = _PendingApproval(
            request_id=approval_id,
            params=params,
            response_mode="permissions",
        )
        self._pending[approval_id] = pending
        return await self._wait_for_decision(approval_id, pending, on_pending)

    async def _wait_for_decision(
        self,
        approval_id: str | int,
        pending: _PendingApproval,
        on_pending: Callable[[str | int, dict[str, Any]], Any] | None = None,
    ) -> dict[str, Any]:
        if on_pending is not None:
            result = on_pending(approval_id, pending.params)
            if inspect.isawaitable(result):
                await result

        # Start timeout after the UI hook gets a chance to render the prompt.
        timeout_task = asyncio.create_task(self._auto_deny_after(approval_id))

        try:
            await pending.event.wait()
        finally:
            timeout_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await timeout_task

        decision = pending.decision or "decline"
        del self._pending[approval_id]
        self._clear_callback_tokens(approval_id)
        if pending.response_mode == "permissions":
            return self._permissions_response_from_decision(decision, pending.params)
        return {"decision": decision}

    def cache_item(self, item_id: str, item: dict[str, Any]) -> None:
        """Cache an item for later lookup during approval formatting."""
        self._item_cache[item_id] = item

    async def resolve(
        self,
        approval_id: str | int,
        decision: Any,
    ) -> bool:
        """Resolve a pending approval with a user decision.

        Returns ``True`` if the approval was found, ``False`` if it already
        timed out.
        """
        pending = self._pending.get(approval_id)
        if pending is None:
            logger.warning(f"ApprovalHandler: resolve called for unknown/timed-out approval {approval_id}")
            return False

        pending.decision = decision
        pending.event.set()
        return True

    def resolve_callback_token(self, token: str) -> tuple[str | int, Any] | None:
        """Return ``(approval_id, decision)`` for a Telegram callback token."""
        return self._callback_tokens.pop(token, None)

    async def _auto_deny_after(self, approval_id: str | int) -> None:
        """Auto-deny an approval after the configured timeout."""
        await asyncio.sleep(self._timeout)
        pending = self._pending.get(approval_id)
        if pending is not None and not pending.event.is_set():
            logger.warning(f"ApprovalHandler: auto-denying approval {approval_id} (timeout {self._timeout}s)")
            pending.decision = "decline"
            pending.event.set()

    def _new_callback_token(self, approval_id: str | int, decision: Any) -> str:
        """Create a short callback token within Telegram's 64-byte limit."""
        while True:
            token = secrets.token_urlsafe(8)
            if token not in self._callback_tokens:
                break
        self._callback_tokens[token] = (approval_id, decision)
        self._approval_callback_tokens.setdefault(approval_id, set()).add(token)
        return token

    @staticmethod
    def describe_decision(decision: Any) -> str:
        """Return a short user-facing label for a Codex approval decision."""
        if isinstance(decision, str):
            return {
                "accept": "Approved",
                "acceptForSession": "Approved (Session)",
                "decline": "Denied",
                "cancel": "Cancelled",
            }.get(decision, decision)
        if isinstance(decision, dict):
            key = next(iter(decision), "approval")
            if key == "acceptWithExecpolicyAmendment":
                return "Approved matching commands"
            if key == "applyNetworkPolicyAmendment":
                amendment = decision.get(key, {}).get("network_policy_amendment", {})
                action = amendment.get("action", "apply")
                host = amendment.get("host")
                if host:
                    return f"Network rule: {action} {host}"
                return f"Network rule: {action}"
            return key
        return str(decision)

    @classmethod
    def _permissions_response_from_decision(
        cls,
        decision: Any,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        if isinstance(decision, dict) and "permissions" in decision:
            scope = decision.get("scope", "turn")
            if scope not in {"turn", "session"}:
                scope = "turn"
            response = {
                "permissions": cls._normalise_permission_profile(decision.get("permissions")),
                "scope": scope,
            }
            if "strictAutoReview" in decision:
                response["strictAutoReview"] = bool(decision["strictAutoReview"])
            return response

        if decision == "accept":
            return {
                "permissions": cls._requested_permissions(params),
                "scope": "turn",
            }
        if decision == "acceptForSession":
            return {
                "permissions": cls._requested_permissions(params),
                "scope": "session",
            }
        return cls._empty_permissions_response()

    @classmethod
    def _requested_permissions(cls, params: dict[str, Any]) -> dict[str, Any]:
        return cls._normalise_permission_profile(params.get("permissions"))

    @classmethod
    def _normalise_permission_profile(cls, permissions: Any) -> dict[str, Any]:
        if not isinstance(permissions, dict):
            return {}

        granted: dict[str, Any] = {}
        for key in ("network", "fileSystem"):
            value = permissions.get(key)
            if value is None:
                continue
            cleaned = cls._clone_without_none(value)
            if cleaned != {}:
                granted[key] = cleaned
        return granted

    @classmethod
    def _clone_without_none(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: cls._clone_without_none(item) for key, item in value.items() if item is not None}
        if isinstance(value, list):
            return [cls._clone_without_none(item) for item in value]
        return value

    @staticmethod
    def _empty_permissions_response() -> dict[str, Any]:
        return {"permissions": {}, "scope": "turn"}

    @staticmethod
    def _normalise_available_decisions(available: Any) -> list[Any]:
        if not available:
            return ["accept", "acceptForSession", "decline"]
        if not isinstance(available, list):
            return ["accept", "acceptForSession", "decline"]
        return [decision for decision in available if decision]

    @staticmethod
    def _button_for_decision(decision: Any) -> tuple[str, Any, bool]:
        """Return ``(label, callback_value, is_decline_family)``."""
        if isinstance(decision, str):
            key = decision.lower()
            decision_map = {
                "accept": ("Approve", "accept", False),
                "acceptforsession": ("Approve for session", "acceptForSession", False),
                "decline": ("Deny", "decline", True),
                "cancel": ("Cancel turn", "cancel", True),
            }
            return decision_map.get(key, (decision.title(), decision, key in {"decline", "cancel"}))

        if isinstance(decision, dict):
            key = next(iter(decision), "")
            if key == "acceptWithExecpolicyAmendment":
                return ("Approve matching commands", decision, False)
            if key == "applyNetworkPolicyAmendment":
                amendment = decision.get(key, {}).get("network_policy_amendment", {})
                action = str(amendment.get("action", "apply")).lower()
                host = amendment.get("host")
                label = f"{action.title()} network rule"
                if host:
                    label = f"{action.title()} {host}"
                return (label, decision, action == "deny")
            return (key or "Decision", decision, "decline" in key.lower() or "deny" in key.lower())

        label = str(decision)
        return (label, decision, False)

    def _clear_callback_tokens(self, approval_id: str | int) -> None:
        tokens = self._approval_callback_tokens.pop(approval_id, set())
        for token in tokens:
            self._callback_tokens.pop(token, None)

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

    def format_file_change_approval_markdown(
        self,
        approval_id: str | int,
        params: dict[str, Any],
    ) -> str:
        """Format a file change approval as Rich Markdown."""
        item_id = params.get("itemId", "")
        item = self._item_cache.get(item_id, {})
        changes = item.get("changes", [])

        lines = ["**Codex wants to modify a file:**", ""]
        if changes:
            for change in changes:
                path = change.get("path", "unknown")
                diff = change.get("diff", "")
                lines.append(f"Path: `{path}`")
                if diff:
                    lines.append(f"```diff\n{diff}\n```")
                lines.append("")
        else:
            lines.append("_No diff available (file change details not cached)._")

        return "\n".join(lines)

    def format_permissions_approval_markdown(
        self,
        approval_id: str | int,
        params: dict[str, Any],
    ) -> str:
        """Format an additional-permissions approval as Rich Markdown."""
        cwd = params.get("cwd", "")
        environment_id = params.get("environmentId")
        reason = params.get("reason", "")
        permissions = self._normalise_permission_profile(params.get("permissions"))

        lines = ["**Codex wants additional permissions:**", ""]
        if cwd:
            lines.append(f"Working directory: `{cwd}`")
        if environment_id:
            lines.append(f"Environment: `{environment_id}`")
        if reason:
            lines.append(f"Reason: {reason}")

        summary = self._format_permission_summary(permissions)
        if summary:
            if len(lines) > 2:
                lines.append("")
            lines.extend(summary)

        lines.extend(
            [
                "",
                "Requested permission payload:",
                f"```json\n{json.dumps(permissions, ensure_ascii=False, indent=2)}\n```",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _format_permission_summary(permissions: dict[str, Any]) -> list[str]:
        lines: list[str] = []
        network = permissions.get("network")
        if isinstance(network, dict):
            enabled = network.get("enabled")
            if enabled is True:
                lines.append("Network access: enabled")
            elif enabled is False:
                lines.append("Network access: disabled")
            else:
                lines.append("Network access: requested")

        file_system = permissions.get("fileSystem")
        if isinstance(file_system, dict):
            read_roots = file_system.get("read") or []
            write_roots = file_system.get("write") or []
            entries = file_system.get("entries") or []
            for root in read_roots:
                lines.append(f"File read: `{root}`")
            for root in write_roots:
                lines.append(f"File write: `{root}`")
            if entries:
                lines.append(f"File system entries: {len(entries)} requested")
        return lines

    def build_approval_keyboard(
        self,
        approval_id: str | int,
        params: dict[str, Any] | None = None,
    ) -> InlineKeyboardMarkup:
        """Build an inline keyboard with Approve/Deny buttons.

        Adapts to ``availableDecisions`` from the app-server when provided.
        Command approvals may include object decisions such as
        ``acceptWithExecpolicyAmendment`` and ``applyNetworkPolicyAmendment``;
        callback tokens store the original decision payload so the JSON-RPC
        response matches the Codex protocol.

        Buttons are stacked one per row so labels stay full-width.
        """
        params = params or {}
        available = self._normalise_available_decisions(params.get("availableDecisions"))

        approve_buttons: list[InlineKeyboardButton] = []
        decline_buttons: list[InlineKeyboardButton] = []

        for decision in available:
            label, callback_value, is_decline_family = self._button_for_decision(decision)
            token = self._new_callback_token(approval_id, callback_value)
            btn = InlineKeyboardButton(
                text=label,
                callback_data=f"codex_approval:{token}",
            )
            if is_decline_family:
                decline_buttons.append(btn)
            else:
                approve_buttons.append(btn)

        # One button per row so Telegram never truncates labels.
        rows: list[list[InlineKeyboardButton]] = [[btn] for btn in approve_buttons] + [[btn] for btn in decline_buttons]

        return InlineKeyboardMarkup(inline_keyboard=rows)
