"""History command: paginated conversation message viewer."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import desc, func, select

from bot.utils.routing import TelegramRoute
from storage import ContextManager
from storage.models import ConversationMessage

router = Router(name="history")

PAGE_SIZE = 10


def _history_keyboard(
    page: int, total_pages: int, conversation_id: int
) -> InlineKeyboardMarkup:
    """Build pagination keyboard for history."""
    nav: list[InlineKeyboardButton] = []
    if page > 1:
        nav.append(
            InlineKeyboardButton(
                text="⬅️ Previous",
                callback_data=f"history:{conversation_id}:{page - 1}",
            )
        )
    nav.append(
        InlineKeyboardButton(
            text=f"{page}/{total_pages}",
            callback_data="history:ignore",
        )
    )
    if page < total_pages:
        nav.append(
            InlineKeyboardButton(
                text="Next ➡️",
                callback_data=f"history:{conversation_id}:{page + 1}",
            )
        )
    return InlineKeyboardMarkup(inline_keyboard=[nav])


async def _fetch_history_page(
    db,
    conversation_id: int,
    page: int,
    page_size: int = PAGE_SIZE,
) -> tuple[list[ConversationMessage], int]:
    """Fetch a page of messages and total count."""
    count_result = await db.execute(
        select(func.count(ConversationMessage.id)).where(
            ConversationMessage.conversation_id == conversation_id
        )
    )
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(desc(ConversationMessage.created_at))
        .offset(offset)
        .limit(page_size)
    )
    messages = list(result.scalars().all())
    return messages, total


def _format_messages(messages: list[ConversationMessage]) -> str:
    """Format a list of messages into Markdown text."""
    lines: list[str] = []
    for msg in reversed(messages):
        role_icon = "👤" if msg.role == "user" else "🤖"
        lines.append(f"{role_icon} **{msg.role.capitalize()}**")
        content = msg.content[:800]
        if len(msg.content) > 800:
            content += "…"
        lines.append(content)
        lines.append("")
    text = "\n".join(lines).strip()
    return text or "📭 No messages on this page."


@router.message(Command("history"))
async def cmd_history(
    message: Message,
    context_manager: ContextManager,
) -> None:
    """Handle /history [page] command."""
    route = TelegramRoute.from_message(message)
    user_id = message.from_user.id if message.from_user else 0

    # Parse optional page number
    text = message.text or ""
    parts = text.split()
    page = 1
    if len(parts) > 1:
        try:
            page = int(parts[1])
        except ValueError:
            page = 1
    if page < 1:
        page = 1

    thread_id = route.storage_thread_id
    conversation = await context_manager.get_or_create_conversation(
        user_id, thread_id=thread_id, chat_id=route.chat_id
    )

    messages, total = await _fetch_history_page(
        context_manager.session, conversation.id, page
    )

    if not messages and total == 0:
        await message.answer(
            "📭 当前对话没有历史消息。",
            **route.send_kwargs(),
        )
        return

    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    if page > total_pages:
        page = total_pages
        messages, total = await _fetch_history_page(
            context_manager.session, conversation.id, page
        )
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    text = _format_messages(messages)
    keyboard = _history_keyboard(page, total_pages, conversation.id)

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=keyboard,
        **route.send_kwargs(),
    )


@router.callback_query(F.data.startswith("history:"))
async def handle_history_callback(
    callback_query: CallbackQuery,
    context_manager: ContextManager,
) -> None:
    """Handle history pagination inline buttons."""
    data = callback_query.data
    if data is None:
        await callback_query.answer("Invalid callback")
        return

    parts = data.split(":")
    if len(parts) != 3:
        await callback_query.answer("Invalid callback")
        return

    _, conv_id_str, page_str = parts
    if conv_id_str == "ignore":
        await callback_query.answer()
        return

    try:
        conversation_id = int(conv_id_str)
        page = int(page_str)
    except ValueError:
        await callback_query.answer("Invalid callback")
        return

    messages, total = await _fetch_history_page(
        context_manager.session, conversation_id, page
    )

    if not messages:
        await callback_query.answer("No messages on this page.")
        return

    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    text = _format_messages(messages)
    keyboard = _history_keyboard(page, total_pages, conversation_id)

    await callback_query.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
    await callback_query.answer()
