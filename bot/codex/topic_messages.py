"""Codex-bound Telegram topic message flow."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.types import Message
from loguru import logger

from bot.codex import command_ui
from bot.utils.routing import TelegramRoute
from core.orchestrator import Orchestrator

AsyncCallable = Callable[..., Awaitable[Any]]
EnsureGlobalOrchestrator = Callable[[Orchestrator], None]


async def handle_topic_message(
    message: Message,
    context_manager: Any,
    orchestrator: Orchestrator,
    *,
    codex_topic_state: AsyncCallable,
    send_topic_recovery_prompt: AsyncCallable,
    codex_daemon: Any,
    codex_reply: AsyncCallable,
    ensure_global_orch: EnsureGlobalOrchestrator,
    execute_codex_prompt: AsyncCallable,
    codex_topic_bound: str,
    codex_topic_recoverable: str,
) -> None:
    """Route text from a Codex-bound topic directly into the bound session."""
    logger.info(f"handle_codex_topic_message: received message in thread {message.message_thread_id}")
    route = TelegramRoute.from_message(message)
    prompt = command_ui.topic_prompt_text(message)

    if not prompt:
        raise SkipHandler

    topic_id = message.message_thread_id
    if topic_id is None:
        raise SkipHandler
    state = await codex_topic_state(topic_id, context_manager, chat_id=route.chat_id)
    if state == codex_topic_recoverable:
        await send_topic_recovery_prompt(message, route, prompt)
        return
    if state != codex_topic_bound:
        raise SkipHandler

    daemon_alive = codex_daemon.is_alive()
    logger.info(f"handle_codex_topic_message: codex_daemon.is_alive()={daemon_alive}")
    if not daemon_alive:
        await codex_reply(
            message,
            "Codex daemon is not running. Please restart the bot.",
            route,
            route.message_thread_id,
        )
        return

    logger.info("handle_codex_topic_message: calling orchestrator.ensure_transport_handlers()")
    orchestrator.ensure_transport_handlers()
    ensure_global_orch(orchestrator)

    logger.info(f"handle_codex_topic_message: routing to _execute_codex_prompt, prompt='{prompt[:50]}...'")
    await execute_codex_prompt(message, route, context_manager, orchestrator, prompt)
