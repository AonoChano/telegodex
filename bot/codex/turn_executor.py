"""Codex prompt turn executor for Telegram routes."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.types import Message
from loguru import logger

from bot.codex import turn_lifecycle, turn_setup
from bot.utils.routing import TelegramRoute
from core.orchestrator import Orchestrator
from core.session import SessionKey

CodexReply = Callable[[Message, str, TelegramRoute, int | None], Awaitable[None]]


async def execute_codex_prompt(
    *,
    message: Message,
    route: TelegramRoute,
    context_manager: Any,
    orchestrator: Orchestrator,
    prompt: str,
    bot_token: str,
    approval_ui_bridge: Any,
    toolbar_handler: Any,
    codex_daemon: Any,
    codex_reply: CodexReply,
    user_id_override: int | None = None,
    status_edit_interval: float,
    draft_flush_chars: int,
    draft_flush_interval: float,
    stderr_late_grace: float,
    stderr_flush_grace: float,
) -> None:
    """Execute a Codex chat prompt and stream results back via Telegram."""
    logger.info(f"execute_codex_prompt: starting, prompt='{prompt[:50]}...', thread_id={route.message_thread_id}")
    bot = message.bot
    if bot is None:
        logger.warning("execute_codex_prompt: bot is None, returning")
        return
    approval_ui_bridge.set_bot(bot)

    session_key = SessionKey.from_telegram_message(route.chat_id, route.message_thread_id)
    logger.info(f"execute_codex_prompt: session_key={session_key}")
    user_id = user_id_override if user_id_override is not None else (message.from_user.id if message.from_user else 0)

    prepared_turn = await turn_setup.prepare_codex_turn(
        message=message,
        route=route,
        orchestrator=orchestrator,
        bot_token=bot_token,
        toolbar_handler=toolbar_handler,
        status_edit_interval=status_edit_interval,
        draft_flush_chars=draft_flush_chars,
        draft_flush_interval=draft_flush_interval,
        stderr_late_grace=stderr_late_grace,
        stderr_flush_grace=stderr_flush_grace,
    )
    if prepared_turn is None:
        return

    session_key = prepared_turn.session_key
    topic_id = prepared_turn.topic_id
    stop_msg = prepared_turn.stop_msg
    stream = prepared_turn.stream
    actor = prepared_turn.actor
    remove_stderr_listener = codex_daemon.add_stderr_listener(actor.on_daemon_stderr)
    try:
        final_text = await orchestrator.handle_message_streaming(
            key=session_key,
            text=prompt,
            db=context_manager.session,
            user_id=user_id,
            callbacks=actor.build_callbacks(),
        )

        final_text = await actor.prepare_final_text(final_text)

        toolbar_handler.set_last_reply(session_key, final_text)

        stop_msg = await turn_lifecycle.persist_final_output(
            bot=bot,
            bot_token=bot_token,
            message=message,
            route=route,
            topic_id=topic_id,
            final_text=final_text,
            stream=stream,
            stop_msg=stop_msg,
            codex_reply=codex_reply,
        )

    except Exception as exc:
        logger.exception("Codex: turn failed")
        await actor.edit_status(f"Codex error.\n{exc}", force=True)
        await codex_reply(
            message,
            f"Codex error: {exc}",
            route,
            topic_id,
        )
    finally:
        remove_stderr_listener()
        await turn_lifecycle.cleanup_turn(
            bot=bot,
            toolbar_handler=toolbar_handler,
            session_key=session_key,
            topic_id=topic_id,
            stop_msg=stop_msg,
        )
