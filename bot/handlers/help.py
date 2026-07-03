"""Help command router with paginated TOC and chapter navigation."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger
from sqlalchemy import select

from bot.help import HelpRenderer, get_help_renderer
from bot.utils.rich_messages import edit_rich_message, send_rich_message
from bot.utils.routing import TelegramRoute
from i18n import resolve_locale, tr
from storage import ContextManager
from storage.models import User

router = Router(name="help")


def _bot_send_kwargs(route: TelegramRoute) -> dict:
    """Build kwargs for ``Bot.send_message`` from a :class:`TelegramRoute`."""
    kwargs: dict = {}
    if route.message_thread_id is not None:
        kwargs["message_thread_id"] = route.message_thread_id
    if route.business_connection_id is not None:
        kwargs["business_connection_id"] = route.business_connection_id
    if route.direct_messages_topic_id is not None:
        kwargs["direct_messages_topic_id"] = route.direct_messages_topic_id
    return kwargs


async def _delete_help_message(message: Message) -> None:
    """Best-effort deletion for replaced help pages."""
    try:
        await message.delete()
    except Exception as exc:
        logger.debug(f"Failed to delete old help message: {exc}")


async def _replace_help_message_content(
    callback: CallbackQuery,
    text: str,
    keyboard: InlineKeyboardMarkup,
) -> bool:
    """Replace a help page while preserving Rich Message output when possible."""
    if callback.message is None:
        return False

    route = TelegramRoute.from_message(callback.message)
    bot_token = callback.bot.token if callback.bot else None
    message_id = getattr(callback.message, "message_id", None)

    if bot_token and message_id is not None:
        edited = await edit_rich_message(
            bot_token=bot_token,
            chat_id=route.chat_id,
            message_id=message_id,
            markdown_text=text,
            business_connection_id=route.business_connection_id,
            reply_markup=keyboard,
        )
        if edited:
            return True

    if bot_token:
        sent = await send_rich_message(
            bot_token=bot_token,
            chat_id=route.chat_id,
            markdown_text=text,
            reply_markup=keyboard,
            message_thread_id=route.message_thread_id,
            direct_messages_topic_id=route.direct_messages_topic_id,
            business_connection_id=route.business_connection_id,
        )
        if sent:
            await _delete_help_message(callback.message)
            return True

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
        return True
    except Exception as exc:
        logger.debug(f"Help plain edit fallback failed: {exc}")

    try:
        await callback.bot.send_message(
            chat_id=route.chat_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=keyboard,
            **_bot_send_kwargs(route),
        )
        await _delete_help_message(callback.message)
        return True
    except Exception as exc:
        logger.debug(f"Help plain send fallback failed: {exc}")
        return False

async def _resolve_locale_from_db(
    context_manager: ContextManager | None, user_id: int, fallback_code: str | None
) -> str:
    """Resolve locale from stored user preference, falling back to Telegram code.

    If *context_manager* is ``None`` (e.g., dependency injection unavailable),
    falls back to *fallback_code* only.
    """
    if context_manager is None:
        return resolve_locale(None, fallback_code)
    result = await context_manager.session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    return resolve_locale(
        getattr(user, "ui_language", None) if user else None,
        fallback_code,
    )


async def send_help_toc(message: Message, locale: str) -> None:
    """Send the help TOC page 1. Can be called from other handlers."""
    renderer = get_help_renderer()
    route = TelegramRoute.from_message(message)
    pages = renderer.get_toc_pages(locale)
    if not pages:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=tr("bot.help.close", locale), callback_data="help:close")]
            ]
        )
        await message.answer(
            tr("bot.help.empty", locale), reply_markup=keyboard, **route.send_kwargs()
        )
        return
    text, keyboard = renderer.render_toc_page(locale, 1)
    await message.answer(text, reply_markup=keyboard, **route.send_kwargs())


@router.message(Command("help"))
async def cmd_help(message: Message, context_manager: ContextManager | None = None) -> None:
    """Handle /help command — send TOC page 1.

    Resolves locale from the user's stored ``ui_language`` preference when
    *context_manager* is injected, falling back to the Telegram client
    ``language_code`` otherwise.
    """
    locale = await _resolve_locale_from_db(
        context_manager,
        message.from_user.id if message.from_user else 0,
        message.from_user.language_code if message.from_user else None,
    )
    await send_help_toc(message, locale)


@router.callback_query(F.data.startswith("help:"))
async def handle_help_callback(
    callback: CallbackQuery, context_manager: ContextManager
) -> None:
    """Handle all help-related inline button callbacks."""
    data = callback.data or ""
    locale = await _resolve_locale_from_db(
        context_manager,
        callback.from_user.id,
        callback.from_user.language_code if callback.from_user else None,
    )
    renderer = get_help_renderer()

    if data == "help:close":
        await _handle_close(callback)
        return

    if data == "help:noop":
        await callback.answer()
        return

    if data.startswith("help:toc:"):
        await _handle_toc_navigation(callback, renderer, locale)
        return

    if data.startswith("help:ch:"):
        await _handle_chapter_navigation(callback, renderer, locale)
        return

    await callback.answer()


async def _handle_close(callback: CallbackQuery) -> None:
    """Close help: delete the message, fall back to removing the keyboard."""
    if callback.message is None:
        await callback.answer()
        return
    try:
        await callback.message.delete()
    except Exception as exc:
        logger.debug(f"Failed to delete help message: {exc}")
        try:
            await callback.message.edit_text(reply_markup=None)
        except Exception:
            pass
    await callback.answer()


async def _handle_toc_navigation(
    callback: CallbackQuery, renderer: HelpRenderer, locale: str
) -> None:
    """Handle TOC pagination: in-place edit, fall back to send-new + delete-old."""
    data = callback.data or ""
    try:
        page = int(data[len("help:toc:") :])
    except ValueError:
        await callback.answer(tr("bot.errors.invalid_callback", locale), show_alert=True)
        return
    text, keyboard = renderer.render_toc_page(locale, page)
    if callback.message is not None:
        await _replace_help_message_content(callback, text, keyboard)
    await callback.answer()


async def _handle_chapter_navigation(
    callback: CallbackQuery, renderer: HelpRenderer, locale: str
) -> None:
    """Handle chapter page navigation with rich in-place editing first."""
    data = callback.data or ""
    parts = data.split(":")
    if len(parts) != 4:
        await callback.answer(tr("bot.errors.invalid_callback", locale), show_alert=True)
        return
    chapter_id = parts[2]
    try:
        page = int(parts[3])
    except ValueError:
        await callback.answer(tr("bot.errors.invalid_callback", locale), show_alert=True)
        return
    rendered = renderer.render_chapter_page(locale, chapter_id, page)
    if rendered is None:
        await callback.answer(tr("bot.help.chapter_not_found", locale), show_alert=True)
        return
    text, keyboard = rendered
    if callback.message is not None:
        await _replace_help_message_content(callback, text, keyboard)
    await callback.answer()
