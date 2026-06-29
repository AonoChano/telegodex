"""Topic recovery prompt state for Codex-bound Telegram topics."""

from __future__ import annotations

import contextlib
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from aiogram import Bot
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger

from bot.utils.routing import TelegramRoute
from core.session import SessionKey


@dataclass(frozen=True)
class TopicRecoveryRequest:
    chat_id: int | str
    topic_id: int
    prompt: str
    user_id: int


@dataclass(frozen=True)
class TopicRecoveryPrompt:
    request_id: str
    message_id: int


class TopicRecoveryStore:
    """Track pending topic-recovery prompts by Telegram topic."""

    def __init__(self) -> None:
        self.requests: dict[str, TopicRecoveryRequest] = {}
        self.prompts: dict[tuple[int | str, int], TopicRecoveryPrompt] = {}

    def clear(self) -> None:
        self.requests.clear()
        self.prompts.clear()

    def key_for_route(self, route: TelegramRoute) -> tuple[int | str, int] | None:
        if route.message_thread_id is None:
            return None
        return route.chat_id, route.message_thread_id

    def pop_request(self, request_id: str) -> TopicRecoveryRequest | None:
        return self.requests.pop(request_id, None)

    async def delete_previous_prompt(self, bot: Bot, route: TelegramRoute) -> None:
        key = self.key_for_route(route)
        if key is None:
            return
        previous = self.prompts.pop(key, None)
        if previous is None:
            return
        self.requests.pop(previous.request_id, None)
        with contextlib.suppress(Exception):
            await bot.delete_message(chat_id=route.chat_id, message_id=previous.message_id)

    async def send_prompt(self, message: Message, route: TelegramRoute, prompt: str) -> None:
        """Ask whether to create a fresh Codex session for this topic."""
        bot = message.bot
        if bot is None or route.message_thread_id is None:
            return

        await self.delete_previous_prompt(bot, route)
        request_id = str(uuid.uuid4())
        self.requests[request_id] = TopicRecoveryRequest(
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
        key = self.key_for_route(route)
        if key is not None and getattr(sent, "message_id", None) is not None:
            self.prompts[key] = TopicRecoveryPrompt(request_id=request_id, message_id=sent.message_id)


topic_recovery_store = TopicRecoveryStore()
AsyncCallable = Callable[..., Awaitable[Any]]


async def handle_topic_recovery_callback(
    callback_query: CallbackQuery,
    context_manager: Any,
    orchestrator: Any,
    *,
    codex_daemon: Any,
    bind_codex_thread_to_topic: AsyncCallable,
    execute_codex_prompt: AsyncCallable,
    codex_reply: AsyncCallable,
    store: TopicRecoveryStore = topic_recovery_store,
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

    request = store.requests.pop(request_id, None)
    message = callback_query.message
    if not isinstance(message, Message):
        await callback_query.answer("Message unavailable.", show_alert=True)
        return

    key = (message.chat.id, message.message_thread_id) if message.message_thread_id is not None else None
    if key is not None:
        existing = store.prompts.get(key)
        if existing is not None and existing.request_id == request_id:
            store.prompts.pop(key, None)

    with contextlib.suppress(Exception):
        await message.delete()

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
        session_manager = orchestrator.session_manager
        if session_manager is not None:
            session_manager.set_topic_id(thread_id, request.topic_id)
        await bind_codex_thread_to_topic(
            context_manager=context_manager,
            chat_id=request.chat_id,
            topic_id=request.topic_id,
            thread_id=thread_id,
            user_id=request.user_id,
            cwd=info.get("cwd"),
        )
        await callback_query.answer("Created.", show_alert=False)
        await execute_codex_prompt(
            message,
            route,
            context_manager,
            orchestrator,
            request.prompt,
            user_id_override=request.user_id,
        )
    except Exception as exc:
        logger.exception("Failed to recover Codex topic")
        await callback_query.answer("Failed to create session.", show_alert=True)
        await codex_reply(message, f"Codex error: {exc}", route, request.topic_id)
