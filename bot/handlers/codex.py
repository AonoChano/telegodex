"""CodexBridge v2 handler — /codex command with persistent app-server daemon.

Routes user prompts through the JSON-RPC app-server, streams results via
draft messages, and persists final output as a Rich Message.
"""

from __future__ import annotations

import asyncio
from typing import Any

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message
from loguru import logger

from bot.utils.rich_messages import (
    send_rich_message,
    send_rich_message_draft,
    send_message_draft,
    new_draft_id,
)
from bot.utils.routing import TelegramRoute
from config import settings
from extensions.codex.approvals import ApprovalHandler
from extensions.codex.commands import (
    parse_instruction_prefix,
    list_skills,
    list_directory,
    format_slash_suggestions,
    format_file_suggestions,
)
from extensions.codex.daemon import codex_daemon
from extensions.codex.session import CodexSessionManager
from storage import ContextManager

router = Router(name="codex")

# Draft limits for codex streaming.
DRAFT_FLUSH_CHARS = 200
DRAFT_MAX_CALLS_PER_ID = 6

# Global session manager and approval handler.
session_manager = CodexSessionManager(codex_daemon)
approval_handler = ApprovalHandler()

# Bot instance stored for approval message routing.
_current_bot: Bot | None = None


# ---------------------------------------------------------------------------
# Forum topic helpers
# ---------------------------------------------------------------------------


async def _ensure_codex_forum_topic(
    message: Message,
    chat_id: int | str,
    context_manager: ContextManager,
    codex_thread_id: str,
) -> int | None:
    """Create a dedicated forum topic for this Codex session if needed.

    Returns the ``message_thread_id`` of the topic, or ``None`` if creation
    fails or the chat is not a forum.
    """
    db = context_manager.session
    from sqlalchemy import select
    from storage.models import Conversation

    user_id = message.from_user.id if message.from_user else 0

    # Check if an active conversation with a thread_id already exists.
    stmt = select(Conversation).where(
        Conversation.user_id == user_id,
        Conversation.codex_thread_id == codex_thread_id,
    )
    result = await db.execute(stmt)
    conv = result.scalars().first()

    if conv and conv.thread_id is not None:
        return conv.thread_id

    # Create forum topic.
    try:
        topic = await message.bot.create_forum_topic(
            chat_id=chat_id,
            name=f"Codex: {codex_thread_id[:12]}...",
        )
        topic_id = topic.message_thread_id
        logger.info(
            f"Codex: created forum topic {topic_id} for thread {codex_thread_id}"
        )

        if conv is not None:
            conv.thread_id = topic_id
        else:
            # Find any conversation for this codex thread.
            stmt = select(Conversation).where(
                Conversation.codex_thread_id == codex_thread_id,
            )
            result = await db.execute(stmt)
            conv = result.scalars().first()
            if conv:
                conv.thread_id = topic_id

        await db.commit()
        return topic_id
    except Exception as exc:
        logger.warning(f"Codex: failed to create forum topic: {exc}")
        # Not a forum or bot lacks permission — fall back to main chat.
        if conv and conv.thread_id is not None:
            return conv.thread_id
        return None


def _codex_send_kwargs(route: TelegramRoute, topic_id: int | None) -> dict[str, Any]:
    """Build send kwargs, adding ``message_thread_id`` when a forum topic exists."""
    kwargs = dict(route.send_kwargs())
    if topic_id is not None:
        kwargs["message_thread_id"] = topic_id
    return kwargs


# ---------------------------------------------------------------------------
# JSON-RPC Notification bridge
# ---------------------------------------------------------------------------

_NOTIFICATION_QUEUES: dict[int | str, asyncio.Queue[tuple[str, dict[str, Any]]]] = {}


async def _on_codex_notification(method: str, params: dict[str, Any]) -> None:
    """Global notification handler: route to the correct chat_id queue.

    Notifications are fanned out to all active session queues. In a
    multi-user setup, the handler routes by looking up thread_id from params.
    """
    thread_id = params.get("threadId", "")
    logger.debug(f"Codex notification: {method} thread={thread_id}")

    # Fan out to all registered queues (simplified: send to all).
    for queue in list(_NOTIFICATION_QUEUES.values()):
        try:
            queue.put_nowait((method, params))
        except asyncio.QueueFull:
            pass


async def _on_codex_server_request(method: str, params: dict[str, Any]) -> dict[str, Any] | None:
    """Global server request handler: send approval messages, then delegate to ApprovalHandler."""
    # Send approval message to Telegram if we know the target chat.
    if method in ("item/commandExecution/requestApproval", "item/fileChange/requestApproval"):
        thread_id = params.get("threadId", "")
        chat_id = session_manager.reverse_lookup(thread_id)
        if chat_id is not None and _current_bot is not None:
            approval_id = params.get("approvalId", params.get("itemId", "unknown"))
            if method == "item/commandExecution/requestApproval":
                text = ApprovalHandler.format_command_approval_markdown(approval_id, params)
            else:
                text = ApprovalHandler.format_file_change_approval_markdown(approval_id, params)
            keyboard = ApprovalHandler.build_approval_keyboard(approval_id)
            try:
                await _current_bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=keyboard,
                )
            except Exception as exc:
                logger.warning(f"Codex: failed to send approval message to chat_id={chat_id}: {exc}")
        else:
            logger.warning(
                f"Codex: cannot route approval request — "
                f"no chat_id found for thread_id={thread_id} (bot={_current_bot is not None})"
            )

    return await approval_handler.handle_server_request(method, params)


# Register notification handlers on the daemon transport.
def _register_transport_handlers() -> None:
    transport = codex_daemon.transport
    if transport is not None:
        transport._on_notification = _on_codex_notification
        transport._on_server_request = _on_codex_server_request


# ---------------------------------------------------------------------------
# Streaming helpers
# ---------------------------------------------------------------------------


def _bot_token() -> str:
    token = settings.telegram_bot_token
    if hasattr(token, "get_secret_value"):
        return token.get_secret_value()
    return token


async def _stream_turn(
    message: Message,
    route: TelegramRoute,
    chat_id: int | str,
    session,
    topic_id: int | None = None,
) -> str:
    """Stream turn output via draft messages. Returns the final markdown text."""
    bot_token = _bot_token()
    use_draft = message.chat.type == "private"
    draft_id = new_draft_id() if use_draft else 0
    draft_call_count = 0
    full_text_parts: list[str] = []

    # Use forum topic thread_id if available, otherwise route's thread_id.
    thread_id = topic_id if topic_id is not None else route.draft_thread_id()

    # Create a notification queue for this turn.
    queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()
    _NOTIFICATION_QUEUES[chat_id] = queue

    async def _push_draft(text: str) -> None:
        nonlocal draft_call_count
        if not use_draft or not text or draft_call_count >= DRAFT_MAX_CALLS_PER_ID:
            return
        ok = await send_rich_message_draft(
            bot_token=bot_token,
            chat_id=route.chat_id,
            markdown_text=text,
            draft_id=draft_id,
            message_thread_id=thread_id,
        )
        if not ok:
            await send_message_draft(
                bot_token=bot_token,
                chat_id=route.chat_id,
                text=text,
                draft_id=draft_id,
                message_thread_id=thread_id,
            )
        draft_call_count += 1

    try:
        while True:
            try:
                method, params = await asyncio.wait_for(
                    queue.get(), timeout=120.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"Codex turn timeout for chat_id={chat_id}")
                await session_manager.cancel_turn(chat_id)
                full_text_parts.append("\n\n_Codex turn timed out._")
                break

            if method == "turn/completed":
                # Final turn notification — add usage footer.
                turn = params.get("turn", {})
                usage = turn.get("usage", {})
                if usage:
                    footer = (
                        f"\n\n---\n"
                        f"Input: {usage.get('inputTokens', 0)} | "
                        f"Output: {usage.get('outputTokens', 0)} | "
                        f"Cache: {usage.get('cachedInputTokens', 0)}"
                    )
                    full_text_parts.append(footer)
                    await _push_draft("".join(full_text_parts))
                session.turn_completed.set()
                break

            elif method == "item/agentMessage/delta":
                delta = params.get("delta", "")
                if delta:
                    full_text_parts.append(delta)
                    accumulated = "".join(full_text_parts)
                    await session_manager.stream_accumulate(chat_id, delta)
                    # Flush draft every DRAFT_FLUSH_CHARS chars.
                    if len(accumulated) % DRAFT_FLUSH_CHARS < len(delta):
                        await _push_draft(accumulated)

            elif method == "item/started":
                item_type = params.get("item", {}).get("type", "")
                label = params.get("item", {}).get("label", "")
                if item_type == "command_execution":
                    cmd = params.get("item", {}).get("command", "")
                    block = f"\n\n+ + + Exec: `{cmd}`"
                    if label:
                        block += f" ({label})"
                    block += "\n"
                    full_text_parts.append(block)
                    await _push_draft("".join(full_text_parts))
                elif item_type == "reasoning":
                    block = "\n\n+ + + Thinking..."
                    full_text_parts.append(block)

            elif method == "item/completed":
                item_type = params.get("item", {}).get("type", "")
                if item_type == "command_execution":
                    exit_code = params.get("item", {}).get("exitCode", "")
                    output = params.get("item", {}).get("output", "")
                    block = f"\nExit code: {exit_code}"
                    if output:
                        block += f"\n```\n{output}\n```"
                    block += "\n"
                    full_text_parts.append(block)
                    await _push_draft("".join(full_text_parts))

            elif method == "error":
                error_msg = params.get("message", "Unknown error")
                full_text_parts.append(f"\n\n_ERROR: {error_msg}_")
                await _push_draft("".join(full_text_parts))

    finally:
        _NOTIFICATION_QUEUES.pop(chat_id, None)

    return "".join(full_text_parts).strip()


# ---------------------------------------------------------------------------
# /codex command handler
# ---------------------------------------------------------------------------


@router.message(Command("codex"))
async def cmd_codex_v2(message: Message, context_manager: ContextManager) -> None:
    """Handle /codex <prompt> with the persistent app-server architecture."""
    global _current_bot
    _current_bot = message.bot

    route = TelegramRoute.from_message(message)
    chat_id = route.chat_id
    user_id = message.from_user.id if message.from_user else 0

    # Codex only works from the main chat (All), not inside conversation threads.
    if route.message_thread_id is not None:
        await message.answer(
            "Codex is only available from the main chat screen.\n\n"
            "Switch to <b>All</b> and send <code>/codex &lt;prompt&gt;</code> there.",
            parse_mode="HTML",
            **route.send_kwargs(),
        )
        return

    # Extract prompt.
    prompt = message.text or ""
    if prompt.startswith("/codex"):
        prompt = prompt[len("/codex"):].strip()

    if not prompt:
        await message.answer(
            "<b>Usage:</b> <code>/codex &lt;prompt&gt;</code>\n\n"
            "<b>Commands:</b>\n"
            "- <code>/codex /status</code> — Show Codex configuration\n"
            "- <code>/codex !command</code> — Execute shell command\n"
            "- <code>/codex @path</code> — Read file at path\n"
            "- <code>/codex new</code> — Start a fresh session\n\n"
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

    # Ensure transport handlers are registered.
    _register_transport_handlers()

    # Parse instruction prefix.
    prefix, rest = parse_instruction_prefix(prompt)

    # --- /codex new ---
    if prompt.strip().lower() == "new":
        try:
            session = await session_manager.new_session(chat_id)
            topic_id = await _ensure_codex_forum_topic(
                message, chat_id, context_manager, session.thread_id
            )
            topic_info = " — started in this topic" if topic_id else ""
            await message.answer(
                f"Started a new Codex session.\nThread: `{session.thread_id}`{topic_info}",
                **_codex_send_kwargs(route, topic_id),
            )
        except Exception as exc:
            logger.exception("Codex: failed to start new session")
            await message.answer(
                f"Failed to start new session: {exc}",
                **route.send_kwargs(),
            )
        return

    # --- /codex /slash command ---
    if prefix == "slash":
        transport = codex_daemon.transport
        if transport is None:
            await message.answer(
                "Codex daemon is not ready.", **route.send_kwargs()
            )
            return

        # Show skill suggestions as draft.
        skills = await list_skills(transport)
        suggestion_text = format_slash_suggestions(skills)
        await message.answer(suggestion_text, **route.send_kwargs())
        return

    # --- /codex !shell command ---
    if prefix == "shell":
        try:
            session = await session_manager.get_or_create_session(
                db=context_manager.session,
                chat_id=chat_id,
                user_id=user_id,
            )
        except Exception as exc:
            logger.exception("Codex: session creation failed")
            await message.answer(
                f"Session error: {exc}", **route.send_kwargs()
            )
            return

        await session_manager.execute_shell(chat_id, rest)
        await message.answer(
            f"Executing: `{rest}`", **route.send_kwargs()
        )
        return

    # --- /codex @file path ---
    if prefix == "file":
        transport = codex_daemon.transport
        if transport is None:
            await message.answer(
                "Codex daemon is not ready.", **route.send_kwargs()
            )
            return

        # Read directory for matching files.
        entries = await list_directory(transport, rest or ".")
        suggestion_text = format_file_suggestions(entries)
        await message.answer(suggestion_text, **route.send_kwargs())
        return

    # --- Normal chat prompt ---
    # Send typing indicator.
    await message.bot.send_chat_action(
        chat_id=route.chat_id,
        action="typing",
        message_thread_id=route.message_thread_id,
        business_connection_id=route.business_connection_id,
    )

    # Get or create session.
    try:
        session = await session_manager.get_or_create_session(
            db=context_manager.session,
            chat_id=chat_id,
            user_id=user_id,
        )
    except Exception as exc:
        logger.exception("Codex: session creation failed")
        await message.answer(
            f"Failed to initialize Codex session: {exc}",
            **route.send_kwargs(),
        )
        return

    # Ensure a dedicated forum topic exists for this Codex session.
    topic_id = await _ensure_codex_forum_topic(
        message, chat_id, context_manager, session.thread_id
    )

    try:
        # Start the turn.
        await session_manager.start_turn(chat_id, prompt)

        # Stream the output into the forum topic.
        final_text = await _stream_turn(message, route, chat_id, session, topic_id)

        if not final_text:
            final_text = "Codex completed with no output."

        # Persist final result.
        success = await send_rich_message(
            bot_token=_bot_token(),
            chat_id=route.chat_id,
            markdown_text=final_text,
            message_thread_id=topic_id,
            direct_messages_topic_id=route.direct_messages_topic_id,
            business_connection_id=route.business_connection_id,
        )
        if not success:
            await message.answer(
                final_text,
                **_codex_send_kwargs(route, topic_id),
            )

    except Exception as exc:
        logger.exception("Codex: turn failed")
        await message.answer(
            f"Codex error: {exc}",
            **_codex_send_kwargs(route, topic_id),
        )