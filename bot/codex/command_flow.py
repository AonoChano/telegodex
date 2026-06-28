"""Main Telegram /codex command flow."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.types import Message
from loguru import logger

from bot.codex import command_ui
from bot.utils.routing import TelegramRoute
from core.orchestrator import Orchestrator
from core.session import SessionKey

AsyncCallable = Callable[..., Awaitable[Any]]
EnsureGlobalOrchestrator = Callable[[Orchestrator], None]


async def handle_codex_command(
    message: Message,
    context_manager: Any,
    orchestrator: Orchestrator,
    *,
    approval_ui_bridge: Any,
    codex_daemon: Any,
    codex_topic_state: AsyncCallable,
    send_topic_recovery_prompt: AsyncCallable,
    ensure_global_orch: EnsureGlobalOrchestrator,
    execute_codex_prompt: AsyncCallable,
    handle_codex_new: AsyncCallable,
    codex_topic_bound: str,
    codex_topic_recoverable: str,
) -> None:
    """Handle /codex <prompt> with the persistent app-server architecture."""
    bot = message.bot
    if bot is None:
        return
    approval_ui_bridge.set_bot(bot)

    route = TelegramRoute.from_message(message)
    chat_id = route.chat_id
    user_id = message.from_user.id if message.from_user else 0
    session_key = SessionKey.from_telegram_message(chat_id, route.message_thread_id)

    if route.message_thread_id is not None:
        state = await codex_topic_state(route.message_thread_id, context_manager, chat_id=route.chat_id)
        prompt = command_ui.topic_prompt_text(message)
        if state == codex_topic_recoverable:
            await send_topic_recovery_prompt(message, route, prompt)
            return
        if state != codex_topic_bound:
            await message.answer(
                "Codex is only available from the main chat screen.\n\n"
                "Switch to <b>All</b> and send <code>/codex &lt;prompt&gt;</code> there.",
                parse_mode="HTML",
                **route.send_kwargs(),
            )
            return
    else:
        prompt = command_ui.command_args(message.text or "", "codex")

    if not prompt:
        await message.answer(
            command_ui.CODEX_USAGE_HTML,
            parse_mode="HTML",
            **route.send_kwargs(),
        )
        return

    if not codex_daemon.is_alive():
        await message.answer(
            "Codex daemon is not running. Please restart the bot.",
            **route.send_kwargs(),
        )
        return

    orchestrator.ensure_transport_handlers()
    ensure_global_orch(orchestrator)

    stripped = prompt.strip().lower()
    if command_ui.is_streaming_prompt(prompt):
        await execute_codex_prompt(message, route, context_manager, orchestrator, prompt)
        return

    if stripped == "new":
        await handle_codex_new(message, route, context_manager, orchestrator, session_key, user_id)
        return

    try:
        result_text = await orchestrator.handle_message(
            key=session_key,
            text=f"/codex {prompt}",
            db=context_manager.session,
            user_id=user_id,
        )
        await message.answer(
            result_text,
            parse_mode="Markdown",
            **route.send_kwargs(),
        )
    except Exception as exc:
        logger.exception("Codex: command execution failed")
        await message.answer(
            f"Codex error: {exc}",
            **route.send_kwargs(),
        )
