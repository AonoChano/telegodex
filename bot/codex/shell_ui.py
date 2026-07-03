"""Telegram UI helpers for shell command proposals and execution."""

from __future__ import annotations

import contextlib
import uuid
from collections.abc import Awaitable, Callable

from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger

from bot.codex import formatting as fmt
from bot.handlers import toolbar as toolbar_handler
from bot.utils.rich_messages import send_rich_message
from bot.utils.routing import TelegramRoute
from config import settings
from core.orchestrator import Orchestrator
from core.orchestrator.shell_pipeline import (
    build_shell_proposal_messages,
    format_shell_proposal_html,
    parse_shell_command_proposal,
    parse_shell_request,
)
from core.session import SessionKey
from i18n import resolve_locale, tr
from storage.context_manager import ContextManager

ShellExecutor = Callable[[Message, TelegramRoute, Orchestrator, str, SessionKey], Awaitable[None]]

SHELL_USAGE = (
    "Usage:\n"
    "/shell <natural language task>\n"
    "/shell !<command>\n"
    "/shell -- <command>\n\n"
    "The natural-language form asks the active AI provider to propose a command first. "
    "Use the raw forms when you already know the exact command."
)

SHORT_SHELL_USAGE = "Usage:\n/shell <natural language task>\n/shell !<command>\n/shell -- <command>"
TELEGRAM_TEXT_LIMIT = 4096


def shell_prompt_from_message(text: str) -> str:
    prompt = text or ""
    if prompt.startswith("/shell"):
        prompt = prompt[len("/shell") :].strip()
    return prompt


async def handle_shell_command(
    message: Message,
    orchestrator: Orchestrator,
    context_manager: ContextManager | None = None,
    *,
    ensure_orchestrator: Callable[[Orchestrator], None] | None = None,
    execute_shell: ShellExecutor | None = None,
) -> None:
    """Handle AI-assisted `/shell <task>` and raw `/shell !<command>`."""
    route = TelegramRoute.from_message(message)
    session_key = SessionKey.from_telegram_message(route.chat_id, route.message_thread_id)
    prompt = shell_prompt_from_message(message.text or "")

    if not prompt or prompt.lower() in {"-h", "help", "--help"}:
        await message.answer(SHELL_USAGE, **route.send_kwargs())
        return

    if ensure_orchestrator is not None:
        ensure_orchestrator(orchestrator)

    request = parse_shell_request(prompt)
    if not request.text:
        await message.answer(SHORT_SHELL_USAGE, **route.send_kwargs())
        return

    execute = execute_shell or execute_shell_telegram
    if request.mode == "ai":
        await propose_shell_telegram(message, route, orchestrator, request.text, session_key, context_manager)
        return

    command = request.text
    if orchestrator.shell_is_dangerous(command):
        await send_dangerous_command_prompt(message, route, orchestrator, command, session_key)
        return

    await execute(message, route, orchestrator, command, session_key)


async def send_dangerous_command_prompt(
    message: Message,
    route: TelegramRoute,
    orchestrator: Orchestrator,
    command: str,
    session_key: SessionKey,
) -> None:
    approval_id = str(uuid.uuid4())
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Run",
                    callback_data=f"shell_approve:{approval_id}:confirm",
                ),
                InlineKeyboardButton(
                    text="Cancel",
                    callback_data=f"shell_approve:{approval_id}:cancel",
                ),
            ]
        ]
    )
    orchestrator.pending_shell_commands[approval_id] = {
        "command": command,
        "message": message,
        "route": route,
        "session_key": session_key,
    }
    await message.answer(
        f"Dangerous command detected:\n```\n{command}\n```\nDo you want to execute it?",
        reply_markup=keyboard,
        parse_mode="Markdown",
        **route.send_kwargs(),
    )


async def propose_shell_telegram(
    message: Message,
    route: TelegramRoute,
    orchestrator: Orchestrator,
    request: str,
    session_key: SessionKey,
    context_manager: ContextManager | None,
) -> None:
    """Ask the active chat provider for a shell command proposal."""
    status_msg = await message.answer(
        "Generating shell command proposal...",
        **route.send_kwargs(),
    )

    try:
        provider_name: str | None = None
        model_name: str | None = None
        if context_manager is not None and message.from_user is not None:
            user = await context_manager.get_or_create_user(message.from_user.id)
            provider_name = user.preferred_provider
            model_name = user.preferred_model

        provider = orchestrator.providers.get_provider(provider_name)
        if provider is None:
            provider = orchestrator.providers.get_provider(None)
            model_name = None
        if provider is None:
            await status_msg.edit_text("No AI provider is available for shell command generation.")
            return

        if model_name is None:
            model_name = getattr(provider, "default_model", None)

        response = await provider.chat(
            build_shell_proposal_messages(request),
            model=model_name,
            temperature=0.1,
            max_tokens=800,
        )
        proposal = parse_shell_command_proposal(response.content)
    except Exception as exc:
        logger.exception("Shell command proposal failed")
        await status_msg.edit_text(f"Could not generate a shell command proposal: {exc}")
        return

    if not proposal.command:
        await status_msg.edit_text(
            format_shell_proposal_html(proposal),
            parse_mode="HTML",
        )
        return

    approval_id = str(uuid.uuid4())
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Run", callback_data=f"shell_ai:{approval_id}:run"),
                InlineKeyboardButton(text="Revise", callback_data=f"shell_ai:{approval_id}:revise"),
                InlineKeyboardButton(text="Cancel", callback_data=f"shell_ai:{approval_id}:cancel"),
            ]
        ]
    )
    orchestrator.pending_shell_commands[approval_id] = {
        "command": proposal.command,
        "message": message,
        "route": route,
        "session_key": session_key,
        "proposal": proposal,
    }
    await status_msg.edit_text(
        format_shell_proposal_html(proposal),
        reply_markup=keyboard,
        parse_mode="HTML",
    )


async def execute_shell_telegram(
    message: Message,
    route: TelegramRoute,
    orchestrator: Orchestrator,
    command: str,
    session_key: SessionKey,
) -> None:
    """Execute a shell command and send the result back to the user."""
    status_msg = await message.answer(
        "Executing shell command...",
        **route.send_kwargs(),
    )
    try:
        result = await orchestrator.shell_provider.execute(command, session_id=session_key.to_string())
        rendered = fmt.format_shell_execution_markdown(command, result)
        toolbar_handler.set_last_reply(session_key, rendered)
        if len(rendered) > TELEGRAM_TEXT_LIMIT:
            await _send_shell_output_file(message, route, status_msg, command, result)
            return

        with contextlib.suppress(Exception):
            await status_msg.delete()
        sent = await send_rich_message(
            bot_token=settings.telegram_bot_token,
            chat_id=route.chat_id,
            markdown_text=rendered,
            message_thread_id=route.message_thread_id,
            direct_messages_topic_id=route.direct_messages_topic_id,
            business_connection_id=route.business_connection_id,
        )
        if not sent:
            if len(rendered) > TELEGRAM_TEXT_LIMIT:
                await _send_shell_output_file(message, route, status_msg, command, result)
            else:
                await message.answer(rendered, parse_mode="Markdown", **route.send_kwargs())
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


async def _send_shell_output_file(
    message: Message,
    route: TelegramRoute,
    status_msg: Message,
    command: str,
    result: dict[str, object],
) -> None:
    locale = resolve_locale(None, message.from_user.language_code if message.from_user else None)
    transcript = fmt.format_shell_execution_text(command, result)
    with contextlib.suppress(Exception):
        await status_msg.delete()
    await message.answer_document(
        document=BufferedInputFile(transcript.encode("utf-8"), filename="shell_output.txt"),
        caption=tr("bot.shell.output_file_caption", locale, command=command),
        parse_mode=None,
        **route.send_kwargs(),
    )

async def handle_shell_ai_callback(
    callback_query: CallbackQuery,
    orchestrator: Orchestrator,
    *,
    execute_shell: ShellExecutor | None = None,
) -> None:
    """Handle AI shell proposal inline button callbacks."""
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
            await msg.edit_text(f"Cancelled shell proposal:\n```\n{command}\n```", parse_mode="Markdown")
        await callback_query.answer("Cancelled")
        return

    if decision == "revise":
        with contextlib.suppress(Exception):
            await msg.edit_text(
                "Not executed. Send `/shell <revised task>` for a new proposal, "
                "or `/shell !<command>` to run a raw command.",
                parse_mode="Markdown",
            )
        await callback_query.answer("Not executed")
        return

    if decision != "run":
        await callback_query.answer("Invalid shell action", show_alert=True)
        return

    if orchestrator.shell_is_dangerous(command):
        await edit_dangerous_command_confirmation(msg, orchestrator, command, message, route, session_key)
        await callback_query.answer("Confirmation required")
        return

    with contextlib.suppress(Exception):
        await msg.delete()
    await callback_query.answer("Executing...")
    execute = execute_shell or execute_shell_telegram
    await execute(message, route, orchestrator, command, session_key)


async def edit_dangerous_command_confirmation(
    msg: Message,
    orchestrator: Orchestrator,
    command: str,
    message: Message,
    route: TelegramRoute,
    session_key: SessionKey,
) -> None:
    confirm_id = str(uuid.uuid4())
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Run", callback_data=f"shell_approve:{confirm_id}:confirm"),
                InlineKeyboardButton(text="Cancel", callback_data=f"shell_approve:{confirm_id}:cancel"),
            ]
        ]
    )
    orchestrator.pending_shell_commands[confirm_id] = {
        "command": command,
        "message": message,
        "route": route,
        "session_key": session_key,
    }
    with contextlib.suppress(Exception):
        await msg.edit_text(
            f"Dangerous command detected:\n```\n{command}\n```\nDo you want to execute it?",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )


async def handle_shell_approve_callback(
    callback_query: CallbackQuery,
    orchestrator: Orchestrator,
    *,
    execute_shell: ShellExecutor | None = None,
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
        await msg.delete()
    await callback_query.answer("Executing...")
    execute = execute_shell or execute_shell_telegram
    await execute(message, route, orchestrator, command, session_key)
