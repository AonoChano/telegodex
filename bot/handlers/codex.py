"""CodexBridge v2 handler — /codex command with persistent app-server daemon.

Routes user prompts through the JSON-RPC app-server, streams results via
draft messages, and persists final output as a Rich Message.

Telegram-specific layer: delegates all business logic to the
:class:`core.orchestrator.Orchestrator`.
"""

from __future__ import annotations

import contextlib
import uuid
from dataclasses import dataclass
from typing import Any

from aiogram import Bot, F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import BaseFilter, Command
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from loguru import logger
from sqlalchemy import select

from bot.codex import formatting as fmt
from bot.codex.turn import CodexTurnActor
from bot.handlers import toolbar as toolbar_handler
from bot.streaming import ReactionTracker
from bot.telegram_draft import DraftStream, shorten_plain_telegram_text
from bot.utils.rich_messages import send_rich_message
from bot.utils.routing import TelegramRoute
from config import settings
from core.orchestrator import Orchestrator
from core.orchestrator.shell_pipeline import (
    build_shell_proposal_messages,
    format_shell_proposal_html,
    parse_shell_command_proposal,
    parse_shell_request,
)
from core.session import SessionKey, session_manager
from extensions.codex.commands import parse_instruction_prefix
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


_CODEX_TOPIC_BOUND = "bound"
_CODEX_TOPIC_RECOVERABLE = "recoverable"
_CODEX_TOPIC_NOT_CODEX = "not_codex"

# Bot instance stored for approval message routing.
_current_bot: Bot | None = None

# Global Orchestrator reference for transport-level approval callbacks.
_global_orch: Orchestrator | None = None

# Session factory (async callable returning an AsyncSession context) used to
# resolve approval requests for threads that aren't loaded in memory yet.
_db_session_factory: Any = None


def set_db_session_factory(factory: Any) -> None:
    """Wire the DB session factory from ``main.py`` startup.

    ``factory`` should be an async generator (e.g. ``Database.get_session``)
    that yields an ``AsyncSession``.  It is consumed by
    :func:`_approval_ui_sender` when a thread-id cannot be resolved in
    memory (e.g. after a bot restart).
    """
    global _db_session_factory
    _db_session_factory = factory


@dataclass(frozen=True)
class _TopicRecoveryRequest:
    chat_id: int | str
    topic_id: int
    prompt: str
    user_id: int


@dataclass(frozen=True)
class _TopicRecoveryPrompt:
    request_id: str
    message_id: int


_topic_recovery_requests: dict[str, _TopicRecoveryRequest] = {}
_topic_recovery_prompts: dict[tuple[int | str, int], _TopicRecoveryPrompt] = {}


def _command_args(text: str, command: str) -> str:
    """Return text after a Telegram command, accepting /command@botname."""
    stripped = text.strip()
    prefix = f"/{command}"
    if not stripped.startswith(prefix):
        return stripped
    rest = stripped[len(prefix) :]
    if rest.startswith("@"):
        if " " not in rest:
            return ""
        rest = rest.split(" ", 1)[1]
    return rest.strip()


def _topic_prompt_text(message: Message) -> str:
    """Return user prompt text inside a Codex topic, without a leading /codex."""
    return _command_args(message.text or "", "codex")


def _ensure_global_orch(
    orchestrator: Orchestrator,
    db_session_factory: Any = None,
) -> None:
    """Cache the Orchestrator instance and wire approval UI sender.

    ``db_session_factory`` is an async-callable that yields a context manager
    producing an ``AsyncSession`` (e.g. ``Database().get_session``). It is
    used to resolve approval requests for threads not loaded in memory.
    """
    global _global_orch, _db_session_factory
    if _global_orch is None:
        _global_orch = orchestrator
        orchestrator.set_approval_ui_sender(_approval_ui_sender)
    if db_session_factory is not None:
        _db_session_factory = db_session_factory


async def _approval_ui_sender(method: str, params: dict[str, Any]) -> None:
    """Send approval requests to Telegram using the cached bot instance.

    All early-return paths log a warning instead of failing silently: a
    silent skip causes the turn to auto-deny after the timeout with no
    visible clue, which is the original "button never appeared" bug.
    """
    if _current_bot is None or _global_orch is None:
        logger.warning(f"approval UI skipped (no bot/orchestrator wired): method={method}")
        return
    sm = _global_orch.session_manager
    if sm is None:
        logger.warning(f"approval UI skipped (no session manager): method={method}")
        return
    thread_id = params.get("threadId", "")
    session_key = sm.reverse_lookup(thread_id)
    if session_key is None:
        # Thread not opened in this process (bot restart, daemon reconnect).
        # Fall back to the database before giving up.
        if _db_session_factory is not None:
            try:
                async for db in _db_session_factory():
                    session_key = await sm.reverse_lookup_db_fallback(thread_id, db)
                    break
            except Exception:
                logger.exception(f"approval UI DB fallback failed for thread={thread_id}")
        if session_key is None:
            logger.warning(f"approval UI skipped (thread {thread_id} not resolvable in memory or DB): method={method}")
            return
    approval_id = params.get("approvalId", params.get("itemId", "unknown"))
    if method == "item/commandExecution/requestApproval":
        text = _global_orch.approval_handler.format_command_approval_markdown(approval_id, params)
    elif method == "item/fileChange/requestApproval":
        text = _global_orch.approval_handler.format_file_change_approval_markdown(approval_id, params)
    elif method == "item/permissions/requestApproval":
        text = _global_orch.approval_handler.format_permissions_approval_markdown(approval_id, params)
    else:
        logger.warning(f"approval UI skipped (unsupported method): method={method}")
        return
    keyboard = _global_orch.approval_handler.build_approval_keyboard(approval_id, params)
    topic_id = sm.get_topic_id(thread_id) or session_key.topic_id
    # Approvals are synchronous gates: if the message never renders, the user
    # can't see the buttons and the turn auto-denies after the timeout. So we
    # try Markdown first (nicer rendering), then fall back to plain text if
    # Telegram rejects the formatting — Codex commands often contain `_`, `*`,
    # `[` etc. that legacy Markdown treats as markup and 400s on.
    try:
        await _current_bot.send_message(
            chat_id=session_key.chat_id,
            text=text,
            reply_markup=keyboard,
            message_thread_id=topic_id,
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.warning(f"Codex: approval Markdown send failed, retrying as plain text: {exc}")
        try:
            await _current_bot.send_message(
                chat_id=session_key.chat_id,
                text=text,
                reply_markup=keyboard,
                message_thread_id=topic_id,
            )
        except Exception as exc2:
            logger.warning(f"Codex: failed to send approval message to {session_key}: {exc2}")


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
    """Handle /codex new — create a new Codex session in a new forum topic."""
    bot = message.bot
    if bot is None:
        await message.answer(
            "Bot instance unavailable.",
            **route.send_kwargs(),
        )
        return

    try:
        # Create the new Codex session first.
        info = await orchestrator.codex_new_session(session_key, context_manager.session, user_id)
        thread_id = info["thread_id"]
        cwd = info.get("cwd", "default")

        # Create a forum topic for this session.
        # Topic name: "Codex: <short_thread_id>"
        short_thread = thread_id[:8]
        topic_name = f"Codex: {short_thread}"

        forum_topic = await bot.create_forum_topic(
            chat_id=route.chat_id,
            name=topic_name,
        )
        topic_id = forum_topic.message_thread_id

        # Update the session manager to map this thread to the topic.
        sm = orchestrator.session_manager
        if sm is not None:
            sm.set_topic_id(thread_id, topic_id)

            # Update the SessionKey mapping from (topic_id=None) to (topic_id=N)
            old_key = SessionKey.from_telegram_message(route.chat_id, None)
            new_key = SessionKey.from_telegram_message(route.chat_id, topic_id)
            updated = sm.update_session_key(old_key, new_key)
            logger.info(
                f"_handle_codex_new: updated session key mapping: old={old_key}, new={new_key}, success={updated}"
            )

        await _bind_codex_thread_to_topic(
            context_manager=context_manager,
            chat_id=route.chat_id,
            topic_id=topic_id,
            thread_id=thread_id,
            user_id=user_id,
            cwd=cwd,
        )

        # Send a welcome message to the new topic.
        await bot.send_message(
            chat_id=route.chat_id,
            message_thread_id=topic_id,
            text=(
                f"**New Codex Session**\n\n"
                f"Thread: `{thread_id}`\n"
                f"CWD: `{cwd}`\n\n"
                f"Send your prompts here directly (no `/codex` prefix needed)."
            ),
            parse_mode="Markdown",
        )

        # Send a confirmation to the original chat.
        await message.answer(
            f"✅ Created new Codex session in topic **{topic_name}**.",
            parse_mode="Markdown",
            **route.send_kwargs(),
        )

    except Exception as exc:
        logger.exception("Failed to create Codex session with forum topic")
        await message.answer(
            f"❌ Failed to create new session: {exc}",
            **route.send_kwargs(),
        )


def _codex_send_kwargs(route: TelegramRoute, topic_id: int | None) -> dict[str, Any]:
    """Build send kwargs, adding ``message_thread_id`` when a forum topic exists."""
    kwargs = dict(route.send_kwargs())
    if topic_id is not None:
        kwargs["message_thread_id"] = topic_id
    return kwargs


async def _codex_reply(
    message: Message,
    text: str,
    route: TelegramRoute,
    topic_id: int | None,
    **kwargs: Any,
) -> None:
    """Send a reply routed to the Codex topic.

    Uses ``bot.send_message`` directly to avoid ``message.answer()``
    auto-including ``message_thread_id`` when the message originated from
    a different topic.
    """
    merged = _codex_send_kwargs(route, topic_id)
    merged.update(kwargs)
    bot = message.bot
    if bot is None:
        return
    await bot.send_message(
        chat_id=route.chat_id,
        text=shorten_plain_telegram_text(text),
        **merged,
    )


def _topic_recovery_key(route: TelegramRoute) -> tuple[int | str, int] | None:
    if route.message_thread_id is None:
        return None
    return route.chat_id, route.message_thread_id


async def _delete_previous_topic_recovery_prompt(bot: Bot, route: TelegramRoute) -> None:
    key = _topic_recovery_key(route)
    if key is None:
        return
    previous = _topic_recovery_prompts.pop(key, None)
    if previous is None:
        return
    _topic_recovery_requests.pop(previous.request_id, None)
    with contextlib.suppress(Exception):
        await bot.delete_message(chat_id=route.chat_id, message_id=previous.message_id)


async def _send_topic_recovery_prompt(message: Message, route: TelegramRoute, prompt: str) -> None:
    """Ask the user whether to create a fresh Codex session for this topic."""
    bot = message.bot
    if bot is None or route.message_thread_id is None:
        return

    await _delete_previous_topic_recovery_prompt(bot, route)
    request_id = str(uuid.uuid4())
    _topic_recovery_requests[request_id] = _TopicRecoveryRequest(
        chat_id=route.chat_id,
        topic_id=route.message_thread_id,
        prompt=prompt,
        user_id=message.from_user.id if message.from_user else 0,
    )
    sent = await bot.send_message(
        chat_id=route.chat_id,
        message_thread_id=route.message_thread_id,
        text=(
            "This topic looks like a Codex topic, but no active Codex thread is bound to it.\n\n"
            "Create a new Codex session here and run the message you just sent?"
        ),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Create new Codex session",
                        callback_data=f"codex_topic_recover|{request_id}|create",
                    ),
                    InlineKeyboardButton(
                        text="Cancel",
                        callback_data=f"codex_topic_recover|{request_id}|cancel",
                    ),
                ]
            ]
        ),
    )
    key = _topic_recovery_key(route)
    if key is not None and getattr(sent, "message_id", None) is not None:
        _topic_recovery_prompts[key] = _TopicRecoveryPrompt(request_id=request_id, message_id=sent.message_id)


async def _bind_codex_thread_to_topic(
    *,
    context_manager: Any,
    chat_id: int | str,
    topic_id: int,
    thread_id: str,
    user_id: int,
    cwd: str | None = None,
) -> None:
    """Persist that a Codex app-server thread belongs to a Telegram topic."""
    from core.session import ProviderSessionData
    from storage.models import Conversation

    db = context_manager.session
    result = await db.execute(
        select(Conversation).where(
            Conversation.chat_id == int(chat_id),
            Conversation.codex_thread_id == thread_id,
        )
    )
    conv = result.scalars().first()
    if conv is None:
        logger.warning(
            "Codex topic bind: missing conversation for chat_id={} thread_id={}; creating binding row",
            chat_id,
            thread_id,
        )
        conv = Conversation(
            user_id=user_id,
            chat_id=int(chat_id),
            codex_thread_id=thread_id,
            cwd=None if cwd == "default" else cwd,
        )
        db.add(conv)

    conv.user_id = user_id
    conv.chat_id = int(chat_id)
    conv.transport = "telegram"
    conv.topic_id = topic_id
    conv.thread_id = topic_id
    conv.codex_thread_id = thread_id
    if cwd is not None and cwd != "default":
        conv.cwd = cwd
    conv.is_active = True
    provider_sessions = dict(conv.provider_sessions or {})
    provider_sessions["codex"] = ProviderSessionData(session_id=thread_id).to_dict()
    conv.provider_sessions = provider_sessions
    await db.commit()


async def _is_codex_bound_topic(
    thread_id: int,
    context_manager: Any,
    chat_id: int | str | None = None,
) -> bool:
    """Check whether a Telegram thread is bound to a Codex session."""
    return await _codex_topic_state(thread_id, context_manager, chat_id=chat_id) == _CODEX_TOPIC_BOUND


async def _codex_topic_state(
    thread_id: int,
    context_manager: Any,
    chat_id: int | str | None = None,
) -> str:
    """Classify a Telegram topic for Codex routing."""
    from sqlalchemy import or_, select

    from storage.models import Conversation

    db = context_manager.session
    scope = [
        or_(
            Conversation.thread_id == thread_id,
            Conversation.topic_id == thread_id,
        ),
        Conversation.codex_thread_id.isnot(None),
    ]
    if chat_id is not None:
        scope.append(Conversation.chat_id == int(chat_id))
    stmt = select(Conversation).where(
        *scope,
        Conversation.is_active.is_(True),
    )
    result = await db.execute(stmt)
    conv = result.scalars().first()
    if conv is not None:
        logger.debug(f"Codex topic check: chat_id={chat_id}, thread_id={thread_id}, state=bound, conv=id={conv.id}")
        return _CODEX_TOPIC_BOUND

    stmt = select(Conversation).where(*scope)
    result = await db.execute(stmt)
    conv = result.scalars().first()
    if conv is not None:
        logger.debug(
            f"Codex topic check: chat_id={chat_id}, thread_id={thread_id}, state=recoverable, conv=id={conv.id}"
        )
        return _CODEX_TOPIC_RECOVERABLE

    logger.debug(f"Codex topic check: chat_id={chat_id}, thread_id={thread_id}, state=not_codex")
    return _CODEX_TOPIC_NOT_CODEX


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
    global _current_bot
    bot = message.bot
    if bot is None:
        logger.warning("_execute_codex_prompt: bot is None, returning")
        return
    _current_bot = bot

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
    """Handle /codex <prompt> with the persistent app-server architecture."""
    global _current_bot
    bot = message.bot
    if bot is None:
        return
    _current_bot = bot

    route = TelegramRoute.from_message(message)
    chat_id = route.chat_id
    user_id = message.from_user.id if message.from_user else 0
    session_key = SessionKey.from_telegram_message(chat_id, route.message_thread_id)

    if route.message_thread_id is not None:
        state = await _codex_topic_state(route.message_thread_id, context_manager, chat_id=route.chat_id)
        prompt = _topic_prompt_text(message)
        if state == _CODEX_TOPIC_RECOVERABLE:
            await _send_topic_recovery_prompt(message, route, prompt)
            return
        if state != _CODEX_TOPIC_BOUND:
            await message.answer(
                "Codex is only available from the main chat screen.\n\n"
                "Switch to <b>All</b> and send <code>/codex &lt;prompt&gt;</code> there.",
                parse_mode="HTML",
                **route.send_kwargs(),
            )
            return
    else:
        # In main chat — extract prompt after /codex
        prompt = _command_args(message.text or "", "codex")

    if not prompt:
        await message.answer(
            "<b>Usage:</b> <code>/codex &lt;prompt&gt;</code>\n\n"
            "<b>Commands:</b>\n"
            "- <code>/codex status</code> — Show session status\n"
            "- <code>/codex cd &lt;path&gt;</code> — Change working directory\n"
            "- <code>/codex pwd</code> — Show working directory\n"
            "- <code>/codex threads</code> — List sessions\n"
            "- <code>/codex archive</code> — Archive current session\n"
            "- <code>/codex switch &lt;id&gt;</code> — Switch session\n"
            "- <code>/codex !command</code> — Execute shell command\n"
            "- <code>/codex @path</code> — Read file at path\n"
            "- <code>/codex new</code> — Start a fresh session\n"
            "- <code>/screenshot</code> — Capture terminal screenshot\n\n"
            "<b>Example:</b> <code>/codex list all Python files</code>",
            parse_mode="HTML",
            **route.send_kwargs(),
        )
        return

    # Check daemon readiness.
    if not codex_daemon.is_alive():
        await message.answer(
            "Codex daemon is not running. Please restart the bot.",
            **route.send_kwargs(),
        )
        return

    orchestrator.ensure_transport_handlers()
    _ensure_global_orch(orchestrator)

    # Delegate sub-command routing and execution to the Orchestrator.
    # For non-streaming results we just send the returned text.
    # For streaming results (_execute_codex_prompt) the Orchestrator provides
    # callbacks and the handler manages DraftStream.
    prefix, rest = parse_instruction_prefix(prompt)

    # Determine if this should be treated as a streaming prompt or a command.
    stripped = prompt.strip().lower()
    is_prompt = (
        stripped
        not in {
            "new",
            "status",
            "pwd",
            "threads",
            "archive",
        }
        and not stripped.startswith("cd ")
        and not stripped.startswith("switch ")
        and prefix not in {"slash", "file"}
    )

    if is_prompt:
        await _execute_codex_prompt(message, route, context_manager, orchestrator, prompt)
        return

    # Special handling for "/codex new" — create a forum topic.
    if stripped == "new":
        await _handle_codex_new(message, route, context_manager, orchestrator, session_key, user_id)
        return

    # Non-streaming command — use Orchestrator.handle_message.
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


# ---------------------------------------------------------------------------
# Codex-bound topic message handler
# ---------------------------------------------------------------------------


class IsCodexBoundTopic(BaseFilter):
    """Filter: catch candidate text messages in Telegram forum topics."""

    async def __call__(self, message: Message, context_manager: Any | None = None) -> bool:
        if message.message_thread_id is None:
            logger.debug("IsCodexBoundTopic: message_thread_id is None, skipping")
            return False
        if message.text is None:
            logger.debug("IsCodexBoundTopic: text is None, skipping")
            return False
        return not message.text.strip().startswith("/codex")


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
    prompt = _topic_prompt_text(message)

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
    """Switch AI provider without losing other provider context."""
    from bot.handlers.messages import (
        _load_session_data,
        _resolve_provider_conversation,
        _save_session_data,
    )

    user_id = message.from_user.id
    route = TelegramRoute.from_message(message)
    thread_id = route.storage_thread_id
    session_key = SessionKey.from_telegram_message(route.chat_id, route.message_thread_id)

    prompt = message.text or ""
    if prompt.startswith("/model"):
        prompt = prompt[len("/model") :].strip()

    if not prompt:
        available = orchestrator.providers.list_available()
        lines = ["**Usage:** `/model <provider>`", "", "**Available providers:**"]
        for name in available:
            lines.append(f"- `{name}`")
        await message.answer(
            "\n".join(lines),
            parse_mode="Markdown",
            **route.send_kwargs(),
        )
        return

    provider_name = prompt.lower()
    if provider_name not in orchestrator.providers.list_available():
        await message.answer(
            f"❌ Unknown provider: `{provider_name}`",
            parse_mode="Markdown",
            **route.send_kwargs(),
        )
        return

    user = await context_manager.get_or_create_user(user_id)
    conversation = await context_manager.get_or_create_conversation(
        user_id,
        thread_id=thread_id,
        chat_id=route.chat_id,
    )

    session_data = await _load_session_data(conversation, session_key)

    # Save current provider bucket before switching.
    if user.preferred_provider:
        old_bucket = session_data.get_or_create_bucket(user.preferred_provider)
        old_bucket.session_id = str(conversation.id)

    # Switch active provider.
    user.preferred_provider = provider_name
    session_manager.set_active_provider(session_key, provider_name)

    # Resolve or create the provider-specific conversation.
    provider_conv = await _resolve_provider_conversation(
        context_manager, session_key, session_data, user_id, thread_id, provider_name
    )

    await _save_session_data(provider_conv, session_key)
    await context_manager.session.commit()

    await message.answer(
        f"✅ Switched to `{provider_name}`\\.\n_Messages in this thread are now isolated per provider\\._",
        parse_mode="MarkdownV2",
        **route.send_kwargs(),
    )


# ---------------------------------------------------------------------------
# /shell command handler
# ---------------------------------------------------------------------------


@router.message(Command("shell"))
async def cmd_shell(
    message: Message,
    orchestrator: Orchestrator,
    context_manager: ContextManager | None = None,
) -> None:
    """Handle AI-assisted `/shell <task>` and raw `/shell !<command>`."""
    route = TelegramRoute.from_message(message)
    session_key = SessionKey.from_telegram_message(route.chat_id, route.message_thread_id)
    prompt = message.text or ""
    if prompt.startswith("/shell"):
        prompt = prompt[len("/shell") :].strip()

    if not prompt or prompt.lower() in {"-h", "help", "--help"}:
        await message.answer(
            "Usage:\n"
            "/shell <natural language task>\n"
            "/shell !<command>\n"
            "/shell -- <command>\n\n"
            "The natural-language form asks the active AI provider to propose a command first. "
            "Use the raw forms when you already know the exact command.",
            **route.send_kwargs(),
        )
        return

    _ensure_global_orch(orchestrator)

    request = parse_shell_request(prompt)
    if not request.text:
        await message.answer(
            "Usage:\n/shell <natural language task>\n/shell !<command>\n/shell -- <command>",
            **route.send_kwargs(),
        )
        return

    if request.mode == "ai":
        await _propose_shell_telegram(message, route, orchestrator, request.text, session_key, context_manager)
        return

    command = request.text
    if orchestrator.shell_is_dangerous(command):
        approval_id = str(uuid.uuid4())
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Run",
                        callback_data=f"shell_approve:{approval_id}:confirm",
                    ),
                    InlineKeyboardButton(
                        text="Cancel",
                        callback_data=f"shell_approve:{approval_id}:cancel",
                    ),
                ]
            ]
        )
        orchestrator.pending_shell_commands[approval_id] = {
            "command": command,
            "message": message,
            "route": route,
            "session_key": session_key,
        }
        await message.answer(
            f"Dangerous command detected:\n```\n{command}\n```\nDo you want to execute it?",
            reply_markup=keyboard,
            parse_mode="Markdown",
            **route.send_kwargs(),
        )
        return

    await _execute_shell_telegram(message, route, orchestrator, command, session_key)


async def _propose_shell_telegram(
    message: Message,
    route: TelegramRoute,
    orchestrator: Orchestrator,
    request: str,
    session_key: SessionKey,
    context_manager: ContextManager | None,
) -> None:
    """Ask the active chat provider for a shell command proposal."""
    status_msg = await message.answer(
        "Generating shell command proposal...",
        **route.send_kwargs(),
    )

    try:
        provider_name: str | None = None
        model_name: str | None = None
        if context_manager is not None and message.from_user is not None:
            user = await context_manager.get_or_create_user(message.from_user.id)
            provider_name = user.preferred_provider
            model_name = user.preferred_model

        provider = orchestrator.providers.get_provider(provider_name)
        if provider is None:
            provider = orchestrator.providers.get_provider(None)
            model_name = None
        if provider is None:
            await status_msg.edit_text("No AI provider is available for shell command generation.")
            return

        if model_name is None:
            model_name = getattr(provider, "default_model", None)

        response = await provider.chat(
            build_shell_proposal_messages(request),
            model=model_name,
            temperature=0.1,
            max_tokens=800,
        )
        proposal = parse_shell_command_proposal(response.content)
    except Exception as exc:
        logger.exception("Shell command proposal failed")
        await status_msg.edit_text(f"Could not generate a shell command proposal: {exc}")
        return

    if not proposal.command:
        await status_msg.edit_text(
            format_shell_proposal_html(proposal),
            parse_mode="HTML",
        )
        return

    approval_id = str(uuid.uuid4())
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Run", callback_data=f"shell_ai:{approval_id}:run"),
                InlineKeyboardButton(text="Revise", callback_data=f"shell_ai:{approval_id}:revise"),
                InlineKeyboardButton(text="Cancel", callback_data=f"shell_ai:{approval_id}:cancel"),
            ]
        ]
    )
    orchestrator.pending_shell_commands[approval_id] = {
        "command": proposal.command,
        "message": message,
        "route": route,
        "session_key": session_key,
        "proposal": proposal,
    }
    await status_msg.edit_text(
        format_shell_proposal_html(proposal),
        reply_markup=keyboard,
        parse_mode="HTML",
    )


async def _execute_shell_telegram(
    message: Message,
    route: TelegramRoute,
    orchestrator: Orchestrator,
    command: str,
    session_key: SessionKey,
) -> None:
    """Execute a shell command and send the result back to the user."""
    status_msg = await message.answer(
        "Executing shell command...",
        **route.send_kwargs(),
    )
    try:
        result = await orchestrator.shell_provider.execute(command, session_id=session_key.to_string())
        rendered = fmt.format_shell_execution_markdown(command, result)
        toolbar_handler.set_last_reply(session_key, rendered)
        if len(rendered) > 12000:
            file_bytes = rendered.encode("utf-8")
            await status_msg.delete()
            await message.answer_document(
                document=BufferedInputFile(file_bytes, filename="shell_output.md"),
                caption=f"Shell output for: `{command}`",
                parse_mode="Markdown",
                **route.send_kwargs(),
            )
            return

        with contextlib.suppress(Exception):
            await status_msg.delete()
        sent = await send_rich_message(
            bot_token=_bot_token(),
            chat_id=route.chat_id,
            markdown_text=rendered,
            message_thread_id=route.message_thread_id,
            direct_messages_topic_id=route.direct_messages_topic_id,
            business_connection_id=route.business_connection_id,
        )
        if not sent:
            await message.answer(rendered, parse_mode="Markdown", **route.send_kwargs())
    except TimeoutError:
        await status_msg.edit_text(
            f"Command timed out after 30 seconds:\n```\n{command}\n```",
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.exception("Shell command execution failed")
        await status_msg.edit_text(
            f"Error executing command:\n```\n{exc}\n```",
            parse_mode="Markdown",
        )


# ---------------------------------------------------------------------------
# Inline button callbacks
# ---------------------------------------------------------------------------


@router.callback_query(F.data.startswith("codex_stop|"))
async def handle_codex_stop_callback(
    callback_query: CallbackQuery,
    orchestrator: Orchestrator,
) -> None:
    """Handle the 'Stop generating' inline button."""
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

    sm = orchestrator.session_manager
    if sm is not None and sm.is_turn_active(session_key):
        await sm.cancel_turn(session_key)
        await callback_query.answer("Turn interrupted.", show_alert=False)
        msg = callback_query.message
        if isinstance(msg, Message):
            with contextlib.suppress(Exception):
                await msg.edit_text("_Interrupted._")
    else:
        await callback_query.answer("No active turn.", show_alert=False)


@router.callback_query(F.data.startswith("codex_topic_recover|"))
async def handle_codex_topic_recovery_callback(
    callback_query: CallbackQuery,
    context_manager: Any,
    orchestrator: Orchestrator,
) -> None:
    """Handle create/cancel for a recoverable Codex forum topic."""
    data = callback_query.data
    if data is None:
        await callback_query.answer("Invalid recovery request.", show_alert=True)
        return
    try:
        _, request_id, decision = data.split("|", 2)
    except ValueError:
        await callback_query.answer("Invalid recovery request.", show_alert=True)
        return

    request = _topic_recovery_requests.pop(request_id, None)
    msg = callback_query.message
    if not isinstance(msg, Message):
        await callback_query.answer("Message unavailable.", show_alert=True)
        return

    key = (msg.chat.id, msg.message_thread_id) if msg.message_thread_id is not None else None
    if key is not None:
        existing = _topic_recovery_prompts.get(key)
        if existing is not None and existing.request_id == request_id:
            _topic_recovery_prompts.pop(key, None)

    with contextlib.suppress(Exception):
        await msg.delete()

    if request is None:
        await callback_query.answer("Request expired or already handled.", show_alert=True)
        return
    if decision != "create":
        await callback_query.answer("Cancelled.", show_alert=False)
        return

    if not codex_daemon.is_alive():
        await callback_query.answer("Codex daemon is not running.", show_alert=True)
        return

    route = TelegramRoute(
        chat_id=request.chat_id,
        message_thread_id=request.topic_id,
    )
    session_key = SessionKey.from_telegram_message(request.chat_id, request.topic_id)
    try:
        info = await orchestrator.codex_new_session(session_key, context_manager.session, request.user_id)
        thread_id = info["thread_id"]
        sm = orchestrator.session_manager
        if sm is not None:
            sm.set_topic_id(thread_id, request.topic_id)
        await _bind_codex_thread_to_topic(
            context_manager=context_manager,
            chat_id=request.chat_id,
            topic_id=request.topic_id,
            thread_id=thread_id,
            user_id=request.user_id,
            cwd=info.get("cwd"),
        )
        await callback_query.answer("Created.", show_alert=False)
        await _execute_codex_prompt(
            msg,
            route,
            context_manager,
            orchestrator,
            request.prompt,
            user_id_override=request.user_id,
        )
    except Exception as exc:
        logger.exception("Failed to recover Codex topic")
        await callback_query.answer("Failed to create session.", show_alert=True)
        await _codex_reply(msg, f"Codex error: {exc}", route, request.topic_id)


@router.callback_query(F.data.startswith("shell_ai:"))
async def handle_shell_ai_callback(
    callback_query: CallbackQuery,
    orchestrator: Orchestrator,
) -> None:
    """Handle AI shell proposal inline button callbacks."""
    data = callback_query.data
    if data is None:
        await callback_query.answer("Invalid callback data", show_alert=True)
        return
    parts = data.split(":", 2)
    if len(parts) < 3:
        await callback_query.answer("Invalid callback data", show_alert=True)
        return

    approval_id = parts[1]
    decision = parts[2]
    pending = orchestrator.pending_shell_commands.pop(approval_id, None)
    if pending is None:
        await callback_query.answer("Request expired or already handled.", show_alert=True)
        return

    command = pending["command"]
    message = pending["message"]
    route = pending["route"]
    session_key = pending["session_key"]

    msg = callback_query.message
    if not isinstance(msg, Message):
        await callback_query.answer("Message unavailable.", show_alert=True)
        return

    if decision == "cancel":
        with contextlib.suppress(Exception):
            await msg.edit_text(f"Cancelled shell proposal:\n```\n{command}\n```", parse_mode="Markdown")
        await callback_query.answer("Cancelled")
        return

    if decision == "revise":
        with contextlib.suppress(Exception):
            await msg.edit_text(
                "Not executed. Send `/shell <revised task>` for a new proposal, "
                "or `/shell !<command>` to run a raw command.",
                parse_mode="Markdown",
            )
        await callback_query.answer("Not executed")
        return

    if decision != "run":
        await callback_query.answer("Invalid shell action", show_alert=True)
        return

    if orchestrator.shell_is_dangerous(command):
        confirm_id = str(uuid.uuid4())
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Run", callback_data=f"shell_approve:{confirm_id}:confirm"),
                    InlineKeyboardButton(text="Cancel", callback_data=f"shell_approve:{confirm_id}:cancel"),
                ]
            ]
        )
        orchestrator.pending_shell_commands[confirm_id] = {
            "command": command,
            "message": message,
            "route": route,
            "session_key": session_key,
        }
        with contextlib.suppress(Exception):
            await msg.edit_text(
                f"Dangerous command detected:\n```\n{command}\n```\nDo you want to execute it?",
                reply_markup=keyboard,
                parse_mode="Markdown",
            )
        await callback_query.answer("Confirmation required")
        return

    with contextlib.suppress(Exception):
        await msg.delete()
    await callback_query.answer("Executing...")
    await _execute_shell_telegram(message, route, orchestrator, command, session_key)


@router.callback_query(F.data.startswith("shell_approve:"))
async def handle_shell_approve_callback(
    callback_query: CallbackQuery,
    orchestrator: Orchestrator,
) -> None:
    """Handle shell approval inline button callbacks."""
    data = callback_query.data
    if data is None:
        await callback_query.answer("Invalid callback data", show_alert=True)
        return
    parts = data.split(":", 2)
    if len(parts) < 3:
        await callback_query.answer("Invalid callback data", show_alert=True)
        return

    approval_id = parts[1]
    decision = parts[2]
    pending = orchestrator.pending_shell_commands.pop(approval_id, None)

    if pending is None:
        await callback_query.answer("Request expired or already handled.", show_alert=True)
        return

    command = pending["command"]
    message = pending["message"]
    route = pending["route"]
    session_key = pending["session_key"]

    msg = callback_query.message
    if not isinstance(msg, Message):
        await callback_query.answer("Message unavailable.", show_alert=True)
        return

    if decision == "cancel":
        with contextlib.suppress(Exception):
            await msg.edit_text(
                f"Cancelled:\n```\n{command}\n```",
                parse_mode="Markdown",
            )
        await callback_query.answer("Cancelled")
        return

    # decision == "confirm"
    with contextlib.suppress(Exception):
        await msg.delete()
    await callback_query.answer("Executing...")
    await _execute_shell_telegram(message, route, orchestrator, command, session_key)


# ---------------------------------------------------------------------------
# /screenshot command handler
# ---------------------------------------------------------------------------


@router.message(Command("screenshot"))
async def cmd_screenshot(message: Message) -> None:
    """Capture the terminal window and send it as a photo."""
    route = TelegramRoute.from_message(message)
    await send_screenshot_to_chat(message, route)
