"""Translation lookup with fallback and placeholder support."""

from __future__ import annotations


class _SafeFormatDict(dict):
    """Dict that returns ``{key}`` for missing keys instead of raising ``KeyError``."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


class Translator:
    """Looks up translation keys with fallback support.

    Attributes:
        translations: dot-path key -> string mapping.
        fallback: Another ``Translator`` to consult if key is missing (usually English).
    """

    def __init__(
        self,
        translations: dict[str, str] | None = None,
        fallback: Translator | None = None,
    ) -> None:
        self._translations = translations or {}
        self._fallback = fallback

    def tr(self, key: str, **placeholders) -> str:
        """Translate *key* with optional placeholders.

        Lookup order: self -> fallback chain -> return *key* itself.
        Found strings are formatted with ``str.format_map`` using
        ``_SafeFormatDict`` (missing placeholders keep their ``{name}`` form).

        Args:
            key: Dot-path translation key (e.g., "bot.menu.settings").
            **placeholders: Named placeholders to substitute in the translated
                string (e.g., ``name="world"`` for ``"Hello, {name}"``).

        Returns:
            The translated and formatted string, or *key* itself if no
            translation was found.
        """
        text = self._lookup(key)
        if text is None:
            return key
        if not placeholders:
            return text
        try:
            return text.format_map(_SafeFormatDict(placeholders))
        except (IndexError, ValueError):
            # Malformed format string (e.g., stray braces) — return raw text.
            return text

    def _lookup(self, key: str) -> str | None:
        """Look up *key* in self, then the fallback chain.

        Args:
            key: Dot-path translation key.

        Returns:
            The raw translation string, or ``None`` if not found anywhere
            in the chain.
        """
        if key in self._translations:
            return self._translations[key]
        if self._fallback is not None:
            return self._fallback._lookup(key)
        return None
