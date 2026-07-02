"""Load and validate a single locale JSON file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loguru import logger

from .locale import LocaleInfo, normalize_locale_code


def load_locale_file(path: Path) -> LocaleInfo | None:
    """Load a locale JSON file and validate its structure.

    Returns ``LocaleInfo`` if valid, ``None`` if invalid (with
    ``logger.warning``).

    Robustness:
        - ``json.JSONDecodeError`` -> warning with filename + error position,
          return ``None``.
        - Missing ``_meta``, or ``locale``/``display_name`` not non-empty
          strings -> warning, return ``None``.
        - Extract all keys except ``_meta``, flatten to dot-path keys.

    JSON structure::

        {
            "_meta": {"locale": "zh-cn", "display_name": "简体中文(中国)"},
            "bot": {"menu": {"settings": "⚙️ 设置"}}
        }

    Flattened: ``{"bot.menu.settings": "⚙️ 设置"}``

    Args:
        path: Path to the locale JSON file.

    Returns:
        ``LocaleInfo`` if the file is valid, otherwise ``None``.
    """
    try:
        with path.open("r", encoding="utf-8") as f:
            data: Any = json.load(f)
    except json.JSONDecodeError as e:
        logger.warning(
            f"Failed to parse locale JSON '{path.name}': {e.msg} at line {e.lineno} col {e.colno}"
        )
        return None
    except OSError as e:
        logger.warning(f"Failed to read locale file '{path.name}': {e}")
        return None

    if not isinstance(data, dict):
        logger.warning(f"Locale file '{path.name}': root is not a JSON object")
        return None

    meta = data.get("_meta")
    if not isinstance(meta, dict):
        logger.warning(f"Locale file '{path.name}': missing or invalid '_meta' section")
        return None

    raw_locale = meta.get("locale")
    raw_display_name = meta.get("display_name")

    if not isinstance(raw_locale, str) or not raw_locale.strip():
        logger.warning(f"Locale file '{path.name}': '_meta.locale' must be a non-empty string")
        return None
    if not isinstance(raw_display_name, str) or not raw_display_name.strip():
        logger.warning(
            f"Locale file '{path.name}': '_meta.display_name' must be a non-empty string"
        )
        return None

    locale = normalize_locale_code(raw_locale)
    display_name = raw_display_name.strip()

    translations: dict[str, str] = {}
    _flatten(data, prefix="", out=translations)

    return LocaleInfo(locale=locale, display_name=display_name, translations=translations)


def _flatten(obj: dict[str, Any], prefix: str, out: dict[str, str]) -> None:
    """Recursively flatten a nested dict into dot-path keys.

    Only string leaf values become translation entries. Non-string, non-dict
    values (lists, numbers, booleans, null) are silently ignored. The
    ``_meta`` key at the top level (``prefix == ""``) is skipped.

    Args:
        obj: The dict to flatten.
        prefix: Current dot-path prefix (empty string at top level).
        out: Output dict accumulating dot-path -> string mappings.
    """
    for key, value in obj.items():
        # Skip the top-level _meta key only.
        if prefix == "" and key == "_meta":
            continue
        new_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, str):
            out[new_key] = value
        elif isinstance(value, dict):
            _flatten(value, new_key, out)
        # Non-string, non-dict values are silently ignored.
