"""Formatting helpers for Telegram-facing Codex output."""

from __future__ import annotations

import html
import re
from typing import Any

STATUS_TEXT_LIMIT = 900

_TRACE_ID_RE = re.compile(r"[（(]traceid:\s*([^)）]+)[)）]", re.IGNORECASE)
_URL_RE = re.compile(r",\s*url:\s*([^,\s]+)", re.IGNORECASE)
_CF_RAY_RE = re.compile(r",\s*cf-ray:\s*(\S+)", re.IGNORECASE)


def trim_status_text(text: str, limit: int = STATUS_TEXT_LIMIT) -> str:
    """Trim volatile status text so it remains safe for Telegram message edits."""
    normalized = "\n".join(" ".join(line.split()) for line in text.splitlines())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "..."


def format_command_status(
    *,
    command: Any | None = None,
    output_preview: str | None = None,
) -> str:
    """Return a short HTML-safe command status message."""
    title = "Codex is running a command..."
    if command:
        preview = trim_status_text(str(command), 720)
        if preview:
            return f"{title}\n<code>{html.escape(preview)}</code>"
    if output_preview:
        preview = trim_status_text(output_preview, 360)
        if preview:
            return f"{title}\n<pre>{html.escape(preview)}</pre>"
    return title


def is_codex_retry_status_line(text: str) -> bool:
    """Return whether a daemon stderr line is useful live turn status."""
    lowered = text.lower()
    retry_markers = (
        "reconnecting",
        "unexpected status",
        "bad request",
        "forbidden",
        "unauthorized",
        "payment required",
        "insufficient",
        "balance",
        "quota",
        "too many requests",
        "rate limit",
        "request body",
        "only one codex conversation",
        "usage limit",
        "context window",
        "status 4",
        "status 5",
        "timed out",
        "timeout",
        "try again",
        "error:",
    )
    return any(marker in lowered for marker in retry_markers)


def is_generic_unknown_error_line(line: str) -> bool:
    """Return whether *line* is only the structured Codex generic error."""
    normalized = line.strip().strip("_").replace("**", "").replace("`", "")
    normalized = " ".join(normalized.split()).lower()
    prefix = "error: unknown error"
    if not normalized.startswith(prefix):
        return False
    suffix = normalized[len(prefix) :].strip()
    return not suffix or (suffix.startswith("(") and suffix.endswith(")"))


def clean_codex_error_text(text: str, stderr_block: str) -> str:
    """Remove noisy duplicate generic errors when raw stderr has the real cause."""
    lines: list[str] = []
    generic_seen = False
    previous_line: str | None = None

    for line in text.splitlines():
        if is_generic_unknown_error_line(line):
            if stderr_block:
                continue
            if generic_seen:
                continue
            generic_seen = True
        if line == previous_line and line.strip():
            continue
        lines.append(line)
        previous_line = line

    cleaned = "\n".join(lines).strip()
    while "\n\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n\n", "\n\n")
    return cleaned


def markdown_code_fence(text: str, language: str = "text") -> str:
    """Return a Markdown code fence that can contain the given raw text."""
    fence = "```"
    while fence in text:
        fence += "`"
    return f"{fence}{language}\n{text}\n{fence}"


def append_codex_stderr_detail(text: str, stderr_block: str) -> str:
    """Append collected raw Codex stderr to final Telegram output."""
    if not stderr_block:
        return text
    if "Codex runtime detail:" in text:
        return text
    base_text = text.replace(stderr_block, "").strip()
    detail = f"**Codex runtime detail:**\n\n{markdown_code_fence(stderr_block)}"
    if not base_text:
        return detail
    return f"{base_text.rstrip()}\n\n---\n{detail}"


def format_shell_execution_markdown(command: str, result: dict[str, Any]) -> str:
    stdout = str(result.get("stdout") or "").strip()
    stderr = str(result.get("stderr") or "").strip()
    returncode = result.get("returncode")
    ok = returncode == 0
    title = "**Shell command completed**" if ok else "**Shell command failed**"
    lines = [
        title,
        "",
        "**Command**",
        markdown_code_fence(command, language="powershell"),
        "",
        f"**Exit code:** `{returncode}`",
    ]
    if stdout:
        lines.extend(
            [
                "",
                "<details><summary>stdout</summary>",
                "",
                markdown_code_fence(stdout),
                "",
                "</details>",
            ]
        )
    if stderr:
        lines.extend(
            [
                "",
                "<details><summary>stderr</summary>",
                "",
                markdown_code_fence(stderr),
                "",
                "</details>",
            ]
        )
    if not stdout and not stderr:
        lines.extend(["", "_No output._"])
    return "\n".join(lines).strip()


def format_shell_execution_text(command: str, result: dict[str, Any]) -> str:
    """Return a plain-text shell execution transcript for file delivery."""
    stdout = str(result.get("stdout") or "").strip()
    stderr = str(result.get("stderr") or "").strip()
    returncode = result.get("returncode")
    sections = [
        "Shell command completed" if returncode == 0 else "Shell command failed",
        "",
        "Command:",
        command,
        "",
        f"Exit code: {returncode}",
    ]
    if stdout:
        sections.extend(["", "stdout:", stdout])
    if stderr:
        sections.extend(["", "stderr:", stderr])
    if not stdout and not stderr:
        sections.extend(["", "No output."])
    return "\n".join(sections).strip() + "\n"

def format_collected_stderr(lines: list[str]) -> str:
    """Join collected daemon stderr lines into a single user-facing block.

    De-duplicates while preserving order (Codex often repeats the same retry
    banner several times) and collapses to ``\\n`` so it renders as a clean
    block on Telegram Rich Messages.
    """
    seen: set[str] = set()
    unique: list[str] = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            unique.append(line)
    return "\n".join(unique)


def append_unique_runtime_detail(lines: list[str], *texts: str | None) -> None:
    """Append non-empty runtime detail lines once, preserving arrival order."""
    for text in texts:
        detail = (text or "").strip()
        if not detail or is_generic_unknown_error_line(detail):
            continue
        if detail not in lines:
            lines.append(detail)


def format_codex_error_detail_for_status(detail: str) -> str:
    """Make one-line provider errors easier to scan in the stop-button status."""
    trace_id = _TRACE_ID_RE.search(detail)
    url = _URL_RE.search(detail)
    cf_ray = _CF_RAY_RE.search(detail)

    summary = detail
    for match in (trace_id, url, cf_ray):
        if match is not None:
            summary = summary.replace(match.group(0), "")
    summary = summary.strip(" ,，")

    lines: list[str] = []
    if summary:
        lines.append(summary)
    if trace_id is not None:
        lines.append(f"traceid: {trace_id.group(1).strip()}")
    if url is not None:
        lines.append(f"url: {url.group(1).strip()}")
    if cf_ray is not None:
        lines.append(f"cf-ray: {cf_ray.group(1).strip()}")
    return "\n".join(lines) if lines else detail


def format_codex_retry_status(message: str, additional_details: str | None = None) -> str:
    """Build the live Telegram text for an app-server retry notification."""
    lines = ["Codex Reconnecting..."]
    if message.strip():
        lines.append(message.strip())
    if additional_details and additional_details.strip() and additional_details.strip() != message.strip():
        lines.append(format_codex_error_detail_for_status(additional_details.strip()))
    return "\n".join(lines)
