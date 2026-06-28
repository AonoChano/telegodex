"""Unit tests for the Telegram Codex approval UI bridge."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.codex.approval_ui import ApprovalUiBridge
from core.session import SessionKey
from extensions.codex.approvals import ApprovalHandler


def _orchestrator(session_key: SessionKey | None = None) -> SimpleNamespace:
    session_manager = SimpleNamespace(
        reverse_lookup=MagicMock(return_value=session_key),
        get_topic_id=MagicMock(return_value=session_key.topic_id if session_key else None),
    )
    return SimpleNamespace(
        session_manager=session_manager,
        approval_handler=ApprovalHandler(),
        set_approval_ui_sender=MagicMock(),
    )


@pytest.mark.asyncio
async def test_bridge_wires_orchestrator_sender_once() -> None:
    bridge = ApprovalUiBridge()
    orchestrator = _orchestrator()

    bridge.ensure_orchestrator(orchestrator)
    bridge.ensure_orchestrator(orchestrator)

    orchestrator.set_approval_ui_sender.assert_called_once_with(bridge.send)


@pytest.mark.asyncio
async def test_bridge_sends_command_approval_inline_keyboard_to_topic() -> None:
    bot = AsyncMock()
    session_key = SessionKey.from_telegram_message(100, 222)
    bridge = ApprovalUiBridge()
    bridge.set_bot(bot)
    bridge.ensure_orchestrator(_orchestrator(session_key))
    object_decision = {
        "acceptWithExecpolicyAmendment": {
            "execpolicy_amendment": ["Get-Date"],
        },
    }

    await bridge.send(
        "item/commandExecution/requestApproval",
        {
            "threadId": "thread-abcdef",
            "approvalId": "approval-telegram",
            "command": "Get-Date -Format o",
            "availableDecisions": [object_decision, "decline"],
        },
    )

    bot.send_message.assert_awaited_once()
    _, kwargs = bot.send_message.await_args
    assert kwargs["chat_id"] == 100
    assert kwargs["message_thread_id"] == 222
    assert kwargs["reply_markup"].inline_keyboard[0][0].text == "Approve matching commands"
    assert kwargs["reply_markup"].inline_keyboard[1][0].text == "Deny"


@pytest.mark.asyncio
async def test_bridge_sends_permissions_prompt_to_topic() -> None:
    bot = AsyncMock()
    session_key = SessionKey.from_telegram_message(100, 222)
    bridge = ApprovalUiBridge()
    bridge.set_bot(bot)
    bridge.ensure_orchestrator(_orchestrator(session_key))

    await bridge.send(
        "item/permissions/requestApproval",
        {
            "threadId": "thread-abcdef",
            "itemId": "perm-telegram",
            "cwd": "C:/repo",
            "reason": "Need workspace write",
            "permissions": {
                "network": {"enabled": True},
                "fileSystem": {"write": ["C:/repo/out"]},
            },
        },
    )

    bot.send_message.assert_awaited_once()
    _, kwargs = bot.send_message.await_args
    assert kwargs["chat_id"] == 100
    assert kwargs["message_thread_id"] == 222
    assert kwargs["parse_mode"] == "Markdown"
    assert "additional permissions" in kwargs["text"]
    assert "Need workspace write" in kwargs["text"]
    assert "C:/repo/out" in kwargs["text"]
    assert kwargs["reply_markup"].inline_keyboard[0][0].text == "Approve"
    assert kwargs["reply_markup"].inline_keyboard[1][0].text == "Approve for session"
    assert kwargs["reply_markup"].inline_keyboard[2][0].text == "Deny"


@pytest.mark.asyncio
async def test_bridge_falls_back_to_plain_text_when_markdown_send_fails() -> None:
    bot = AsyncMock()
    bot.send_message.side_effect = [RuntimeError("bad markdown"), None]
    session_key = SessionKey.from_telegram_message(100, 222)
    bridge = ApprovalUiBridge()
    bridge.set_bot(bot)
    bridge.ensure_orchestrator(_orchestrator(session_key))

    await bridge.send(
        "item/fileChange/requestApproval",
        {
            "threadId": "thread-abcdef",
            "approvalId": "file-telegram",
            "filePath": "C:/repo/file.py",
            "changes": "diff",
        },
    )

    assert bot.send_message.await_count == 2
    _, first_kwargs = bot.send_message.await_args_list[0]
    _, second_kwargs = bot.send_message.await_args_list[1]
    assert first_kwargs["parse_mode"] == "Markdown"
    assert "parse_mode" not in second_kwargs


@pytest.mark.asyncio
async def test_bridge_uses_db_fallback_when_thread_is_not_in_memory() -> None:
    bot = AsyncMock()
    session_key = SessionKey.from_telegram_message(100, 222)
    session_manager = SimpleNamespace(
        reverse_lookup=MagicMock(return_value=None),
        reverse_lookup_db_fallback=AsyncMock(return_value=session_key),
        get_topic_id=MagicMock(return_value=222),
    )
    orchestrator = SimpleNamespace(
        session_manager=session_manager,
        approval_handler=ApprovalHandler(),
        set_approval_ui_sender=MagicMock(),
    )

    async def session_factory():
        yield object()

    bridge = ApprovalUiBridge()
    bridge.set_bot(bot)
    bridge.ensure_orchestrator(orchestrator, session_factory)

    await bridge.send(
        "item/commandExecution/requestApproval",
        {
            "threadId": "thread-abcdef",
            "approvalId": "approval-telegram",
            "command": "Get-Date",
            "availableDecisions": ["accept", "decline"],
        },
    )

    session_manager.reverse_lookup_db_fallback.assert_awaited_once()
    bot.send_message.assert_awaited_once()
