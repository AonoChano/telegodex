"""Normal-chat tool intent helpers.

This module keeps tool parsing and permission wording out of Telegram handlers.
The first supported tool is shell execution because it reuses the existing
ShellProvider and `/shell` approval UX.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Literal

from ai.base import Message, MessageRole
from i18n import tr
from prompts.shell import SHELL_TOOL_RESULT_TEMPLATE
from prompts.telegodex import TELEGODEX_CAPABILITY_CHAT_PROMPT, TELEGODEX_CAPABILITY_TOOL_TEMPLATE

ToolPermissionMode = Literal["chat", "confirm", "full"]

PERMISSION_MODES: tuple[ToolPermissionMode, ...] = ("chat", "confirm", "full")
DEFAULT_PERMISSION_MODE: ToolPermissionMode = "confirm"


@dataclass(frozen=True)
class ChatToolRequest:
    """A tool request emitted by a normal chat provider."""

    tool: Literal["shell"]
    command: str
    reason: str = ""
    risk: str = ""


def normalize_permission_mode(value: str | None) -> ToolPermissionMode:
    """Return a valid permission mode, defaulting safely to user confirmation."""
    if value in PERMISSION_MODES:
        return value
    return DEFAULT_PERMISSION_MODE


def next_permission_mode(value: str | None) -> ToolPermissionMode:
    """Cycle permission modes in the settings menu."""
    current = normalize_permission_mode(value)
    idx = PERMISSION_MODES.index(current)
    return PERMISSION_MODES[(idx + 1) % len(PERMISSION_MODES)]


def permission_mode_label(value: str | None, locale: str | None = None) -> str:
    """Return the human-readable Telegram label for a permission mode."""
    mode = normalize_permission_mode(value)
    return tr(f"core.permission.{mode}", locale or "en")


def build_telegodex_capability_prompt(permission_mode: str | None, locale: str | None = None) -> str:
    """Build the normal-chat system addendum for Telegodex capability awareness."""
    mode = normalize_permission_mode(permission_mode)
    label = permission_mode_label(mode, locale)

    if mode == "chat":
        return "\n\n" + TELEGODEX_CAPABILITY_CHAT_PROMPT

    return "\n\n" + TELEGODEX_CAPABILITY_TOOL_TEMPLATE.format(mode=label)


def parse_chat_tool_request(text: str) -> ChatToolRequest | None:
    """Parse a Telegodex tool request from provider text.

    The parser is intentionally strict: ordinary JSON in an assistant reply
    should not become a tool call unless it declares ``telegodex_tool``.
    """
    for candidate in _json_candidates(text):
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        tool = payload.get("telegodex_tool")
        if tool != "shell":
            continue
        command = _single_line(str(payload.get("command") or ""))
        if not command:
            return None
        return ChatToolRequest(
            tool="shell",
            command=command,
            reason=str(payload.get("reason") or "").strip(),
            risk=str(payload.get("risk") or "").strip(),
        )
    return None


def build_tool_result_message(request: ChatToolRequest, result: dict[str, Any]) -> Message:
    """Format a shell execution result for the model's next turn."""
    stdout = str(result.get("stdout") or "").strip()
    stderr = str(result.get("stderr") or "").strip()
    exit_code = result.get("returncode", result.get("exit_code", "unknown"))
    timed_out = bool(result.get("timeout"))

    output_parts = []
    if stdout:
        output_parts.append(f"stdout:\n{_limit(stdout)}")
    if stderr:
        output_parts.append(f"stderr:\n{_limit(stderr)}")
    output = "\n".join(output_parts)

    content = SHELL_TOOL_RESULT_TEMPLATE.format(
        tool=request.tool,
        command=request.command,
        exit_code=exit_code,
        timed_out=timed_out,
        output=output,
    )
    return Message(role=MessageRole.SYSTEM, content=content)


def _json_candidates(text: str) -> list[str]:
    stripped = text.strip()
    candidates = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL | re.IGNORECASE)
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        candidates.append(stripped[start : end + 1])
    return candidates


def _single_line(text: str) -> str:
    return " ".join(part.strip() for part in text.splitlines() if part.strip()).strip()


def _limit(text: str, limit: int = 6000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]"
