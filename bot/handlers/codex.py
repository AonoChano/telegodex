"""CodexBridge v2 handler — /codex command with persistent app-server daemon.

Routes user prompts through the JSON-RPC app-server, streams results via
draft messages, and persists final output as a Rich Message.

Telegram-specific layer: delegates all business logic to the
:class:`core.orchestrator.Orchestrator`.
"""

from __future__ import annotations

from typing import Any

from aiogram import Bot, F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from loguru import logger

from bot.codex import command_flow, command_ui, model_ui, reply_ui, session_ui, shell_ui, stop_ui
from bot.codex.approval_ui import approval_ui_bridge
from bot.codex.topic_filter import IsCodexBoundTopic
from bot.codex.topic_recovery import (
    TopicRecoveryPrompt,
    TopicRecoveryRequest,
    handle_topic_recovery_callback,
    topic_recovery_store,
)
from bot.codex.topic_state import (
    CODEX_TOPIC_BOUND,
    CODEX_TOPIC_NOT_CODEX,
    CODEX_TOPIC_RECOVERABLE,
    bind_codex_thread_to_topic,
    codex_topic_state,
    is_codex_bound_topic,
)
from bot.codex.turn import CodexTurnActor
from bot.handlers import toolbar as toolbar_handler
from bot.streaming import ReactionTracker
from bot.telegram_draft import DraftStream
from bot.utils.rich_messages import send_rich_message
from bot.utils.routing import TelegramRoute
from config import settings
from core.orchestrator import Orchestrator
from core.session import SessionKey
from extensions.codex.daemon import codex_daemon
from storage.context_manager import ContextManager
from utils.screenshot import send_screenshot_to_chat

router = Router(name="codex")

# Draft limits for codex streaming.
DRAFT_FLUSH_CHARS = 200
DRAFT_FLUSH_INTERVAL_SECONDS = 1.2
STATUS_EDIT_INTERVAL_SECONDS = 2.0
STDERR_LATE_GRACE_SECONDS = 2.0
STDERR_FLUSH_GRACE_SECONDS = 0.25


_CODEX_TOPIC_BOUND = CODEX_TOPIC_BOUND
_CODEX_TOPIC_RECOVERABLE = CODEX_TOPIC_RECOVERABLE
_CODEX_TOPIC_NOT_CODEX = CODEX_TOPIC_NOT_CODEX


def set_db_session_factory(factory: Any) -> None:
    """Wire the DB session factory from ``main.py`` startup."""
    approval_ui_bridge.set_db_session_factory(factory)


_TopicRecoveryRequest = TopicRecoveryRequest
_TopicRecoveryPrompt = TopicRecoveryPrompt
_topic_recovery_requests = topic_recovery_store.requests
_topic_recovery_prompts = topic_recovery_store.prompts


def _ensure_global_orch(
    orchestrator: Orchestrator,
    db_session_factory: Any = None,
) -> None:
    """Cache the Orchestrator instance and wire approval UI sender."""
    approval_ui_bridge.ensure_orchestrator(orchestrator, db_session_factory)


async def _approval_ui_sender(method: str, params: dict[str, Any]) -> None:
    """Compatibility wrapper for the transport-level approval callback."""
    await approval_ui_bridge.send(method, params)


def _bot_token() -> str:
    return settings.telegram_bot_token


# ---------------------------------------------------------------------------
# Forum topic helpers
# ---------------------------------------------------------------------------


async def _handle_codex_new(
    message: Message,
    route: TelegramRoute,
    context_manager: Any,
    orchestrator: Orchestrator,
    session_key: SessionKey,
    user_id: int,
) -> None:
    await session_ui.handle_codex_new(
        message,
        route,
        context_manager,
        orchestrator,
        session_key,
        user_id,
        bind_codex_thread_to_topic=_bind_codex_thread_to_topic,
    )

def _codex_send_kwargs(route: TelegramRoute, topic_id: int | None) -> dict[str, Any]:
    return reply_ui.codex_send_kwargs(route, topic_id)


async def _codex_reply(
    message: Message,
    text: str,
    route: TelegramRoute,
    topic_id: int | None,
    **kwargs: Any,
) -> None:
    await reply_ui.codex_reply(message, text, route, topic_id, **kwargs)

def _topic_recovery_key(route: TelegramRoute) -> tuple[int | str, int] | None:
    return topic_recovery_store.key_for_route(route)


async def _delete_previous_topic_recovery_prompt(bot: Bot, route: TelegramRoute) -> None:
    await topic_recovery_store.delete_previous_prompt(bot, route)


async def _send_topic_recovery_prompt(message: Message, route: TelegramRoute, prompt: str) -> None:
    await topic_recovery_store.send_prompt(message, route, prompt)


async def _bind_codex_thread_to_topic(
    *,
    context_manager: Any,
    chat_id: int | str,
    topic_id: int,
    thread_id: str,
    user_id: int,
    cwd: str | None = None,
) -> None:
    await bind_codex_thread_to_topic(
        context_manager=context_manager,
        chat_id=chat_id,
        topic_id=topic_id,
        thread_id=thread_id,
        user_id=user_id,
        cwd=cwd,
    )


async def _is_codex_bound_topic(
    thread_id: int,
    context_manager: Any,
    chat_id: int | str | None = None,
) -> bool:
    return await is_codex_bound_topic(thread_id, context_manager, chat_id=chat_id)


async def _codex_topic_state(
    thread_id: int,
    context_manager: Any,
    chat_id: int | str | None = None,
) -> str:
    return await codex_topic_state(thread_id, context_manager, chat_id=chat_id)


# ---------------------------------------------------------------------------
# Shared prompt executor (Telegram-specific UI layer)
# ---------------------------------------------------------------------------


async def _execute_codex_prompt(
    message: Message,
    route: TelegramRoute,
    context_manager: Any,
    orchestrator: Orchestrator,
    prompt: str,
    user_id_override: int | None = None,
) -> None:
    """Execute a Codex chat prompt and stream results back via Telegram."""
    logger.info(f"_execute_codex_prompt: starting, prompt='{prompt[:50]}...', thread_id={route.message_thread_id}")
    bot = message.bot
    if bot is None:
        logger.warning("_execute_codex_prompt: bot is None, returning")
        return
    approval_ui_bridge.set_bot(bot)

    session_key = SessionKey.from_telegram_message(route.chat_id, route.message_thread_id)
    logger.info(f"_execute_codex_prompt: session_key={session_key}")
    user_id = user_id_override if user_id_override is not None else (message.from_user.id if message.from_user else 0)

    # Send typing indicator.
    await bot.send_chat_action(
        chat_id=route.chat_id,
        action="typing",
        message_thread_id=route.message_thread_id,
        business_connection_id=route.business_connection_id,
    )

    topic_id = route.message_thread_id

    # Send a "Stop" inline button for this turn.
    stop_msg = None
    stop_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Stop generating",
                    callback_data=f"codex_stop|{session_key.to_string()}",
                )
            ]
        ]
    )
    try:
        stop_msg = await bot.send_message(
            chat_id=route.chat_id,
            text="Codex is working...",
            reply_markup=stop_keyboard,
            message_thread_id=topic_id,
        )
    except Exception as exc:
        logger.debug(f"Codex: failed to send stop button: {exc}")

    try:
        await toolbar_handler.send_reply_keyboard(
            bot,
            session_key=session_key,
            message_thread_id=topic_id,
        )
    except Exception as exc:
        logger.debug(f"Codex: failed to send reply keyboard: {exc}")

    # Enable draft streaming in private chats and forum topics.
    use_draft = message.chat.type == "private" or route.message_thread_id is not None
    stream = (
        DraftStream(
            bot_token=_bot_token(),
            chat_id=route.chat_id,
            message_thread_id=topic_id,
            direct_messages_topic_id=route.direct_messages_topic_id,
            business_connection_id=route.business_connection_id,
            use_rich=True,
        )
        if use_draft
        else None
    )

    reaction_tracker = None
    if stop_msg is not None:
        reaction_tracker = ReactionTracker(bot, stop_msg.chat.id, stop_msg.message_id)
        try:
            await reaction_tracker.set_state("thinking")
        except Exception as exc:
            logger.debug(f"Codex: failed to set initial reaction: {exc}")

    actor = CodexTurnActor(
        bot=bot,
        route=route,
        session_key=session_key,
        orchestrator=orchestrator,
        stop_msg=stop_msg,
        stop_keyboard=stop_keyboard,
        stream=stream,
        reaction_tracker=reaction_tracker,
        status_edit_interval=STATUS_EDIT_INTERVAL_SECONDS,
        draft_flush_chars=DRAFT_FLUSH_CHARS,
        draft_flush_interval=DRAFT_FLUSH_INTERVAL_SECONDS,
        stderr_late_grace=STDERR_LATE_GRACE_SECONDS,
        stderr_flush_grace=STDERR_FLUSH_GRACE_SECONDS,
    )
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

        # Persist final result.
        if stream is not None:
            success = await stream.finalize(final_text)
        else:
            success = await send_rich_message(
                bot_token=_bot_token(),
                chat_id=route.chat_id,
                markdown_text=final_text,
                message_thread_id=topic_id,
                direct_messages_topic_id=route.direct_messages_topic_id,
                business_connection_id=route.business_connection_id,
            )
        if not success:
            await _codex_reply(
                message,
                final_text,
                route,
                topic_id,
            )
        # The status / stop-button message has served its purpose once the
        # final answer is on screen. Delete it now instead of leaving
        # "Codex completed." visible alongside the result until ``finally``
        # runs — that transient dupe is confusing on success.
        if success and stop_msg is not None:
            try:
                await bot.delete_message(
                    chat_id=stop_msg.chat.id,
                    message_id=stop_msg.message_id,
                )
                stop_msg = None  # signal ``finally`` it's already gone
            except Exception as exc:
                logger.debug(f"Codex: failed to delete status message after finalize: {exc}")

    except Exception as exc:
        logger.exception("Codex: turn failed")
        await actor.edit_status(f"Codex error.\n{exc}", force=True)
        await _codex_reply(
            message,
            f"Codex error: {exc}",
            route,
            topic_id,
        )
    finally:
        remove_stderr_listener()
        # Remove the stop button message.
        if stop_msg is not None:
            try:
                await bot.delete_message(
                    chat_id=stop_msg.chat.id,
                    message_id=stop_msg.message_id,
                )
            except Exception as exc:
                logger.debug(f"Codex: failed to delete stop button: {exc}")
        # Remove ReplyKeyboard when the turn ends.
        try:
            await toolbar_handler.remove_reply_keyboard(bot, session_key, message_thread_id=topic_id)
        except Exception as exc:
            logger.debug(f"Codex: failed to remove reply keyboard: {exc}")


# ---------------------------------------------------------------------------
# /codex command handler
# ---------------------------------------------------------------------------


@router.message(Command("codex"))
async def cmd_codex_v2(
    message: Message,
    context_manager: Any,
    orchestrator: Orchestrator,
) -> None:
    await command_flow.handle_codex_command(
        message,
        context_manager,
        orchestrator,
        approval_ui_bridge=approval_ui_bridge,
        codex_daemon=codex_daemon,
        codex_topic_state=_codex_topic_state,
        send_topic_recovery_prompt=_send_topic_recovery_prompt,
        ensure_global_orch=_ensure_global_orch,
        execute_codex_prompt=_execute_codex_prompt,
        handle_codex_new=_handle_codex_new,
        codex_topic_bound=_CODEX_TOPIC_BOUND,
        codex_topic_recoverable=_CODEX_TOPIC_RECOVERABLE,
    )
# ---------------------------------------------------------------------------
# Codex-bound topic message handler
# ---------------------------------------------------------------------------


@router.message(F.text, IsCodexBoundTopic())
async def handle_codex_topic_message(
    message: Message,
    context_manager: Any,
    orchestrator: Orchestrator,
) -> None:
    """Handle regular text messages inside a Codex-bound forum topic.

    Routes the message directly to the Codex session bound to this topic
    without requiring the /codex prefix.
    """
    logger.info(f"handle_codex_topic_message: received message in thread {message.message_thread_id}")
    route = TelegramRoute.from_message(message)
    prompt = command_ui.topic_prompt_text(message)

    if not prompt:
        raise SkipHandler

    # Verify this topic is actually bound to a Codex session.
    topic_id = message.message_thread_id
    if topic_id is None:
        raise SkipHandler
    state = await _codex_topic_state(topic_id, context_manager, chat_id=route.chat_id)
    if state == _CODEX_TOPIC_RECOVERABLE:
        await _send_topic_recovery_prompt(message, route, prompt)
        return
    if state != _CODEX_TOPIC_BOUND:
        raise SkipHandler

    # Check daemon readiness.
    daemon_alive = codex_daemon.is_alive()
    logger.info(f"handle_codex_topic_message: codex_daemon.is_alive()={daemon_alive}")
    if not daemon_alive:
        await _codex_reply(
            message,
            "Codex daemon is not running. Please restart the bot.",
            route,
            route.message_thread_id,
        )
        return

    logger.info("handle_codex_topic_message: calling orchestrator.ensure_transport_handlers()")
    orchestrator.ensure_transport_handlers()
    _ensure_global_orch(orchestrator)

    # Route the message as a Codex prompt.
    logger.info(f"handle_codex_topic_message: routing to _execute_codex_prompt, prompt='{prompt[:50]}...'")
    await _execute_codex_prompt(message, route, context_manager, orchestrator, prompt)


# ---------------------------------------------------------------------------
# /model command handler
# ---------------------------------------------------------------------------


@router.message(Command("model"))
async def cmd_model(
    message: Message,
    context_manager: ContextManager,
    orchestrator: Orchestrator,
) -> None:
    await model_ui.handle_model_command(message, context_manager, orchestrator)

# ---------------------------------------------------------------------------
# /shell command handler
# ---------------------------------------------------------------------------


async def _execute_shell_telegram(
    message: Message,
    route: TelegramRoute,
    orchestrator: Orchestrator,
    command: str,
    session_key: SessionKey,
) -> None:
    await shell_ui.execute_shell_telegram(message, route, orchestrator, command, session_key)


@router.message(Command("shell"))
async def cmd_shell(
    message: Message,
    orchestrator: Orchestrator,
    context_manager: ContextManager | None = None,
) -> None:
    await shell_ui.handle_shell_command(
        message,
        orchestrator,
        context_manager,
        ensure_orchestrator=_ensure_global_orch,
        execute_shell=_execute_shell_telegram,
    )


async def _propose_shell_telegram(
    message: Message,
    route: TelegramRoute,
    orchestrator: Orchestrator,
    request: str,
    session_key: SessionKey,
    context_manager: ContextManager | None,
) -> None:
    await shell_ui.propose_shell_telegram(message, route, orchestrator, request, session_key, context_manager)


# ---------------------------------------------------------------------------
# Inline button callbacks
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("codex_stop|"))
async def handle_codex_stop_callback(
    callback_query: CallbackQuery,
    orchestrator: Orchestrator,
) -> None:
    await stop_ui.handle_stop_callback(callback_query, orchestrator)


@router.callback_query(F.data.startswith("codex_topic_recover|"))
async def handle_codex_topic_recovery_callback(
    callback_query: CallbackQuery,
    context_manager: Any,
    orchestrator: Orchestrator,
) -> None:
    await handle_topic_recovery_callback(
        callback_query,
        context_manager,
        orchestrator,
        codex_daemon=codex_daemon,
        bind_codex_thread_to_topic=_bind_codex_thread_to_topic,
        execute_codex_prompt=_execute_codex_prompt,
        codex_reply=_codex_reply,
    )


@router.callback_query(F.data.startswith("shell_ai:"))
async def handle_shell_ai_callback(
    callback_query: CallbackQuery,
    orchestrator: Orchestrator,
) -> None:
    await shell_ui.handle_shell_ai_callback(callback_query, orchestrator, execute_shell=_execute_shell_telegram)


@router.callback_query(F.data.startswith("shell_approve:"))
async def handle_shell_approve_callback(
    callback_query: CallbackQuery,
    orchestrator: Orchestrator,
) -> None:
    await shell_ui.handle_shell_approve_callback(callback_query, orchestrator, execute_shell=_execute_shell_telegram)

# ---------------------------------------------------------------------------
# /screenshot command handler
# ---------------------------------------------------------------------------


@router.message(Command("screenshot"))
async def cmd_screenshot(message: Message) -> None:
    """Capture the terminal window and send it as a photo."""
    route = TelegramRoute.from_message(message)
    await send_screenshot_to_chat(message, route)
