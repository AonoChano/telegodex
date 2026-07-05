"""Telegram UI helpers for AI provider switching."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.types import Message

from bot.utils.routing import TelegramRoute
from core.orchestrator import Orchestrator
from core.session import SessionKey, session_manager
from storage.context_manager import ContextManager

LoadSessionData = Callable[[Any, SessionKey], Awaitable[Any]]
ResolveProviderConversation = Callable[[ContextManager, SessionKey, Any, int, str | None, str], Awaitable[Any]]
SaveSessionData = Callable[[Any, SessionKey], Awaitable[None]]
# 处理 /model 命令

def model_prompt_from_message(text: str) -> str:
    prompt = text or ""
    if prompt.startswith("/model"):
        prompt = prompt[len("/model") :].strip()
    return prompt


async def handle_model_command(
    message: Message,
    context_manager: ContextManager,
    orchestrator: Orchestrator,
    *,
    load_session_data: LoadSessionData | None = None,
    resolve_provider_conversation: ResolveProviderConversation | None = None,
    save_session_data: SaveSessionData | None = None,
    active_session_manager: Any = session_manager,
) -> None:
    """Switch AI provider without losing other provider context."""
    if load_session_data is None or resolve_provider_conversation is None or save_session_data is None:
        from bot.handlers.chat_sessions import (
            load_session_data as _load_session_data,
            resolve_provider_conversation as _resolve_provider_conversation,
            save_session_data as _save_session_data,
        )

        load_session_data = load_session_data or _load_session_data
        resolve_provider_conversation = resolve_provider_conversation or _resolve_provider_conversation
        save_session_data = save_session_data or _save_session_data

    user_id = message.from_user.id
    route = TelegramRoute.from_message(message)
    thread_id = route.storage_thread_id
    session_key = SessionKey.from_telegram_message(route.chat_id, route.message_thread_id)

    prompt = model_prompt_from_message(message.text or "")
    available = orchestrator.providers.list_available()
    if not prompt:
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
    if provider_name not in available:
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

    session_data = await load_session_data(conversation, session_key)

    if user.preferred_provider:
        old_bucket = session_data.get_or_create_bucket(user.preferred_provider)
        old_bucket.session_id = str(conversation.id)

    user.preferred_provider = provider_name
    active_session_manager.set_active_provider(session_key, provider_name)

    provider_conv = await resolve_provider_conversation(
        context_manager,
        session_key,
        session_data,
        user_id,
        thread_id,
        provider_name,
    )

    await save_session_data(provider_conv, session_key)
    await context_manager.session.commit()

    await message.answer(
        f"✅ Switched to `{provider_name}`\\.\n_Messages in this thread are now isolated per provider\\._",
        parse_mode="MarkdownV2",
        **route.send_kwargs(),
    )

