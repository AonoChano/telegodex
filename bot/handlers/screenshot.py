"""Telegram-native desktop screenshot commands and monitor picker."""

from __future__ import annotations

import html
from contextlib import suppress

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.types import (
    User as TelegramUser,
)
from loguru import logger
from sqlalchemy import select

from bot.utils.routing import TelegramRoute
from i18n import resolve_locale, tr
from storage.context_manager import ContextManager
from storage.models import User
from utils.screenshot import (
    DisplayMonitor,
    capture_desktop_screenshot,
    list_display_monitors,
)

router = Router(name="screenshot")

_CALLBACK_PREFIX = "screenshot:"
_CALLBACK_DATA_LIMIT = 64


async def _resolve_user_locale(
    context_manager: ContextManager | None,
    user: TelegramUser | None,
) -> str:
    fallback_code = user.language_code if user else None
    if context_manager is None or user is None:
        return resolve_locale(None, fallback_code)

    result = await context_manager.session.execute(select(User).where(User.id == user.id))
    stored_user = result.scalar_one_or_none()
    return resolve_locale(
        getattr(stored_user, "ui_language", None) if stored_user else None,
        fallback_code,
    )


def _monitor_callback_data(user_id: int, monitor: DisplayMonitor) -> str:
    prefix = f"{_CALLBACK_PREFIX}{user_id}:"
    available = _CALLBACK_DATA_LIMIT - len(prefix.encode("utf-8"))
    identifier = monitor.identifier.encode("utf-8")[:available].decode("utf-8", errors="ignore")
    return f"{prefix}{identifier}"


def build_monitor_keyboard(
    monitors: list[DisplayMonitor],
    user_id: int,
    locale: str,
) -> InlineKeyboardMarkup:
    """Build one full-width row for each available display."""
    rows: list[list[InlineKeyboardButton]] = []
    for monitor in monitors:
        key = "bot.screenshot.monitor_button_primary" if monitor.is_primary else "bot.screenshot.monitor_button"
        rows.append(
            [
                InlineKeyboardButton(
                    text=tr(
                        key,
                        locale,
                        name=monitor.name,
                        width=monitor.width,
                        height=monitor.height,
                    ),
                    callback_data=_monitor_callback_data(user_id, monitor),
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _send_monitor_screenshot(
    message: Message,
    route: TelegramRoute,
    locale: str,
    monitor: DisplayMonitor | None,
) -> bool:
    png_bytes = await capture_desktop_screenshot(monitor)
    if png_bytes is None:
        await message.answer(
            tr("bot.screenshot.capture_failed", locale),
            **route.send_kwargs(),
        )
        return False

    monitor_label = monitor.name if monitor else tr("bot.screenshot.default_monitor", locale)
    try:
        await message.answer_photo(
            photo=BufferedInputFile(png_bytes, filename="screenshot.png"),
            caption=tr("bot.screenshot.caption", locale, monitor=monitor_label),
            **route.send_kwargs(),
        )
    except Exception as exc:
        logger.warning(f"Failed to send desktop screenshot: {exc}")
        await message.answer(
            tr("bot.screenshot.send_failed", locale, error=html.escape(str(exc))),
            **route.send_kwargs(),
        )
        return False
    return True


@router.message(Command("screenshot"))
async def cmd_screenshot(
    message: Message,
    context_manager: ContextManager | None = None,
) -> None:
    """Capture the only display or ask the user which display to capture."""
    route = TelegramRoute.from_message(message)
    locale = await _resolve_user_locale(context_manager, message.from_user)
    monitors = list_display_monitors()

    if len(monitors) > 1:
        user_id = message.from_user.id if message.from_user else 0
        await message.answer(
            tr("bot.screenshot.select_monitor", locale),
            reply_markup=build_monitor_keyboard(monitors, user_id, locale),
            **route.send_kwargs(),
        )
        return

    await _send_monitor_screenshot(
        message,
        route,
        locale,
        monitors[0] if monitors else None,
    )


@router.callback_query(F.data.startswith(_CALLBACK_PREFIX))
async def handle_screenshot_callback(
    callback: CallbackQuery,
    context_manager: ContextManager | None = None,
) -> None:
    """Capture the display selected by the user who opened the picker."""
    locale = await _resolve_user_locale(context_manager, callback.from_user)
    data = callback.data or ""
    parts = data.split(":", maxsplit=2)
    if len(parts) != 3 or not parts[1].isdigit():
        await callback.answer(tr("bot.screenshot.monitor_unavailable", locale), show_alert=True)
        return

    owner_id = int(parts[1])
    if callback.from_user.id != owner_id:
        await callback.answer(tr("bot.screenshot.picker_owner_mismatch", locale), show_alert=True)
        return

    monitor = next(
        (candidate for candidate in list_display_monitors() if _monitor_callback_data(owner_id, candidate) == data),
        None,
    )
    if monitor is None or not isinstance(callback.message, Message):
        await callback.answer(tr("bot.screenshot.monitor_unavailable", locale), show_alert=True)
        return

    await callback.answer(tr("bot.screenshot.capturing", locale))
    with suppress(Exception):
        await callback.message.edit_reply_markup(reply_markup=None)

    route = TelegramRoute.from_message(callback.message)
    if await _send_monitor_screenshot(callback.message, route, locale, monitor):
        with suppress(Exception):
            await callback.message.delete()
