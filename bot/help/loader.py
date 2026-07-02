"""Parse and validate Markdown help files with YAML frontmatter."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from loguru import logger

from .scanner import scan_help_documents


@dataclass(frozen=True)
class HelpChapter:
    """A single help chapter parsed from a Markdown file.

    Attributes:
        chapter_id: Filename without the ``.md`` extension.
        title: Human-readable title from YAML frontmatter.
        order: Sort order from frontmatter (positive int).
        pages: Content split by ``---`` page breaks.
    """

    chapter_id: str
    title: str
    order: int
    pages: list[str]


def _log_error(
    log_dir: Path | None,
    file_path: Path,
    error_type: str,
    message: str,
    field: str | None = None,
) -> None:
    """Log a help-file error to logger and append to daily JSONL log.

    Args:
        log_dir: Directory for log files. If ``None``, only logs to logger.
        file_path: Path to the offending file (used for the ``file`` field).
        error_type: Short error category (e.g., ``"missing_field"``).
        message: Human-readable error message.
        field: Optional field name related to the error.
    """
    logger.warning(message)
    if log_dir is None:
        return
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "file": f"{file_path.parent.name}/{file_path.name}",
            "error_type": error_type,
            "field": field,
            "message": message,
        }
        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as e:
        logger.warning(f"Failed to write help error log: {e}")


def _unquote(value: str) -> str:
    """Strip surrounding quotes from a YAML value string."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str] | None:
    """Parse simple YAML frontmatter from Markdown content.

    Expects content to start with a ``---`` line and contain a closing
    ``---`` line. Parses ``key: value`` pairs between them (no nesting).
    Quoted values (``"..."`` or ``'...'``) are unquoted.

    Args:
        content: Full file content as a string.

    Returns:
        ``(frontmatter_dict, remaining_content)`` if frontmatter is present
        and well-formed, otherwise ``None``.
    """
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return None

    closing_idx: int | None = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            closing_idx = i
            break
    if closing_idx is None:
        return None

    frontmatter: dict[str, str] = {}
    for line in lines[1:closing_idx]:
        if not line.strip() or ":" not in line:
            continue
        key, _, value = line.partition(":")
        frontmatter[key.strip()] = _unquote(value)

    remaining = "\n".join(lines[closing_idx + 1 :])
    return frontmatter, remaining


def _split_pages(content: str) -> list[str]:
    """Split content into pages by lines that are exactly ``---``.

    Empty/whitespace-only pages are stripped.

    Args:
        content: Markdown content after frontmatter removal.

    Returns:
        List of non-empty page strings.
    """
    stripped = content.strip()
    if not stripped:
        return []
    pages = re.split(r"\n---\n", stripped)
    return [p.strip() for p in pages if p.strip()]


def load_help_file(path: Path, log_dir: Path | None = None) -> HelpChapter | None:
    """Load and validate a single Markdown help file.

    Parses YAML frontmatter for ``title`` and ``order``, then splits the
    body into pages by ``---`` separators.

    Required frontmatter fields:
        - ``title``: non-empty string.
        - ``order``: positive integer.

    On any error: logs a warning, writes to ``log_dir/<date>.jsonl``, and
    returns ``None``.

    Args:
        path: Path to the ``.md`` help file.
        log_dir: Optional directory for error log files.

    Returns:
        ``HelpChapter`` if valid, otherwise ``None``.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        _log_error(log_dir, path, "read_error", f"Failed to read help file '{path.name}': {e}")
        return None

    parsed = _parse_frontmatter(content)
    if parsed is None:
        _log_error(
            log_dir,
            path,
            "missing_frontmatter",
            f"Help file '{path.name}' has no valid YAML frontmatter",
        )
        return None

    frontmatter, body = parsed

    title = frontmatter.get("title", "")
    if not title or not title.strip():
        _log_error(
            log_dir,
            path,
            "missing_field",
            "YAML frontmatter missing required field: title",
            field="title",
        )
        return None
    title = title.strip()

    order_str = frontmatter.get("order", "")
    try:
        order = int(order_str)
    except (ValueError, TypeError):
        _log_error(
            log_dir,
            path,
            "invalid_field",
            f"YAML frontmatter field 'order' must be an integer, got: {order_str!r}",
            field="order",
        )
        return None
    if order <= 0:
        _log_error(
            log_dir,
            path,
            "invalid_field",
            f"YAML frontmatter field 'order' must be a positive integer, got: {order}",
            field="order",
        )
        return None

    pages = _split_pages(body)

    return HelpChapter(
        chapter_id=path.stem,
        title=title,
        order=order,
        pages=pages,
    )


def load_help_locale(locale_dir: Path, log_dir: Path | None = None) -> list[HelpChapter]:
    """Load all valid help chapters for a locale directory.

    Scans *locale_dir* for ``.md`` files, loads each, and performs semantic
    checks (unique ``chapter_id``, unique ``order``). Valid chapters are
    sorted by ``order``.

    Args:
        locale_dir: Path to a locale's help directory.
        log_dir: Optional directory for error log files.

    Returns:
        Sorted list of ``HelpChapter`` objects (may be empty).
    """
    files = scan_help_documents(locale_dir)

    chapters: list[HelpChapter] = []
    seen_ids: set[str] = set()
    seen_orders: set[int] = set()

    for path in files:
        chapter = load_help_file(path, log_dir)
        if chapter is None:
            continue
        if chapter.chapter_id in seen_ids:
            _log_error(
                log_dir,
                path,
                "duplicate_chapter_id",
                f"Duplicate chapter_id '{chapter.chapter_id}' in locale '{locale_dir.name}'",
                field="chapter_id",
            )
            continue
        if chapter.order in seen_orders:
            _log_error(
                log_dir,
                path,
                "duplicate_order",
                f"Duplicate order {chapter.order} (chapter '{chapter.chapter_id}') in locale '{locale_dir.name}'",
                field="order",
            )
            continue
        seen_ids.add(chapter.chapter_id)
        seen_orders.add(chapter.order)
        chapters.append(chapter)

    chapters.sort(key=lambda c: c.order)
    return chapters
