"""Telegram startup configuration and environment checks."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

from aiogram.types import BotCommand
from loguru import logger


class StartupBot(Protocol):
    async def set_my_commands(self, commands: list[BotCommand], **kwargs: Any) -> bool:
        """Set the bot command menu."""

    async def get_me(self) -> Any:
        """Return the bot user object."""

    async def send_message(self, chat_id: int, text: str, **kwargs: Any) -> Any:
        """Send a Telegram message."""


TELEGRAM_BOT_COMMANDS: tuple[BotCommand, ...] = (
    BotCommand(command="start", description="Open the Telegodex menu"),
    BotCommand(command="help", description="Show help and available commands"),
    BotCommand(command="new", description="Start a new AI chat"),
    BotCommand(command="clear", description="Clear the current AI chat"),
    BotCommand(command="settings", description="Open provider and model settings"),
    BotCommand(command="codex", description="Start or control a Codex session"),
    BotCommand(command="model", description="Switch the AI provider"),
    BotCommand(command="shell", description="Run a shell command through Telegodex"),
    BotCommand(command="send", description="Send a local file from this machine"),
    BotCommand(command="history", description="Browse conversation history"),
    BotCommand(command="status", description="Show the current session status"),
    BotCommand(command="stop", description="Interrupt the active Codex or shell task"),
    BotCommand(command="live", description="Toggle live session status"),
    BotCommand(command="last", description="Resend the last assistant reply"),
    BotCommand(command="screenshot", description="Capture the current desktop"),
)


def _extra_field(obj: Any, name: str) -> Any:
    """Read pydantic extra fields without depending on aiogram's type stubs."""
    if hasattr(obj, name):
        return getattr(obj, name)
    extra = getattr(obj, "model_extra", None)
    if isinstance(extra, dict):
        return extra.get(name)
    return None


async def configure_bot_commands(bot: StartupBot) -> bool:
    """Synchronize the Telegram command menu.

    This is intentionally non-fatal. BotFather remains useful for global bot
    metadata, but the runtime command menu should follow the code that actually
    handles the commands.
    """
    try:
        await bot.set_my_commands(list(TELEGRAM_BOT_COMMANDS))
    except Exception as exc:
        logger.warning(
            f"Telegram command menu sync failed: {type(exc).__name__}: {exc}"
        )
        return False

    logger.info(
        "Telegram command menu synced: "
        + ", ".join(f"/{command.command}" for command in TELEGRAM_BOT_COMMANDS)
    )
    return True


def _threaded_mode_warning(username: str | None) -> str:
    bot_label = f"@{username}" if username else "this bot"
    return (
        "Telegodex startup check: Telegram Threaded Mode appears to be disabled "
        f"for {bot_label}.\n\n"
        "Open BotFather, select this bot, and enable Threaded Mode so private "
        "AI chatbot conversations can use separate topics.\n\n"
        "This check is for Telegram private AI chatbot topics. Forum supergroup "
        "topics are separate and still require group Topics plus bot admin "
        "permissions."
    )


async def check_threaded_mode(
    bot: StartupBot,
    admin_ids: Sequence[int],
) -> bool:
    """Check Telegram private-chat Threaded Mode and notify admins if absent."""
    try:
        me = await bot.get_me()
    except Exception as exc:
        logger.warning(
            f"Telegram getMe startup check failed: {type(exc).__name__}: {exc}"
        )
        return False

    has_topics_enabled = _extra_field(me, "has_topics_enabled")
    if has_topics_enabled is True:
        logger.info("Telegram private-chat Threaded Mode is enabled")
        return True

    username = _extra_field(me, "username")
    warning = _threaded_mode_warning(username)
    logger.warning(warning.replace("\n", " "))

    if not admin_ids:
        logger.warning(
            "Threaded Mode warning could not be sent because no admin IDs are configured"
        )
        return False

    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, warning)
        except Exception as exc:
            logger.warning(
                "Failed to notify admin "
                f"{admin_id} about Threaded Mode: {type(exc).__name__}: {exc}"
            )

    return False


async def run_telegram_startup_checks(
    bot: StartupBot,
    admin_ids: Sequence[int],
) -> None:
    """Run Telegram platform checks that should not block bot startup."""
    await configure_bot_commands(bot)
    await check_threaded_mode(bot, admin_ids)
