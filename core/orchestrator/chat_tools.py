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

ToolPermissionMode = Literal["chat", "confirm", "full"]

PERMISSION_MODES: tuple[ToolPermissionMode, ...] = ("chat", "confirm", "full")
DEFAULT_PERMISSION_MODE: ToolPermissionMode = "confirm"

PERMISSION_MODE_LABELS: dict[ToolPermissionMode, str] = {
    "chat": "仅对话",
    "confirm": "用户确认",
    "full": "⚠️ 完全访问",
}


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


def permission_mode_label(value: str | None) -> str:
    """Return the human-readable Telegram label for a permission mode."""
    return PERMISSION_MODE_LABELS[normalize_permission_mode(value)]


def build_telegodex_capability_prompt(permission_mode: str | None) -> str:
    """Build the normal-chat system addendum for Telegodex capability awareness."""
    mode = normalize_permission_mode(permission_mode)
    label = permission_mode_label(mode)
    base = (
        "\n\nYou are Telegodex, a Telegram Workbench assistant. You can answer "
        "normal chat questions, explain Telegodex features, and, when permitted, "
        "request local tools through Telegodex. The current tool permission mode "
        f"is `{label}`.\n"
    )
    if mode == "chat":
        return (
            base + "Tool use is disabled. If the user asks you to inspect files, run "
            "commands, or call local capabilities, explain that permissions are "
            "set to `仅对话` and ask them to switch the permission level in Settings."
        )
    return (
        base + "When a local shell command is necessary, do not pretend you ran it. "
        "Respond with only one JSON object, optionally inside a json code fence, "
        "using exactly these fields: telegodex_tool, command, reason, risk. "
        'Set telegodex_tool to "shell". Keep command to one Windows PowerShell '
        "line. Prefer read-only commands unless the user explicitly asks to "
        "change files."
    )


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
    lines = [
        "Telegodex tool result:",
        f"tool: {request.tool}",
        f"command: {request.command}",
        f"exit_code: {exit_code}",
        f"timed_out: {timed_out}",
    ]
    if stdout:
        lines.extend(["stdout:", _limit(stdout)])
    if stderr:
        lines.extend(["stderr:", _limit(stderr)])
    lines.append("Use this result to answer the user. If it failed, explain the failure and propose the next step.")
    return Message(role=MessageRole.SYSTEM, content="\n".join(lines))


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
