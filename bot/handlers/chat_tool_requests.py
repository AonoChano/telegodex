"""Normal-chat tool request handling."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from ai import Message as AIMessage
from ai import MessageRole
from bot.utils.latex import normalize_rich_markdown_latex
from bot.utils.routing import TelegramRoute
from core.orchestrator.chat_tools import (
    build_tool_result_message,
    normalize_permission_mode,
    parse_chat_tool_request,
    permission_mode_label,
)
from core.orchestrator.shell_pipeline import ShellCommandProposal, format_shell_proposal_html
from core.session import SessionKey
from storage import ContextManager
from storage.models import Conversation


def looks_like_chat_tool_request_prefix(text: str) -> bool:
    stripped = text.lstrip()
    if not stripped:
        return False
    if stripped.startswith("{") and "telegodex_tool" in stripped[:500]:
        return True
    return stripped.startswith("```") and "telegodex_tool" in stripped[:700]


def has_chat_tool_request(text: str) -> bool:
    return parse_chat_tool_request(text) is not None


async def handle_chat_tool_request(
    *,
    tool_response_text: str,
    message: Message,
    route: TelegramRoute,
    context_manager: ContextManager,
    conversation: Conversation,
    messages_with_system: list[AIMessage],
    provider: Any,
    orchestrator: Any | None,
    session_key: SessionKey,
    permission_mode: str | None,
    model_name: str | None,
    temperature: float,
    max_output_tokens: int,
) -> tuple[str, str | None, int | None] | None:
    """Handle a normal-chat tool request.

    Returns replacement assistant text/model/tokens for full-access execution.
    Returns ``None`` when the request was blocked or deferred to an inline button.
    """
    request = parse_chat_tool_request(tool_response_text)
    if request is None:
        return None

    mode = normalize_permission_mode(permission_mode)
    label = permission_mode_label(mode)

    if mode == "chat":
        text = (
            "权限当前为 `仅对话`。我不会运行命令或调用本地工具。\n\n"
            "需要我查看本地环境、执行命令或使用工具时，请在设置里把权限切到 `用户确认` "
            "或 `⚠️ 完全访问` 后再继续。"
        )
        await context_manager.add_message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=text,
        )
        await message.answer(text, parse_mode="Markdown", **route.send_kwargs())
        return None

    if mode == "confirm":
        if orchestrator is None or not hasattr(orchestrator, "pending_shell_commands"):
            text = "Telegodex detected a tool request, but approval handling is not available in this chat runtime."
            await context_manager.add_message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=text,
            )
            await message.answer(text, **route.send_kwargs())
            return None

        approval_id = f"chat-{uuid4().hex[:12]}"
        orchestrator.pending_shell_commands[approval_id] = {
            "command": request.command,
            "message": message,
            "route": route,
            "session_key": session_key,
            "source": "chat_tool",
        }
        proposal = ShellCommandProposal(
            command=request.command,
            explanation=request.reason or "The chat AI requested this command to complete the task.",
            risk=request.risk or f"Permission mode: {label}",
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Run", callback_data=f"shell_ai:{approval_id}:run"),
                    InlineKeyboardButton(text="Cancel", callback_data=f"shell_ai:{approval_id}:cancel"),
                ]
            ]
        )
        await message.answer(
            format_shell_proposal_html(proposal),
            parse_mode="HTML",
            reply_markup=keyboard,
            **route.send_kwargs(),
        )
        audit_text = f"Requested user confirmation for shell command: `{request.command}`"
        await context_manager.add_message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=audit_text,
        )
        return None

    shell_provider = getattr(orchestrator, "shell_provider", None) if orchestrator is not None else None
    if shell_provider is None or not hasattr(shell_provider, "execute"):
        text = "Telegodex full-access tool execution is unavailable because no shell provider is attached."
        await context_manager.add_message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=text,
        )
        await message.answer(text, **route.send_kwargs())
        return None

    current_text = tool_response_text
    current_messages = list(messages_with_system)
    response_model = model_name
    response_tokens: int | None = None
    for _ in range(3):
        request = parse_chat_tool_request(current_text)
        if request is None:
            return current_text, response_model, response_tokens
        result = await shell_provider.execute(request.command, session_id=session_key.to_string())
        current_messages.extend(
            [
                AIMessage(role=MessageRole.ASSISTANT, content=current_text),
                build_tool_result_message(request, result),
            ]
        )
        response = await provider.chat(
            messages=current_messages,
            model=model_name,
            temperature=temperature,
            max_tokens=max_output_tokens,
        )
        current_text = normalize_rich_markdown_latex(response.content)
        response_model = response.model
        response_tokens = response.usage.get("total_tokens") if response.usage else None

    if parse_chat_tool_request(current_text) is not None:
        current_text = "Tool loop stopped after 3 rounds. Please review the latest command result and try again."
    return current_text, response_model, response_tokens
