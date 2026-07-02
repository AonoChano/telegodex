"""Locale data structures and code normalization."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LocaleInfo:
    """Metadata and translation table for a single locale.

    Attributes:
        locale: Normalized locale code (e.g., "zh-cn", "en").
        display_name: Human-readable name shown in the language menu (e.g., "简体中文(中国)").
        translations: Flattened dot-path -> string mapping (e.g., {"bot.menu.settings": "⚙️ 设置"}).
    """

    locale: str
    display_name: str
    translations: dict[str, str] = field(default_factory=dict)


def normalize_locale_code(value: str) -> str:
    """Normalize a locale code: lowercase, underscores to hyphens, stripped.

    Args:
        value: Raw locale code (e.g., "zh_CN", " EN ").

    Returns:
        Normalized locale code (e.g., "zh-cn", "en"). Returns empty string
        for non-string input.

    Examples:
        >>> normalize_locale_code("zh_CN")
        "zh-cn"
        >>> normalize_locale_code(" EN ")
        "en"
    """
    if not isinstance(value, str):
        return ""
    return value.strip().lower().replace("_", "-")


def match_locale(language_code: str | None, available: list[str]) -> str | None:
    """Match a Telegram language_code to an available locale.

    Tries exact match first, then prefix match (on the primary subtag).
    Returns ``None`` if no match.

    Args:
        language_code: Raw language code (e.g., "zh", "en", "zh-Hans-CN").
        available: List of available locale codes (e.g., ["en", "zh-cn"]).

    Returns:
        The matched locale code from *available* (original form), or ``None``.

    Examples:
        >>> match_locale("zh", ["en", "zh-cn"])
        "zh-cn"
        >>> match_locale("en", ["en", "zh-cn"])
        "en"
        >>> match_locale("fr", ["en", "zh-cn"])
        None
    """
    if not language_code:
        return None
    normalized = normalize_locale_code(language_code)
    if not normalized:
        return None

    # Build a normalized -> original mapping for lookup.
    normalized_available: dict[str, str] = {}
    for code in available:
        normalized_available[normalize_locale_code(code)] = code

    # Exact match first.
    if normalized in normalized_available:
        return normalized_available[normalized]

    # Prefix match on the primary subtag (e.g., "zh" matches "zh-cn").
    primary = normalized.split("-")[0]
    for norm_code, original in normalized_available.items():
        if norm_code.split("-")[0] == primary:
            return original

    return None
