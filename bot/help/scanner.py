"""Scan a locale directory for Markdown help document files."""

from __future__ import annotations

from pathlib import Path

from loguru import logger


def scan_help_documents(locale_dir: Path) -> list[Path]:
    """Return sorted list of candidate ``.md`` help files in *locale_dir*.

    Filters:
        - Only ``.md`` extension.
        - Skip filenames starting with ``_`` or ``.``.
        - Skip ``README.md`` (syntax doc, not a chapter).

    If *locale_dir* does not exist or is not a directory, log a warning and
    return an empty list (no crash).

    Args:
        locale_dir: Path to a locale's help directory (e.g., ``i18n/help/en``).

    Returns:
        Sorted list of candidate ``Path`` objects (files only).
    """
    if not locale_dir.exists():
        logger.warning(f"Help locale directory does not exist: {locale_dir}")
        return []
    if not locale_dir.is_dir():
        logger.warning(f"Help locale path is not a directory: {locale_dir}")
        return []

    candidates: list[Path] = []
    for entry in sorted(locale_dir.iterdir()):
        if not entry.is_file():
            continue
        name = entry.name
        if not name.endswith(".md"):
            continue
        if name.startswith("_") or name.startswith("."):
            continue
        if name == "README.md":
            continue
        candidates.append(entry)

    return candidates
