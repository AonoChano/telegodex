"""Unit tests for Codex approval callback routing."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.handlers.callbacks import handle_codex_approval
from extensions.codex.approvals import ApprovalHandler


def _keyboard_callback_data(markup) -> list[str]:
    return [button.callback_data for row in markup.inline_keyboard for button in row]


def test_approval_keyboard_uses_telegram_safe_callback_tokens() -> None:
    handler = ApprovalHandler()
    long_approval_id = "approval-" + ("x" * 120)

    markup = handler.build_approval_keyboard(
        long_approval_id,
        {"availableDecisions": ["Accept", "AcceptForSession", "Decline", "Cancel"]},
    )

    callback_data = _keyboard_callback_data(markup)
    assert len(callback_data) == 4
    assert all(data.startswith("codex_approval:") for data in callback_data)
    assert all(len(data.encode("utf-8")) <= 64 for data in callback_data)
    assert all(long_approval_id not in data for data in callback_data)


@pytest.mark.asyncio
async def test_codex_approval_callback_resolves_token_via_orchestrator() -> None:
    handler = ApprovalHandler()
    markup = handler.build_approval_keyboard(
        "approval-1",
        {"availableDecisions": ["AcceptForSession"]},
    )
    callback_data = _keyboard_callback_data(markup)[0]
    message = SimpleNamespace(
        text="Approve this",
        caption=None,
        edit_text=AsyncMock(),
    )
    callback = SimpleNamespace(
        data=callback_data,
        message=message,
        answer=AsyncMock(),
    )
    orchestrator = SimpleNamespace(approval_handler=handler)
    resolve = AsyncMock(return_value=True)
    handler.resolve = resolve  # type: ignore[method-assign]

    await handle_codex_approval(callback, orchestrator)

    resolve.assert_awaited_once_with("approval-1", "AcceptForSession")
    message.edit_text.assert_awaited_once()
    callback.answer.assert_awaited_once_with("Approved (Session)")


@pytest.mark.asyncio
async def test_codex_approval_callback_rejects_unknown_token() -> None:
    callback = SimpleNamespace(
        data="codex_approval:missing",
        answer=AsyncMock(),
    )
    orchestrator = SimpleNamespace(approval_handler=MagicMock())
    orchestrator.approval_handler.resolve_callback_token.return_value = None

    await handle_codex_approval(callback, orchestrator)

    callback.answer.assert_awaited_once_with("Approval already timed out", show_alert=True)


@pytest.mark.asyncio
async def test_command_approval_auto_deny_does_not_drop_pending_before_waiter_returns() -> None:
    handler = ApprovalHandler()
    handler._timeout = 0

    result = await handler._handle_command_approval(
        {
            "approvalId": "approval-timeout",
            "command": "pytest",
        }
    )

    assert result == {"decision": "Decline"}
    assert "approval-timeout" not in handler._pending
