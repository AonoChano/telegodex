"""Inline stop-button handling for Codex turns."""

from __future__ import annotations

import contextlib

from aiogram.types import CallbackQuery, Message

from core.orchestrator import Orchestrator
from core.session import SessionKey


async def handle_stop_callback(
    callback_query: CallbackQuery,
    orchestrator: Orchestrator,
) -> None:
    """Handle the "Stop generating" inline button."""
    data = callback_query.data
    if data is None:
        await callback_query.answer("Invalid stop request.", show_alert=True)
        return
    try:
        _, session_key_str = data.split("|", 1)
        session_key = SessionKey.from_string(session_key_str)
    except ValueError:
        await callback_query.answer("Invalid stop request.", show_alert=True)
        return

    session_manager = orchestrator.session_manager
    if session_manager is not None and session_manager.is_turn_active(session_key):
        await session_manager.cancel_turn(session_key)
        await callback_query.answer("Turn interrupted.", show_alert=False)
        message = callback_query.message
        if isinstance(message, Message):
            with contextlib.suppress(Exception):
                await message.edit_text("_Interrupted._")
    else:
        await callback_query.answer("No active turn.", show_alert=False)
