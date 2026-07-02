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
        {"availableDecisions": ["accept", "acceptForSession", "decline", "cancel"]},
    )

    callback_data = _keyboard_callback_data(markup)
    assert len(callback_data) == 4
    assert all(data.startswith("codex_approval:") for data in callback_data)
    assert all(len(data.encode("utf-8")) <= 64 for data in callback_data)
    assert all(long_approval_id not in data for data in callback_data)


def test_approval_keyboard_supports_object_decisions() -> None:
    handler = ApprovalHandler()
    object_decision = {
        "acceptWithExecpolicyAmendment": {
            "execpolicy_amendment": ["read-only-safe-command"],
        },
    }

    markup = handler.build_approval_keyboard(
        "approval-object",
        {"availableDecisions": [object_decision, "decline"]},
    )

    labels = [button.text for row in markup.inline_keyboard for button in row]
    assert labels == ["Approve matching commands", "Deny"]
    token = markup.inline_keyboard[0][0].callback_data.split(":", 1)[1]
    assert handler.resolve_callback_token(token) == ("approval-object", object_decision)


@pytest.mark.asyncio
async def test_command_approval_invokes_pending_hook_after_registration() -> None:
    handler = ApprovalHandler()
    handler._timeout = 0
    seen: list[str | int] = []

    async def on_pending(approval_id: str | int, params: dict) -> None:
        assert approval_id in handler._pending
        assert params["command"] == "Get-Date -Format o"
        seen.append(approval_id)

    result = await handler.handle_server_request(
        "item/commandExecution/requestApproval",
        {
            "approvalId": "approval-pending",
            "command": "Get-Date -Format o",
        },
        on_pending,
    )

    assert seen == ["approval-pending"]
    assert result == {"decision": "decline"}


@pytest.mark.asyncio
async def test_permissions_approval_accept_grants_requested_permissions_turn_scope() -> None:
    handler = ApprovalHandler()
    seen: list[str | int] = []
    params = {
        "itemId": "perm-1",
        "cwd": "C:/repo",
        "environmentId": "local",
        "reason": "Need workspace write",
        "permissions": {
            "network": {"enabled": True},
            "fileSystem": {
                "read": ["C:/repo"],
                "write": ["C:/repo/out"],
            },
        },
    }

    async def on_pending(approval_id: str | int, pending_params: dict) -> None:
        assert approval_id in handler._pending
        assert pending_params is params
        seen.append(approval_id)
        await handler.resolve(approval_id, "accept")

    result = await handler.handle_server_request(
        "item/permissions/requestApproval",
        params,
        on_pending,
    )

    assert seen == ["perm-1"]
    assert result == {
        "permissions": {
            "network": {"enabled": True},
            "fileSystem": {
                "read": ["C:/repo"],
                "write": ["C:/repo/out"],
            },
        },
        "scope": "turn",
    }


@pytest.mark.asyncio
async def test_permissions_approval_accept_for_session_sets_session_scope() -> None:
    handler = ApprovalHandler()
    params = {
        "itemId": "perm-session",
        "permissions": {"network": {"enabled": True}},
    }

    async def on_pending(approval_id: str | int, _params: dict) -> None:
        await handler.resolve(approval_id, "acceptForSession")

    result = await handler.handle_server_request(
        "item/permissions/requestApproval",
        params,
        on_pending,
    )

    assert result == {
        "permissions": {"network": {"enabled": True}},
        "scope": "session",
    }


@pytest.mark.asyncio
async def test_permissions_approval_auto_deny_returns_empty_turn_scope() -> None:
    handler = ApprovalHandler()
    handler._timeout = 0

    result = await handler.handle_server_request(
        "item/permissions/requestApproval",
        {
            "itemId": "perm-timeout",
            "permissions": {"network": {"enabled": True}},
        },
    )

    assert result == {"permissions": {}, "scope": "turn"}


def test_format_permissions_approval_markdown_describes_request() -> None:
    handler = ApprovalHandler()

    text = handler.format_permissions_approval_markdown(
        "perm-format",
        {
            "cwd": "C:/repo",
            "environmentId": "local",
            "reason": "Need workspace write",
            "permissions": {
                "network": {"enabled": True},
                "fileSystem": {"write": ["C:/repo/out"]},
            },
        },
    )

    assert "additional permissions" in text
    assert "Need workspace write" in text
    assert "C:/repo/out" in text
    assert "Network access: enabled" in text


@pytest.mark.asyncio
async def test_codex_approval_callback_resolves_token_via_orchestrator() -> None:
    handler = ApprovalHandler()
    markup = handler.build_approval_keyboard(
        "approval-1",
        {"availableDecisions": ["acceptForSession"]},
    )
    callback_data = _keyboard_callback_data(markup)[0]
    message = SimpleNamespace(
        text="Approve this",
        caption=None,
        edit_text=AsyncMock(),
        delete=AsyncMock(),
    )
    callback = SimpleNamespace(
        from_user=None,
        data=callback_data,
        message=message,
        answer=AsyncMock(),
    )
    orchestrator = SimpleNamespace(approval_handler=handler)
    resolve = AsyncMock(return_value=True)
    handler.resolve = resolve  # type: ignore[method-assign]

    await handle_codex_approval(callback, orchestrator)

    resolve.assert_awaited_once_with("approval-1", "acceptForSession")
    message.delete.assert_awaited_once()
    message.edit_text.assert_not_awaited()
    callback.answer.assert_awaited_once_with("Approved (Session)")


@pytest.mark.asyncio
async def test_codex_approval_callback_resolves_object_decision() -> None:
    handler = ApprovalHandler()
    object_decision = {
        "acceptWithExecpolicyAmendment": {
            "execpolicy_amendment": ["Get-Date"],
        },
    }
    markup = handler.build_approval_keyboard(
        "approval-object-callback",
        {"availableDecisions": [object_decision]},
    )
    callback_data = _keyboard_callback_data(markup)[0]
    message = SimpleNamespace(
        text="Approve matching commands",
        caption=None,
        edit_text=AsyncMock(),
        delete=AsyncMock(),
    )
    callback = SimpleNamespace(
        from_user=None,
        data=callback_data,
        message=message,
        answer=AsyncMock(),
    )
    orchestrator = SimpleNamespace(approval_handler=handler)
    resolve = AsyncMock(return_value=True)
    handler.resolve = resolve  # type: ignore[method-assign]

    await handle_codex_approval(callback, orchestrator)

    resolve.assert_awaited_once_with("approval-object-callback", object_decision)
    message.delete.assert_awaited_once()
    message.edit_text.assert_not_awaited()
    callback.answer.assert_awaited_once_with("Approved matching commands")


@pytest.mark.asyncio
async def test_codex_approval_callback_compacts_message_when_delete_fails() -> None:
    handler = ApprovalHandler()
    markup = handler.build_approval_keyboard(
        "approval-delete-fallback",
        {"availableDecisions": ["accept"]},
    )
    callback_data = _keyboard_callback_data(markup)[0]
    message = SimpleNamespace(
        text="Approve this",
        caption=None,
        edit_text=AsyncMock(),
        delete=AsyncMock(side_effect=RuntimeError("delete failed")),
    )
    callback = SimpleNamespace(
        from_user=None,
        data=callback_data,
        message=message,
        answer=AsyncMock(),
    )
    orchestrator = SimpleNamespace(approval_handler=handler)
    resolve = AsyncMock(return_value=True)
    handler.resolve = resolve  # type: ignore[method-assign]

    await handle_codex_approval(callback, orchestrator)

    resolve.assert_awaited_once_with("approval-delete-fallback", "accept")
    message.delete.assert_awaited_once()
    message.edit_text.assert_awaited_once_with(
        "Codex approval handled: Approved",
        reply_markup=None,
    )
    callback.answer.assert_awaited_once_with("Approved")


@pytest.mark.asyncio
async def test_codex_approval_callback_rejects_unknown_token() -> None:
    callback = SimpleNamespace(
        from_user=None,
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

    assert result == {"decision": "decline"}
    assert "approval-timeout" not in handler._pending
