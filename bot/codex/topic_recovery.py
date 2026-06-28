"""Topic recovery prompt state for Codex-bound Telegram topics."""

from __future__ import annotations

import contextlib
import uuid
from dataclasses import dataclass

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.utils.routing import TelegramRoute


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
