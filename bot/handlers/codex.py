"""CodexBridge v2 handler — /codex command with persistent app-server daemon.

Routes user prompts through the JSON-RPC app-server, streams results via
draft messages, and persists final output as a Rich Message.

Telegram-specific layer: delegates all business logic to the
:class:`core.orchestrator.Orchestrator`.
"""

from __future__ import annotations

from typing import Any

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.codex import (
    command_flow,
    model_ui,
    reply_ui,
    session_ui,
    shell_ui,
    stop_ui,
    topic_messages,
    turn_executor,
)
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
)
from bot.handlers import toolbar as toolbar_handler
from bot.utils.routing import TelegramRoute
from config import settings
from core.orchestrator import Orchestrator
from core.session import SessionKey
from extensions.codex.daemon import codex_daemon
from i18n import resolve_locale, tr
from storage.context_manager import ContextManager

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


async def _handle_codex_resume(
    message: Message,
    route: TelegramRoute,
    context_manager: Any,
    orchestrator: Orchestrator,
    session_key: SessionKey,
    user_id: int,
    thread_id: str,
) -> None:
    await session_ui.handle_codex_resume(
        message,
        route,
        context_manager,
        orchestrator,
        session_key,
        user_id,
        thread_id,
        bind_codex_thread_to_topic=_bind_codex_thread_to_topic,
    )


async def _codex_reply(
    message: Message,
    text: str,
    route: TelegramRoute,
    topic_id: int | None,
    **kwargs: Any,
) -> None:
    await reply_ui.codex_reply(message, text, route, topic_id, **kwargs)



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
    await turn_executor.execute_codex_prompt(
        message=message,
        route=route,
        context_manager=context_manager,
        orchestrator=orchestrator,
        prompt=prompt,
        user_id_override=user_id_override,
        bot_token=_bot_token(),
        approval_ui_bridge=approval_ui_bridge,
        toolbar_handler=toolbar_handler,
        codex_daemon=codex_daemon,
        codex_reply=_codex_reply,
        status_edit_interval=STATUS_EDIT_INTERVAL_SECONDS,
        draft_flush_chars=DRAFT_FLUSH_CHARS,
        draft_flush_interval=DRAFT_FLUSH_INTERVAL_SECONDS,
        stderr_late_grace=STDERR_LATE_GRACE_SECONDS,
        stderr_flush_grace=STDERR_FLUSH_GRACE_SECONDS,
    )


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
        handle_codex_resume=_handle_codex_resume,
        codex_topic_bound=_CODEX_TOPIC_BOUND,
        codex_topic_recoverable=_CODEX_TOPIC_RECOVERABLE,
    )
# ---------------------------------------------------------------------------
# Codex-bound topic message handler
# ---------------------------------------------------------------------------


@router.message(lambda message: bool(message.text and message.text.strip().startswith("/")))
async def guard_codex_topic_bot_command(
    message: Message,
    context_manager: Any,
) -> None:
    """Keep generic Bot commands out of Codex-owned topics."""
    route = TelegramRoute.from_message(message)
    if route.message_thread_id is None:
        raise SkipHandler
    state = await _codex_topic_state(route.message_thread_id, context_manager, chat_id=route.chat_id)
    if state == _CODEX_TOPIC_NOT_CODEX:
        raise SkipHandler

    locale = resolve_locale(None, message.from_user.language_code if message.from_user else None)
    await message.answer(
        tr("bot.errors.codex_topic_command_unsupported", locale),
        parse_mode="HTML",
        **route.send_kwargs(),
    )


@router.message(F.text, IsCodexBoundTopic())
async def handle_codex_topic_message(
    message: Message,
    context_manager: Any,
    orchestrator: Orchestrator,
) -> None:
    await topic_messages.handle_topic_message(
        message,
        context_manager,
        orchestrator,
        codex_topic_state=_codex_topic_state,
        send_topic_recovery_prompt=_send_topic_recovery_prompt,
        codex_daemon=codex_daemon,
        codex_reply=_codex_reply,
        ensure_global_orch=_ensure_global_orch,
        execute_codex_prompt=_execute_codex_prompt,
        codex_topic_bound=_CODEX_TOPIC_BOUND,
        codex_topic_recoverable=_CODEX_TOPIC_RECOVERABLE,
    )


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
