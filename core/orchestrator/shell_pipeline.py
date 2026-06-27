"""Natural-language shell command proposal helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html import escape
from typing import Literal

from ai.base import Message, MessageRole

ShellRequestMode = Literal["ai", "raw"]


@dataclass(frozen=True)
class ShellRequest:
    """Parsed `/shell` request."""

    mode: ShellRequestMode
    text: str


@dataclass(frozen=True)
class ShellCommandProposal:
    """Command candidate produced by an AI provider."""

    command: str
    explanation: str = ""
    risk: str = ""


def parse_shell_request(text: str) -> ShellRequest:
    """Parse the body of a `/shell` command.

    `/shell <natural language>` is the default AI-assisted flow.
    `/shell !<command>` and `/shell -- <command>` keep direct raw execution.
    """
    stripped = text.strip()
    if stripped.startswith("!"):
        return ShellRequest(mode="raw", text=stripped[1:].strip())
    if stripped.startswith("--"):
        return ShellRequest(mode="raw", text=stripped[2:].strip())
    return ShellRequest(mode="ai", text=stripped)


def build_shell_proposal_messages(request: str) -> list[Message]:
    """Build a provider-agnostic prompt for command proposal generation."""
    system = (
        "You translate a user's natural-language shell task into one safe, concrete "
        "Windows PowerShell command. Return JSON only with these string fields: "
        "command, explanation, risk. The command field must be a single line and "
        "must not contain Markdown fences. If the request is ambiguous, destructive, "
        "or impossible to satisfy safely, return an empty command and explain why. "
        "Prefer read-only commands unless the user explicitly asks to change files."
    )
    user = f"Task: {request}"
    return [
        Message(role=MessageRole.SYSTEM, content=system),
        Message(role=MessageRole.USER, content=user),
    ]


def parse_shell_command_proposal(text: str) -> ShellCommandProposal:
    """Parse a JSON command proposal from provider text."""
    payload_text = _extract_json_object(text)
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise ValueError("AI provider did not return valid JSON.") from exc

    if not isinstance(payload, dict):
        raise ValueError("AI provider returned JSON, but not an object.")

    command = _single_line(str(payload.get("command") or ""))
    explanation = str(payload.get("explanation") or "").strip()
    risk = str(payload.get("risk") or "").strip()
    return ShellCommandProposal(command=command, explanation=explanation, risk=risk)


def format_shell_proposal_message(proposal: ShellCommandProposal) -> str:
    """Format a proposal for Telegram Markdown."""
    lines = ["Shell command proposal:", "", "```", proposal.command or "(no command proposed)", "```"]
    if proposal.explanation:
        lines.extend(["", f"Why: {proposal.explanation}"])
    if proposal.risk:
        lines.extend(["", f"Risk: {proposal.risk}"])
    if proposal.command:
        lines.extend(["", "Run this command?"])
    return "\n".join(lines)


def format_shell_proposal_html(proposal: ShellCommandProposal) -> str:
    """Format a proposal for Telegram HTML parse mode."""
    command = escape(proposal.command or "(no command proposed)")
    lines = ["Shell command proposal:", "", f"<pre><code>{command}</code></pre>"]
    if proposal.explanation:
        lines.extend(["", f"<b>Why:</b> {escape(proposal.explanation)}"])
    if proposal.risk:
        lines.extend(["", f"<b>Risk:</b> {escape(proposal.risk)}"])
    if proposal.command:
        lines.extend(["", "Run this command?"])
    return "\n".join(lines)


def _extract_json_object(text: str) -> str:
    stripped = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1)
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        return stripped[start : end + 1]
    return stripped


def _single_line(text: str) -> str:
    return " ".join(part.strip() for part in text.splitlines() if part.strip()).strip()
