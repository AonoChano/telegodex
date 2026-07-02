"""Telegodex i18n (internationalization) package.

Public API:
    tr(key, locale, **placeholders) — translate a key.
    get_i18n_manager() — get the singleton manager.
    list_available_locales() — list all loaded ``LocaleInfo``.
    resolve_locale(ui_language, telegram_language_code) — resolve effective locale.
    LocaleInfo — locale metadata dataclass.
    I18nManager — the manager class (for advanced use).
"""

from __future__ import annotations

from .locale import LocaleInfo
from .manager import I18nManager, get_i18n_manager


def tr(key: str, locale: str | None = None, **placeholders) -> str:
    """Translate *key* for *locale* with optional placeholders.

    Convenience function: gets the translator from the singleton manager
    and delegates to ``Translator.tr()``.

    Args:
        key: Dot-path translation key (e.g., "bot.menu.settings").
        locale: Locale code (e.g., "zh-cn", "en"), or ``None`` for fallback.
        **placeholders: Named placeholders to substitute in the translated string.

    Returns:
        The translated and formatted string, or *key* itself if no
        translation was found.
    """
    return get_i18n_manager().get_translator(locale).tr(key, **placeholders)


def list_available_locales() -> list[LocaleInfo]:
    """Return all loaded locales sorted by display name."""
    return get_i18n_manager().list_available_locales()


def resolve_locale(ui_language: str | None, telegram_language_code: str | None) -> str:
    """Resolve the effective locale for a user."""
    return get_i18n_manager().resolve_locale(ui_language, telegram_language_code)


__all__ = [
    "tr",
    "get_i18n_manager",
    "list_available_locales",
    "resolve_locale",
    "LocaleInfo",
    "I18nManager",
]
