"""Toolbar handler — Reply Keyboard + commands for session control.

Replaces the old inline-keyboard toolbar with a bottom ReplyKeyboard
that appears only while a Codex turn or Shell process is active.

Commands (always available via /):
    /stop      — interrupt active Codex turn or Shell process
    /live      — toggle live status refresh
    /last      — resend the most recent assistant reply
    /status    — show current session state snapshot

Reply Keyboard buttons mirror these commands for one-tap access.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from loguru import logger

from bot.utils.routing import TelegramRoute
from core.session import SessionKey
from providers.shell import ShellProvider

router = Router(name="toolbar")

_shell_provider = ShellProvider()

_last_replies: dict[str, str] = {}

_live_tasks: dict[str, asyncio.Task] = {}

_live_messages: dict[str, Message] = {}

_session_manager: Any | None = None

# ------------------------------------------------------------------
# ReplyKeyboard state machine
# ------------------------------------------------------------------

_KB_IDLE = "idle"
_KB_CODEX = "codex"
_KB_SHELL = "shell"
_KB_LIVE = "live"

_keyboard_states: dict[str, str] = {}
_keyboard_locks: dict[str, asyncio.Lock] = {}


def _kb_lock(key_str: str) -> asyncio.Lock:
    """Return (and create if necessary) the lock for *key_str*."""
    lock = _keyboard_locks.get(key_str)
    if lock is None:
        lock = asyncio.Lock()
        _keyboard_locks[key_str] = lock
    return lock


def set_session_manager(manager: Any | None) -> None:
    """Set the shared CodexSessionManager instance."""
    global _session_manager
    _session_manager = manager


def _is_codex_turn_active(session_key: SessionKey) -> bool:
    if _session_manager is None:
        return False
    return _session_manager.is_turn_active(session_key)


def _read_state(session_key: SessionKey) -> str:
    """Brief human-readable session state."""
    parts: list[str] = []
    if _is_codex_turn_active(session_key):
        parts.append("Codex active")
    if _shell_provider.is_running(session_key.to_string()):
        parts.append("Shell running")
    if not parts:
        return "No active process"
    return " | ".join(parts)


# ------------------------------------------------------------------
# Keyboard builders
# ------------------------------------------------------------------


def _build_codex_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Stop"),
                KeyboardButton(text="Live"),
                KeyboardButton(text="Last Reply"),
            ],
            [KeyboardButton(text="Status")],
        ],
        resize_keyboard=True,
        selective=True,
    )


def _build_shell_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Stop"),
                KeyboardButton(text="Esc"),
                KeyboardButton(text="Tab"),
                KeyboardButton(text="Enter"),
            ],
            [
                KeyboardButton(text="Up"),
                KeyboardButton(text="Down"),
                KeyboardButton(text="Status"),
            ],
        ],
        resize_keyboard=True,
        selective=True,
    )


def _build_live_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Stop Live"),
                KeyboardButton(text="Status"),
            ],
        ],
        resize_keyboard=True,
        selective=True,
    )


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


async def send_reply_keyboard(
    bot: Bot,
    session_key: SessionKey,
    message_thread_id: int | None = None,
) -> Message | None:
    """Send the appropriate ReplyKeyboard for the current session state.

    Idempotent: if the keyboard is already showing with the same layout,
    nothing is sent.
    """
    key_str = session_key.to_string()
    async with _kb_lock(key_str):
        codex_active = _is_codex_turn_active(session_key)
        shell_active = _shell_provider.is_running(key_str)
        live_active = key_str in _live_tasks

        # Determine desired state.
        if live_active:
            desired = _KB_LIVE
        elif shell_active:
            desired = _KB_SHELL
        elif codex_active:
            desired = _KB_CODEX
        else:
            desired = _KB_IDLE

        # Already in the right state → no-op.
        if _keyboard_states.get(key_str) == desired:
            return None

        if desired == _KB_IDLE:
            _keyboard_states.pop(key_str, None)
            return None

        # Pick keyboard.
        if desired == _KB_LIVE:
            keyboard = _build_live_keyboard()
        elif desired == _KB_SHELL:
            keyboard = _build_shell_keyboard()
        else:
            keyboard = _build_codex_keyboard()

        try:
            msg = await bot.send_message(
                chat_id=session_key.chat_id,
                text=f"Controls: {_read_state(session_key)}",
                reply_markup=keyboard,
                message_thread_id=message_thread_id,
            )
            _keyboard_states[key_str] = desired
            return msg
        except Exception as exc:
            logger.warning(f"Toolbar: failed to send reply keyboard: {exc}")
            return None


async def remove_reply_keyboard(
    bot: Bot,
    session_key: SessionKey,
    message_thread_id: int | None = None,
) -> None:
    """Remove the ReplyKeyboard and reset state to idle."""
    key_str = session_key.to_string()
    async with _kb_lock(key_str):
        if _keyboard_states.pop(key_str, None) is None:
            return
        try:
            await bot.send_message(
                chat_id=session_key.chat_id,
                text=f"Finished: {_read_state(session_key)}",
                reply_markup=ReplyKeyboardRemove(),
                message_thread_id=message_thread_id,
            )
        except Exception as exc:
            logger.debug(f"Toolbar: failed to remove reply keyboard: {exc}")


def set_last_reply(session_key: SessionKey, text: str) -> None:
    """Store the most recent assistant reply or command output."""
    _last_replies[session_key.to_string()] = text


# ------------------------------------------------------------------
# Command handlers
# ------------------------------------------------------------------


@router.message(Command("stop"))
async def cmd_stop(message: Message) -> None:
    """Interrupt any active Codex turn or Shell process."""
    route = TelegramRoute.from_message(message)
    session_key = SessionKey.from_telegram_message(route.chat_id, route.message_thread_id)
    key_str = session_key.to_string()
    handled = False

    if _is_codex_turn_active(session_key):
        await _session_manager.cancel_turn(session_key)
        handled = True
    if _shell_provider.is_running(key_str):
        await _shell_provider.terminate(key_str)
        handled = True

    if handled:
        await message.answer(
            "Interrupted.",
            reply_markup=ReplyKeyboardRemove(),
            **route.send_kwargs(),
        )
        _keyboard_states.pop(key_str, None)
    else:
        await message.answer("No active process to stop.", **route.send_kwargs())


@router.message(Command("live"))
async def cmd_live(message: Message) -> None:
    """Toggle live mode for the current session."""
    route = TelegramRoute.from_message(message)
    session_key = SessionKey.from_telegram_message(route.chat_id, route.message_thread_id)
    key_str = session_key.to_string()

    if key_str in _live_tasks:
        # Turn off.
        task = _live_tasks.pop(key_str)
        task.cancel()
        msg = _live_messages.pop(key_str, None)
        if msg is not None:
            with contextlib.suppress(Exception):
                await msg.delete()
        await message.answer(
            "Live mode off.",
            reply_markup=ReplyKeyboardRemove(),
            **route.send_kwargs(),
        )
        _keyboard_states.pop(key_str, None)
        return

    # Turn on.
    msg = await message.answer(
        "Live mode active.\nSession info: initializing...",
        reply_markup=_build_live_keyboard(),
        **route.send_kwargs(),
    )
    _live_messages[key_str] = msg
    _keyboard_states[key_str] = _KB_LIVE

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
                text = "Live mode active.\n\n" + "\n".join(f"- {p}" for p in info_parts)
                await msg.edit_text(text)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug(f"Toolbar live refresh error: {exc}")
                break

    _live_tasks[key_str] = asyncio.create_task(_refresh())


@router.message(Command("last"))
async def cmd_last(message: Message) -> None:
    """Resend the most recent assistant reply."""
    route = TelegramRoute.from_message(message)
    session_key = SessionKey.from_telegram_message(route.chat_id, route.message_thread_id)
    text = _last_replies.get(session_key.to_string())
    if text:
        await message.answer(text, **route.send_kwargs())
    else:
        await message.answer("No last reply stored.", **route.send_kwargs())


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    """Show a brief snapshot of the current session state."""
    route = TelegramRoute.from_message(message)
    session_key = SessionKey.from_telegram_message(route.chat_id, route.message_thread_id)
    state = _read_state(session_key)
    await message.answer(f"Status: {state}", **route.send_kwargs())


# ------------------------------------------------------------------
# ReplyKeyboard text handlers
# ------------------------------------------------------------------

_CODEX_BUTTONS = {"Stop", "Live", "Last Reply", "Status"}
_SHELL_BUTTONS = {"Stop", "Esc", "Tab", "Enter", "Up", "Down", "Status"}
_LIVE_BUTTONS = {"Stop Live", "Status"}
_ALL_BUTTONS = _CODEX_BUTTONS | _SHELL_BUTTONS | _LIVE_BUTTONS


@router.message(F.text.in_(_ALL_BUTTONS))
async def handle_toolbar_text(message: Message) -> None:
    """Handle taps on ReplyKeyboard buttons by delegating to commands."""
    text = message.text or ""
    route = TelegramRoute.from_message(message)
    session_key = SessionKey.from_telegram_message(route.chat_id, route.message_thread_id)
    key_str = session_key.to_string()

    if text == "Stop":
        handled = False
        if _is_codex_turn_active(session_key):
            await _session_manager.cancel_turn(session_key)
            handled = True
        if _shell_provider.is_running(key_str):
            await _shell_provider.terminate(key_str)
            handled = True
        if handled:
            await message.answer(
                "Interrupted.",
                reply_markup=ReplyKeyboardRemove(),
                **route.send_kwargs(),
            )
            _keyboard_states.pop(key_str, None)
        else:
            await message.answer("No active process.", **route.send_kwargs())
        return

    if text == "Live" or text == "Stop Live":
        # Delegate to /live logic.
        await cmd_live(message)
        return

    if text == "Last Reply":
        await cmd_last(message)
        return

    if text == "Status":
        await cmd_status(message)
        return

    if text == "Esc":
        if _shell_provider.is_running(key_str):
            await _shell_provider.send_input(key_str, "\x1b")
            await asyncio.sleep(0.25)
            await message.answer(
                f"Sent Esc — {_read_state(session_key)}",
                **route.send_kwargs(),
            )
        else:
            await message.answer("No active shell.", **route.send_kwargs())
        return

    if text == "Tab":
        if _shell_provider.is_running(key_str):
            await _shell_provider.send_input(key_str, "\t")
            await asyncio.sleep(0.25)
            await message.answer(
                f"Sent Tab — {_read_state(session_key)}",
                **route.send_kwargs(),
            )
        else:
            await message.answer("No active shell.", **route.send_kwargs())
        return

    if text == "Enter":
        if _shell_provider.is_running(key_str):
            await _shell_provider.send_input(key_str, "\n")
            await asyncio.sleep(0.25)
            await message.answer(
                f"Sent Enter — {_read_state(session_key)}",
                **route.send_kwargs(),
            )
        else:
            await message.answer("No active shell.", **route.send_kwargs())
        return

    if text == "Up":
        if _shell_provider.is_running(key_str):
            await _shell_provider.send_input(key_str, "\x1b[A")
            await asyncio.sleep(0.25)
            await message.answer(
                f"Sent Up — {_read_state(session_key)}",
                **route.send_kwargs(),
            )
        else:
            await message.answer("No active shell.", **route.send_kwargs())
        return

    if text == "Down":
        if _shell_provider.is_running(key_str):
            await _shell_provider.send_input(key_str, "\x1b[B")
            await asyncio.sleep(0.25)
            await message.answer(
                f"Sent Down — {_read_state(session_key)}",
                **route.send_kwargs(),
            )
        else:
            await message.answer("No active shell.", **route.send_kwargs())
        return
