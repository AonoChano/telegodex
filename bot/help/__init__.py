"""Telegodex help document system.

Public API:
    HelpChapter — parsed help chapter dataclass.
    load_help_file — load a single ``.md`` help file.
    load_help_locale — load all chapters for a locale directory.
    HelpRenderer — multi-language chapter cache and renderer.
    get_help_renderer — get the singleton renderer.
    init_help_renderer — create and initialize the singleton renderer.
    scan_help_documents — scan a locale directory for ``.md`` files.
"""

from __future__ import annotations

from pathlib import Path

from .loader import HelpChapter, load_help_file, load_help_locale
from .renderer import HelpRenderer
from .scanner import scan_help_documents

__all__ = [
    "HelpChapter",
    "HelpRenderer",
    "get_help_renderer",
    "init_help_renderer",
    "load_help_file",
    "load_help_locale",
    "scan_help_documents",
]

_renderer: HelpRenderer | None = None


def init_help_renderer(help_root: Path) -> HelpRenderer:
    """Create and initialize the singleton ``HelpRenderer``.

    Args:
        help_root: Root directory containing locale subdirectories.

    Returns:
        The initialized ``HelpRenderer`` instance.
    """
    global _renderer
    _renderer = HelpRenderer(help_root)
    _renderer.initialize()
    return _renderer


def get_help_renderer() -> HelpRenderer:
    """Return the singleton ``HelpRenderer`` instance.

    Raises:
        RuntimeError: If ``init_help_renderer()`` has not been called.
    """
    if _renderer is None:
        raise RuntimeError("HelpRenderer not initialized. Call init_help_renderer() first.")
    return _renderer
