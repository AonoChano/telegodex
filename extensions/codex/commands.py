"""CodexBridge instruction support — ``/``, ``!``, ``@`` prefix routing.

When a user sends ``/codex /status``, ``/codex !ls``, or ``/codex @path``,
we route the input to the appropriate RPC call and return draft suggestions.
"""

from __future__ import annotations

from typing import Any

from loguru import logger


def parse_instruction_prefix(text: str) -> tuple[str | None, str]:
    """Detect the instruction prefix and return ``(prefix, rest)``.

    Returns:
        ``("slash", rest)``, ``("shell", rest)``, ``("file", rest)``,
        or ``(None, text)`` for normal chat input.
    """
    stripped = text.strip()
    if not stripped:
        return None, text

    if stripped.startswith("/"):
        return "slash", stripped[1:]
    if stripped.startswith("!"):
        return "shell", stripped[1:]
    if stripped.startswith("@"):
        return "file", stripped[1:]

    return None, text


async def list_skills(transport: Any) -> list[dict[str, Any]]:
    """Call ``skills/list`` and return the list of available skills."""
    try:
        resp = await transport.send_request("skills/list", {})
        return resp.get("skills", [])
    except Exception as exc:
        logger.warning(f"Commands: skills/list failed: {exc}")
        return []


async def list_directory(transport: Any, path: str) -> list[dict[str, Any]]:
    """Call ``fs/readDirectory`` and return directory entries."""
    try:
        resp = await transport.send_request("fs/readDirectory", {"path": path})
        return resp.get("entries", [])
    except Exception as exc:
        logger.warning(f"Commands: fs/readDirectory({path}) failed: {exc}")
        return []


def format_slash_suggestions(skills: list[dict[str, Any]]) -> str:
    """Format the skills list as Rich Markdown."""
    if not skills:
        return "No skills available."

    lines = ["**Available skills:**", ""]
    for skill in skills[:10]:  # cap at 10
        name = skill.get("name", "unknown")
        desc = skill.get("description", "")
        lines.append(f"- `/{name}` — {desc}")

    if len(skills) > 10:
        lines.append(f"  ... and {len(skills) - 10} more")

    return "\n".join(lines)


def format_file_suggestions(entries: list[dict[str, Any]]) -> str:
    """Format directory entries as Rich Markdown."""
    if not entries:
        return "No matching files."

    lines = ["**Files in directory:**", ""]
    for entry in entries[:15]:
        name = entry.get("name", "unknown")
        entry_type = entry.get("type", "")
        icon = " " if entry_type == "directory" else " "
        lines.append(f"- {icon} `{name}`")

    if len(entries) > 15:
        lines.append(f"  ... and {len(entries) - 15} more")

    return "\n".join(lines)