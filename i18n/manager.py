"""I18nManager singleton: coordinates scanning, loading, and translation lookup."""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from .loader import load_locale_file
from .locale import LocaleInfo, match_locale, normalize_locale_code
from .scanner import scan_locales_directory
from .translator import Translator

DEFAULT_LOCALE = "en"


class I18nManager:
    """Singleton manager for all locale translations.

    The manager scans a locales directory, loads each valid JSON file into a
    ``LocaleInfo``, builds a ``Translator`` per locale (with English as the
    fallback when available), and exposes lookup helpers.

    Even if no locales load, the system still works: ``tr`` returns the key
    itself, and ``resolve_locale`` returns ``DEFAULT_LOCALE``.
    """

    def __init__(self) -> None:
        self._locales: dict[str, LocaleInfo] = {}  # locale -> LocaleInfo
        self._translators: dict[str, Translator] = {}  # locale -> Translator
        self._fallback_translator = Translator()  # empty, returns keys as-is
        self._initialized = False

    def initialize(self, locales_dir: Path) -> None:
        """Scan and load all locale files from *locales_dir*.

        Safe to call: errors in scanning/loading are caught and logged. Even
        if no locales load, the system still works (``tr`` returns the key
        itself). Calling ``initialize`` again after the first successful call
        is a no-op.

        Args:
            locales_dir: Path to the directory containing locale JSON files.
        """
        if self._initialized:
            logger.debug("I18nManager already initialized; skipping")
            return

        self._locales.clear()
        self._translators.clear()

        try:
            candidates = scan_locales_directory(locales_dir)
        except Exception as e:  # noqa: BLE001 — broad on purpose for robustness
            logger.warning(f"Failed to scan locales directory '{locales_dir}': {e}")
            candidates = []

        if not candidates:
            logger.info(f"No locale files found in '{locales_dir}'; i18n will return keys as-is")
            self._initialized = True
            return

        # First pass: load all valid locales.
        loaded: list[LocaleInfo] = []
        for path in candidates:
            try:
                info = load_locale_file(path)
            except Exception as e:  # noqa: BLE001 — one bad file must not crash init
                logger.warning(f"Unexpected error loading locale file '{path.name}': {e}")
                info = None
            if info is not None:
                loaded.append(info)

        # Build locale -> LocaleInfo map (first occurrence wins on duplicates).
        for info in loaded:
            if info.locale in self._locales:
                logger.warning(
                    f"Duplicate locale '{info.locale}' (from '{info.display_name}'); "
                    f"keeping the first one"
                )
                continue
            self._locales[info.locale] = info

        # Build translators. Non-English locales fall back to English; English
        # (and any locale without English available) falls back to the empty
        # translator, which returns keys as-is.
        english_info = self._locales.get(DEFAULT_LOCALE)
        english_translator: Translator | None = None
        if english_info is not None:
            english_translator = Translator(translations=english_info.translations)

        for locale, info in self._locales.items():
            if locale == DEFAULT_LOCALE or english_translator is None:
                fallback = self._fallback_translator
            else:
                fallback = english_translator
            self._translators[locale] = Translator(
                translations=info.translations,
                fallback=fallback,
            )

        self._initialized = True
        if not self._locales:
            logger.error(
                f"No valid locale files loaded from '{locales_dir}'; "
                f"i18n will return keys as-is"
            )
        else:
            logger.info(
                f"I18nManager initialized: {len(self._locales)} locale(s) loaded: "
                f"{sorted(self._locales.keys())}"
            )

    def get_translator(self, locale: str | None) -> Translator:
        """Return the ``Translator`` for *locale*, or the fallback translator.

        If *locale* is ``None`` or not loaded, the empty fallback translator
        is returned (its ``tr`` returns the key itself).

        Args:
            locale: Locale code (e.g., "zh-cn", "en"), or ``None``.

        Returns:
            The ``Translator`` for the locale, or the fallback translator.
        """
        if locale is None:
            return self._fallback_translator
        normalized = normalize_locale_code(locale)
        translator = self._translators.get(normalized)
        if translator is None:
            return self._fallback_translator
        return translator

    def list_available_locales(self) -> list[LocaleInfo]:
        """Return all loaded locales sorted by ``display_name``.

        Returns:
            List of ``LocaleInfo`` objects, sorted alphabetically by display name.
        """
        return sorted(self._locales.values(), key=lambda x: x.display_name)

    def resolve_locale(self, ui_language: str | None, telegram_language_code: str | None) -> str:
        """Resolve the effective locale for a user.

        Priority:
            1. ``ui_language`` (explicitly chosen by the user) — exact or
               prefix match against loaded locales.
            2. ``telegram_language_code`` — matched via ``match_locale``.
            3. ``DEFAULT_LOCALE`` (``"en"``).

        Args:
            ui_language: Locale code explicitly set in the user's UI preferences.
            telegram_language_code: Language code from Telegram (``User.language_code``).

        Returns:
            The resolved locale code (e.g., "zh-cn", "en").
        """
        available = list(self._locales.keys())

        # Priority 1: ui_language.
        if ui_language:
            normalized = normalize_locale_code(ui_language)
            if normalized in self._locales:
                return normalized
            matched = match_locale(ui_language, available)
            if matched is not None:
                return matched

        # Priority 2: telegram_language_code.
        if telegram_language_code:
            matched = match_locale(telegram_language_code, available)
            if matched is not None:
                return matched

        # Priority 3: default.
        return DEFAULT_LOCALE


# Module-level singleton.
_manager: I18nManager | None = None


def get_i18n_manager() -> I18nManager:
    """Return the singleton ``I18nManager`` instance.

    Creates the instance on first call. The returned manager is not yet
    initialized; call ``initialize()`` with a locales directory before use.
    """
    global _manager
    if _manager is None:
        _manager = I18nManager()
    return _manager
