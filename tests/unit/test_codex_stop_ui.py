"""Unit tests for Codex stop callback handling."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.codex import stop_ui
from core.session import SessionKey


@pytest.mark.asyncio
async def test_handle_stop_callback_rejects_missing_data() -> None:
    callback_query = SimpleNamespace(data=None, answer=AsyncMock(), message=None)
    orchestrator = SimpleNamespace(session_manager=None)

    await stop_ui.handle_stop_callback(callback_query, orchestrator)

    callback_query.answer.assert_awaited_once_with("Invalid stop request.", show_alert=True)


@pytest.mark.asyncio
async def test_handle_stop_callback_rejects_invalid_session_key() -> None:
    callback_query = SimpleNamespace(data="codex_stop|not-a-session-key", answer=AsyncMock(), message=None)
    orchestrator = SimpleNamespace(session_manager=None)

    await stop_ui.handle_stop_callback(callback_query, orchestrator)

    callback_query.answer.assert_awaited_once_with("Invalid stop request.", show_alert=True)


@pytest.mark.asyncio
async def test_handle_stop_callback_cancels_active_turn() -> None:
    session_key = SessionKey.from_telegram_message(100, 222)
    session_manager = SimpleNamespace(
        is_turn_active=MagicMock(return_value=True),
        cancel_turn=AsyncMock(),
    )
    callback_query = SimpleNamespace(
        data=f"codex_stop|{session_key.to_string()}",
        answer=AsyncMock(),
        message=None,
    )
    orchestrator = SimpleNamespace(session_manager=session_manager)

    await stop_ui.handle_stop_callback(callback_query, orchestrator)

    session_manager.is_turn_active.assert_called_once_with(session_key)
    session_manager.cancel_turn.assert_awaited_once_with(session_key)
    callback_query.answer.assert_awaited_once_with("Turn interrupted.", show_alert=False)


@pytest.mark.asyncio
async def test_handle_stop_callback_reports_no_active_turn() -> None:
    session_key = SessionKey.from_telegram_message(100, None)
    session_manager = SimpleNamespace(
        is_turn_active=MagicMock(return_value=False),
        cancel_turn=AsyncMock(),
    )
    callback_query = SimpleNamespace(
        data=f"codex_stop|{session_key.to_string()}",
        answer=AsyncMock(),
        message=None,
    )
    orchestrator = SimpleNamespace(session_manager=session_manager)

    await stop_ui.handle_stop_callback(callback_query, orchestrator)

    session_manager.is_turn_active.assert_called_once_with(session_key)
    session_manager.cancel_turn.assert_not_awaited()
    callback_query.answer.assert_awaited_once_with("No active turn.", show_alert=False)
