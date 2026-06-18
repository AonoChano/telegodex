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
from aiogram.filters import BaseFilter, Command
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from loguru import logger

from bot.handlers import toolbar as toolbar_handler
from bot.streaming import ReactionTracker
from bot.telegram_draft import DraftStream
from bot.utils.rich_messages import send_rich_message
from bot.utils.routing import TelegramRoute
from config import settings
from core.orchestrator import Orchestrator, StreamingCallbacks
from core.session import SessionKey, session_manager
from extensions.codex.commands import parse_instruction_prefix
from extensions.codex.daemon import codex_daemon
from storage.context_manager import ContextManager
from utils.screenshot import send_screenshot_to_chat

router = Router(name="codex")

# Draft limits for codex streaming.
DRAFT_FLUSH_CHARS = 200

_CODEX_TOPIC_BOUND = "bound"
_CODEX_TOPIC_RECOVERABLE = "recoverable"
_CODEX_TOPIC_NOT_CODEX = "not_codex"

# Bot instance stored for approval message routing.
_current_bot: Bot | None = None

# Global Orchestrator reference for transport-level approval callbacks.
_global_orch: Orchestrator | None = None


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


def _ensure_global_orch(orchestrator: Orchestrator) -> None:
    """Cache the Orchestrator instance and wire approval UI sender."""
    global _global_orch
    if _global_orch is None:
        _global_orch = orchestrator
        orchestrator.set_approval_ui_sender(_approval_ui_sender)


async def _approval_ui_sender(method: str, params: dict[str, Any]) -> None:
    """Send approval requests to Telegram using the cached bot instance."""
    if _current_bot is None or _global_orch is None:
        return
    sm = _global_orch.session_manager
    if sm is None:
        return
    thread_id = params.get("threadId", "")
    session_key = sm.reverse_lookup(thread_id)
    if session_key is None:
        return
    approval_id = params.get("approvalId", params.get("itemId", "unknown"))
    if method == "item/commandExecution/requestApproval":
        text = _global_orch.approval_handler.format_command_approval_markdown(approval_id, params)
    else:
        text = _global_orch.approval_handler.format_file_change_approval_markdown(approval_id, params)
    keyboard = _global_orch.approval_handler.build_approval_keyboard(approval_id, params)
    topic_id = sm.get_topic_id(thread_id)
    try:
        await _current_bot.send_message(
            chat_id=session_key.chat_id,
            text=text,
            reply_markup=keyboard,
            message_thread_id=topic_id,
        )
    except Exception as exc:
        logger.warning(f"Codex: failed to send approval message to {session_key}: {exc}")


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

        # Update the database conversation record with the topic_id.
        from sqlalchemy import update

        from storage.models import Conversation

        stmt = update(Conversation).where(Conversation.codex_thread_id == thread_id).values(topic_id=topic_id)
        await context_manager.session.execute(stmt)
        await context_manager.session.commit()

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
        text=text,
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


async def _is_codex_bound_topic(
    thread_id: int,
    context_manager: Any,
) -> bool:
    """Check whether a Telegram thread is bound to a Codex session."""
    return await _codex_topic_state(thread_id, context_manager) == _CODEX_TOPIC_BOUND


async def _codex_topic_state(
    thread_id: int,
    context_manager: Any,
) -> str:
    """Classify a Telegram topic for Codex routing."""
    from sqlalchemy import or_, select

    from storage.models import Conversation

    db = context_manager.session
    stmt = select(Conversation).where(
        or_(
            Conversation.thread_id == thread_id,
            Conversation.topic_id == thread_id,
        ),
        Conversation.codex_thread_id.isnot(None),
        Conversation.is_active.is_(True),
    )
    result = await db.execute(stmt)
    conv = result.scalars().first()
    if conv is not None:
        logger.debug(f"Codex topic check: thread_id={thread_id}, state=bound, conv=id={conv.id}")
        return _CODEX_TOPIC_BOUND

    stmt = select(Conversation).where(
        or_(
            Conversation.thread_id == thread_id,
            Conversation.topic_id == thread_id,
        ),
        Conversation.codex_thread_id.isnot(None),
    )
    result = await db.execute(stmt)
    conv = result.scalars().first()
    if conv is not None:
        logger.debug(f"Codex topic check: thread_id={thread_id}, state=recoverable, conv=id={conv.id}")
        return _CODEX_TOPIC_RECOVERABLE

    logger.debug(f"Codex topic check: thread_id={thread_id}, state=not_codex")
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
    try:
        stop_msg = await bot.send_message(
            chat_id=route.chat_id,
            text="_Codex is working..._",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Stop generating",
                            callback_data=f"codex_stop|{session_key.to_string()}",
                        )
                    ]
                ]
            ),
            message_thread_id=topic_id,
            parse_mode="Markdown",
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

    last_flush_len = 0
    full_accumulated = ""

    async def _on_text_delta(delta: str, accumulated: str) -> None:
        nonlocal last_flush_len, full_accumulated
        full_accumulated = accumulated
        if reaction_tracker is not None:
            await reaction_tracker.set_state("editing")
        if stream is None:
            return
        if len(accumulated) - last_flush_len >= DRAFT_FLUSH_CHARS:
            await stream.push(accumulated)
            last_flush_len = len(accumulated)

    async def _on_item_started(item_type: str, item: dict[str, Any]) -> None:
        if reaction_tracker is not None:
            await reaction_tracker.on_codex_event("item/started", item_type)

    async def _on_turn_completed(turn: dict[str, Any], final_text: str) -> None:
        if reaction_tracker is not None:
            await reaction_tracker.set_state("done")

    callbacks = StreamingCallbacks(
        on_text_delta=_on_text_delta,
        on_item_started=_on_item_started,
        on_turn_completed=_on_turn_completed,
    )

    try:
        final_text = await orchestrator.handle_message_streaming(
            key=session_key,
            text=prompt,
            db=context_manager.session,
            user_id=user_id,
            callbacks=callbacks,
        )

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

    except Exception as exc:
        logger.exception("Codex: turn failed")
        await _codex_reply(
            message,
            f"Codex error: {exc}",
            route,
            topic_id,
        )
    finally:
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

    # Codex only works from the main chat (All), not inside conversation threads.
    if route.message_thread_id is not None:
        is_bound = await _is_codex_bound_topic(route.message_thread_id, context_manager)
        if not is_bound:
            await message.answer(
                "Codex is only available from the main chat screen.\n\n"
                "Switch to <b>All</b> and send <code>/codex &lt;prompt&gt;</code> there.",
                parse_mode="HTML",
                **route.send_kwargs(),
            )
            return
        # In a Codex-bound topic — prompt is the full message text.
        prompt = message.text or ""
    else:
        # In main chat — extract prompt after /codex
        prompt = message.text or ""
        if prompt.startswith("/codex"):
            prompt = prompt[len("/codex") :].strip()

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
    """Filter: match plain text messages in Codex-bound forum topics only."""

    async def __call__(self, message: Message, context_manager: Any | None = None) -> bool:
        if message.message_thread_id is None:
            logger.debug("IsCodexBoundTopic: message_thread_id is None, skipping")
            return False
        if message.text is None:
            logger.debug("IsCodexBoundTopic: text is None, skipping")
            return False
        # Let /codex commands pass through to the command handler.
        is_codex_cmd = message.text.strip().startswith("/codex")
        logger.debug(
            f"IsCodexBoundTopic: thread_id={message.message_thread_id}, "
            f"text={message.text[:30]}..., is_codex_cmd={is_codex_cmd}"
        )
        if is_codex_cmd:
            return False
        if context_manager is None:
            logger.debug("IsCodexBoundTopic: context_manager unavailable")
            return False
        state = await _codex_topic_state(message.message_thread_id, context_manager)
        logger.debug(f"IsCodexBoundTopic: thread_id={message.message_thread_id}, state={state}")
        return state in {_CODEX_TOPIC_BOUND, _CODEX_TOPIC_RECOVERABLE}


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
    prompt = (message.text or "").strip()

    if not prompt:
        return

    # Verify this topic is actually bound to a Codex session.
    topic_id = message.message_thread_id
    if topic_id is None:
        return
    state = await _codex_topic_state(topic_id, context_manager)
    if state == _CODEX_TOPIC_RECOVERABLE:
        await _send_topic_recovery_prompt(message, route, prompt)
        return
    if state != _CODEX_TOPIC_BOUND:
        return

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
    conversation = await context_manager.get_or_create_conversation(user_id, thread_id=thread_id)

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
) -> None:
    """Handle /shell <command> as a standalone alternative to the ! prefix."""
    route = TelegramRoute.from_message(message)
    session_key = SessionKey.from_telegram_message(route.chat_id, route.message_thread_id)
    prompt = message.text or ""
    if prompt.startswith("/shell"):
        prompt = prompt[len("/shell") :].strip()

    if not prompt:
        await message.answer(
            "Usage: `/shell <command>`",
            parse_mode="Markdown",
            **route.send_kwargs(),
        )
        return

    _ensure_global_orch(orchestrator)

    if orchestrator.shell_is_dangerous(prompt):
        approval_id = str(uuid.uuid4())
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="▶ Yes",
                        callback_data=f"shell_approve:{approval_id}:confirm",
                    ),
                    InlineKeyboardButton(
                        text="✕ Cancel",
                        callback_data=f"shell_approve:{approval_id}:cancel",
                    ),
                ]
            ]
        )
        orchestrator.pending_shell_commands[approval_id] = {
            "command": prompt,
            "message": message,
            "route": route,
            "session_key": session_key,
        }
        await message.answer(
            f"Dangerous command detected:\n```\n{prompt}\n```\nDo you want to execute it?",
            reply_markup=keyboard,
            parse_mode="Markdown",
            **route.send_kwargs(),
        )
        return

    await _execute_shell_telegram(message, route, orchestrator, prompt, session_key)


async def _execute_shell_telegram(
    message: Message,
    route: TelegramRoute,
    orchestrator: Orchestrator,
    command: str,
    session_key: SessionKey,
) -> None:
    """Execute a shell command and send the result back to the user."""
    status_msg = await message.answer(
        f"Executing: `{command}`",
        parse_mode="Markdown",
        **route.send_kwargs(),
    )
    try:
        result = await orchestrator.shell_provider.execute(command, session_id=session_key.to_string())
        output = result["stdout"]
        stderr = result["stderr"]
        returncode = result["returncode"]

        lines: list[str] = []
        if output:
            lines.append(output)
        if stderr:
            lines.append(f"[stderr]\n{stderr}")
        lines.append(f"\nExit code: {returncode}")

        full_text = "\n".join(lines).strip()
        toolbar_handler.set_last_reply(session_key, full_text)
        if len(full_text) > 4096:
            file_bytes = full_text.encode("utf-8")
            await status_msg.delete()
            await message.answer_document(
                document=BufferedInputFile(file_bytes, filename="shell_output.txt"),
                caption=f"Output for: `{command}`",
                parse_mode="Markdown",
                **route.send_kwargs(),
            )
        else:
            text = f"```\n{full_text}\n```"
            await status_msg.edit_text(text, parse_mode="Markdown")
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
        await msg.edit_text(
            f"Confirmed. Executing:\n```\n{command}\n```",
            parse_mode="Markdown",
        )
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
