"""Toolbar handler — /toolbar command with inline keyboard for session control."""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from loguru import logger

from bot.handlers.toolbar_config import ToolbarConfig, load_toolbar_config
from bot.utils.routing import TelegramRoute
from core.session import SessionKey
from providers.shell import ShellProvider

router = Router(name="toolbar")

_shell_provider = ShellProvider()

_last_replies: dict[str, str] = {}

_live_tasks: dict[str, asyncio.Task] = {}

_live_messages: dict[str, Message] = {}

_session_manager: Any | None = None

# Loaded once at import time; restart bot to refresh.
_toolbar_config: ToolbarConfig = load_toolbar_config()


def set_session_manager(manager: Any | None) -> None:
    """Set the shared CodexSessionManager instance."""
    global _session_manager
    _session_manager = manager


def _is_codex_turn_active(session_key: SessionKey) -> bool:
    if _session_manager is None:
        return False
    return _session_manager.is_turn_active(session_key)


def _build_toolbar(session_key: SessionKey) -> InlineKeyboardMarkup:
    """Build the inline keyboard layout for the toolbar."""
    rows_map: dict[int, list[InlineKeyboardButton]] = {}
    codex_active = _is_codex_turn_active(session_key)
    shell_active = _shell_provider.is_running(session_key.to_string())
    any_active = codex_active or shell_active

    for action in _toolbar_config.actions:
        # Evaluate conditions
        if action.condition == "codex_active" and not codex_active:
            continue
        if action.condition == "active" and not any_active:
            continue

        callback = (
            action.callback_data_template
            if action.callback_data_template
            else f"tb:{action.name}:{session_key.to_string()}"
        )
        btn = InlineKeyboardButton(text=action.label, callback_data=callback)
        rows_map.setdefault(action.row, []).append(btn)

    # Sort rows by index and build inline_keyboard list.
    sorted_rows = [rows_map[k] for k in sorted(rows_map.keys())]
    return InlineKeyboardMarkup(inline_keyboard=sorted_rows)


@router.message(Command("toolbar"))
async def cmd_toolbar(message: Message) -> None:
    """Send the toolbar inline keyboard."""
    route = TelegramRoute.from_message(message)
    session_key = SessionKey.from_telegram_message(route.chat_id, route.message_thread_id)

    keyboard = _build_toolbar(session_key)
    await message.answer("Toolbar:", reply_markup=keyboard, **route.send_kwargs())


async def send_toolbar(
    bot: Bot,
    session_key: SessionKey,
    message_thread_id: int | None = None,
) -> Message | None:
    """Send a toolbar message to the given chat."""
    keyboard = _build_toolbar(session_key)
    try:
        return await bot.send_message(
            chat_id=session_key.chat_id,
            text="Toolbar:",
            reply_markup=keyboard,
            message_thread_id=message_thread_id,
        )
    except Exception as exc:
        logger.warning(f"Toolbar: failed to send toolbar: {exc}")
        return None


def set_last_reply(session_key: SessionKey, text: str) -> None:
    """Store the most recent assistant reply or command output."""
    _last_replies[session_key.to_string()] = text


def _parse_callback(data: str) -> tuple[str, SessionKey] | None:
    """Parse callback data in format tb:action:session_key."""
    if not data.startswith("tb:"):
        return None
    parts = data.split(":", 2)
    if len(parts) != 3:
        return None
    action = parts[1]
    session_key_str = parts[2]
    try:
        session_key = SessionKey.from_string(session_key_str)
    except ValueError:
        return None
    return action, session_key


async def _read_session_state(session_key: SessionKey) -> str:
    """Capture a brief snapshot of session state for feedback toasts."""
    parts: list[str] = []
    if _is_codex_turn_active(session_key):
        parts.append("Codex active")
    if _shell_provider.is_running(session_key.to_string()):
        parts.append("Shell running")
    if not parts:
        return "No active process"
    return " | ".join(parts)


@router.callback_query(F.data.startswith("tb:"))
async def handle_toolbar_callback(callback_query: CallbackQuery) -> None:
    """Handle all toolbar inline button callbacks."""
    parsed = _parse_callback(callback_query.data)
    if parsed is None:
        await callback_query.answer("Invalid callback data.", show_alert=True)
        return

    action, session_key = parsed
    key_str = session_key.to_string()

    if action == "ctrl_c":
        handled = False
        if _is_codex_turn_active(session_key):
            await _session_manager.cancel_turn(session_key)
            handled = True
        if _shell_provider.is_running(key_str):
            await _shell_provider.terminate(key_str)
            handled = True
        if handled:
            await callback_query.answer("Interrupted.", show_alert=False)
        else:
            await callback_query.answer("No active process.", show_alert=False)
        return

    if action == "live":
        if key_str in _live_tasks:
            task = _live_tasks.pop(key_str)
            task.cancel()
            msg = _live_messages.pop(key_str, None)
            if msg is not None:
                with contextlib.suppress(Exception):
                    await msg.delete()
            await callback_query.answer("Live mode off.", show_alert=False)
        else:
            msg = await callback_query.message.answer(
                "Live mode active.\nSession info: initializing..."
            )
            _live_messages[key_str] = msg

            async def _refresh() -> None:
                while True:
                    try:
                        await asyncio.sleep(5.0)
                        info_parts: list[str] = []
                        if _is_codex_turn_active(session_key):
                            info_parts.append("Codex turn: active")
                        if _shell_provider.is_running(key_str):
                            info_parts.append("Shell process: running")
                        if not info_parts:
                            info_parts.append("No active sessions.")
                        text = "Live mode active.\n\n" + "\n".join(
                            f"- {p}" for p in info_parts
                        )
                        await msg.edit_text(text)
                    except asyncio.CancelledError:
                        break
                    except Exception as exc:
                        logger.debug(f"Toolbar live refresh error: {exc}")
                        break

            _live_tasks[key_str] = asyncio.create_task(_refresh())
            await callback_query.answer("Live mode on.", show_alert=False)
        return

    if action == "last_reply":
        text = _last_replies.get(key_str)
        if text:
            await callback_query.message.answer(text)
            await callback_query.answer("Resent last reply.", show_alert=False)
        else:
            await callback_query.answer("No last reply stored.", show_alert=False)
        return

    if action == "esc":
        if _shell_provider.is_running(key_str):
            await _shell_provider.send_input(key_str, "\x1b")
            await asyncio.sleep(0.25)
            state = await _read_session_state(session_key)
            await callback_query.answer(f"Sent Esc — {state}", show_alert=False)
        elif _is_codex_turn_active(session_key):
            await callback_query.answer("Sent Esc (Codex placeholder).", show_alert=False)
        else:
            await callback_query.answer("No active process.", show_alert=False)
        return

    if action == "tab":
        if _shell_provider.is_running(key_str):
            await _shell_provider.send_input(key_str, "\t")
            await asyncio.sleep(0.25)
            state = await _read_session_state(session_key)
            await callback_query.answer(f"Sent Tab — {state}", show_alert=False)
        elif _is_codex_turn_active(session_key):
            await callback_query.answer("Sent Tab (Codex placeholder).", show_alert=False)
        else:
            await callback_query.answer("No active process.", show_alert=False)
        return

    if action == "mode":
        await callback_query.answer("Mode switching not yet implemented.", show_alert=True)
        return

    if action == "up":
        if _shell_provider.is_running(key_str):
            await _shell_provider.send_input(key_str, "\x1b[A")
            await asyncio.sleep(0.25)
            state = await _read_session_state(session_key)
            await callback_query.answer(f"Sent Up — {state}", show_alert=False)
        elif _is_codex_turn_active(session_key):
            await callback_query.answer("Sent Up (Codex placeholder).", show_alert=False)
        else:
            await callback_query.answer("No active process.", show_alert=False)
        return

    if action == "down":
        if _shell_provider.is_running(key_str):
            await _shell_provider.send_input(key_str, "\x1b[B")
            await asyncio.sleep(0.25)
            state = await _read_session_state(session_key)
            await callback_query.answer(f"Sent Down — {state}", show_alert=False)
        elif _is_codex_turn_active(session_key):
            await callback_query.answer("Sent Down (Codex placeholder).", show_alert=False)
        else:
            await callback_query.answer("No active process.", show_alert=False)
        return

    if action == "enter":
        if _shell_provider.is_running(key_str):
            await _shell_provider.send_input(key_str, "\n")
            await asyncio.sleep(0.25)
            state = await _read_session_state(session_key)
            await callback_query.answer(f"Sent Enter — {state}", show_alert=False)
        elif _is_codex_turn_active(session_key):
            await callback_query.answer("Sent Enter (Codex placeholder).", show_alert=False)
        else:
            await callback_query.answer("No active process.", show_alert=False)
        return

    if action == "close":
        with contextlib.suppress(Exception):
            await callback_query.message.delete()
        await callback_query.answer("Toolbar closed.", show_alert=False)
        return

    await callback_query.answer("Unknown action.", show_alert=False)
