"""Shared helpers for Telegram Codex command routing."""

from __future__ import annotations

from aiogram.types import Message

from extensions.codex.commands import parse_instruction_prefix

CODEX_USAGE_HTML = (
    "<b>Usage:</b> <code>/codex &lt;prompt&gt;</code>\n\n"
    "<b>Commands:</b>\n"
    "- <code>/codex status</code> — Show session status\n"
    "- <code>/codex cd &lt;path&gt;</code> — Change working directory\n"
    "- <code>/codex pwd</code> — Show working directory\n"
    "- <code>/codex threads</code> — List sessions\n"
    "- <code>/codex archive</code> — Archive current session\n"
    "- <code>/codex switch &lt;id&gt;</code> — Switch session\n"
    "- <code>/codex !command</code> — Execute shell command\n"
    "- <code>/codex @path</code> — Read file at path\n"
    "- <code>/codex new</code> — Start a fresh session\n"
    "- <code>/codex resume &lt;thread-id&gt;</code> — Resume a Codex thread in a topic\n\n"
    "<b>Example:</b> <code>/codex new</code>"
)

_NON_STREAMING_COMMANDS = {
    "new",
    "status",
    "pwd",
    "threads",
    "archive",
}


def command_args(text: str, command: str) -> str:
    """Return text after a Telegram command, accepting /command@botname."""
    stripped = text.strip()
    prefix = f"/{command}"
    if not stripped.startswith(prefix):
        return stripped
    rest = stripped[len(prefix) :]
    if rest.startswith("@"):
        if " " not in rest:
            return ""
        rest = rest.split(" ", 1)[1]
    return rest.strip()


def topic_prompt_text(message: Message) -> str:
    """Return user prompt text inside a Codex topic, without a leading /codex."""
    return command_args(message.text or "", "codex")


def resume_thread_id(prompt: str) -> str | None:
    """Return the requested Codex thread id for ``resume <thread-id>``."""
    stripped = prompt.strip()
    if not stripped.lower().startswith("resume "):
        return None
    thread_id = stripped.split(None, 1)[1].strip()
    return thread_id or None


def is_streaming_prompt(prompt: str) -> bool:
    """Return whether a Codex command should run through streaming prompt flow."""
    prefix, _ = parse_instruction_prefix(prompt)
    stripped = prompt.strip().lower()
    return (
        stripped not in _NON_STREAMING_COMMANDS
        and not stripped.startswith("cd ")
        and not stripped.startswith("resume ")
        and not stripped.startswith("switch ")
        and prefix not in {"slash", "file"}
    )
