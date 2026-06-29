"""Telegram /screenshot command handling."""

from __future__ import annotations

from aiogram.types import Message

from bot.utils.routing import TelegramRoute
from utils.screenshot import send_screenshot_to_chat


async def handle_screenshot_command(message: Message) -> None:
    """Capture the terminal window and send it as a photo."""
    route = TelegramRoute.from_message(message)
    await send_screenshot_to_chat(message, route)
