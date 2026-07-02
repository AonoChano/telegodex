"""Scan the locales directory for candidate JSON files."""

from __future__ import annotations

from pathlib import Path

from loguru import logger


def scan_locales_directory(directory: Path) -> list[Path]:
    """Return sorted list of candidate locale JSON files in *directory*.

    Filters:
        - Only ``.json`` extension.
        - Skip filenames starting with ``_`` or ``.`` (e.g., ``_template.json``,
          ``.hidden.json``).

    If *directory* does not exist or is not a directory, log a warning and
    return an empty list (no crash).

    Args:
        directory: Path to the locales directory.

    Returns:
        Sorted list of candidate ``Path`` objects (files only).
    """
    if not directory.exists():
        logger.warning(f"Locales directory does not exist: {directory}")
        return []
    if not directory.is_dir():
        logger.warning(f"Locales path is not a directory: {directory}")
        return []

    candidates: list[Path] = []
    for entry in sorted(directory.iterdir()):
        if not entry.is_file():
            continue
        name = entry.name
        if not name.endswith(".json"):
            continue
        if name.startswith("_") or name.startswith("."):
            continue
        candidates.append(entry)

    return candidates
