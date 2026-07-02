"""Unit tests for ``i18n.manager`` — I18nManager locale loading and resolution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from i18n.manager import DEFAULT_LOCALE, I18nManager


def _write_locale(directory: Path, name: str, data: Any) -> Path:
    """Write a locale JSON file to *directory* and return its path."""
    path = directory / name
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f)
    return path


def _write_en(directory: Path) -> Path:
    return _write_locale(
        directory,
        "en.json",
        {
            "_meta": {"locale": "en", "display_name": "English"},
            "bot": {"only_en": "English-only key"},
        },
    )


def _write_zh_cn(directory: Path) -> Path:
    return _write_locale(
        directory,
        "zh-cn.json",
        {
            "_meta": {"locale": "zh-cn", "display_name": "简体中文(中国)"},
            "bot": {"menu": "菜单"},
        },
    )


def test_initialize_loads_valid_locales(tmp_path: Path) -> None:
    _write_en(tmp_path)
    _write_zh_cn(tmp_path)

    manager = I18nManager()
    manager.initialize(tmp_path)

    locales = manager.list_available_locales()
    assert len(locales) == 2
    # Sorted by display_name: "English" (ASCII) sorts before "简体中文(中国)" (CJK).
    assert [loc.display_name for loc in locales] == ["English", "简体中文(中国)"]


def test_initialize_skips_invalid_files(tmp_path: Path) -> None:
    _write_en(tmp_path)
    (tmp_path / "broken.json").write_text("{not valid json", encoding="utf-8")
    _write_locale(tmp_path, "no_meta.json", {"bot": {"menu": "Settings"}})

    manager = I18nManager()
    manager.initialize(tmp_path)

    locales = manager.list_available_locales()
    assert len(locales) == 1
    assert locales[0].locale == "en"


def test_initialize_empty_directory(tmp_path: Path) -> None:
    manager = I18nManager()
    manager.initialize(tmp_path)

    assert manager.list_available_locales() == []
    assert manager.get_translator("en").tr("any.key") == "any.key"


def test_initialize_nonexistent_directory(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"

    manager = I18nManager()
    manager.initialize(missing)

    assert manager.list_available_locales() == []


def test_get_translator_returns_fallback_for_unknown_locale(tmp_path: Path) -> None:
    _write_en(tmp_path)

    manager = I18nManager()
    manager.initialize(tmp_path)

    translator = manager.get_translator("fr")
    assert translator.tr("any.key") == "any.key"


def test_get_translator_returns_fallback_for_none(tmp_path: Path) -> None:
    _write_en(tmp_path)

    manager = I18nManager()
    manager.initialize(tmp_path)

    translator = manager.get_translator(None)
    assert translator.tr("any.key") == "any.key"


def test_resolve_locale_uses_ui_language(tmp_path: Path) -> None:
    _write_en(tmp_path)
    _write_zh_cn(tmp_path)

    manager = I18nManager()
    manager.initialize(tmp_path)

    assert manager.resolve_locale("zh-cn", None) == "zh-cn"


def test_resolve_locale_falls_back_to_telegram_language_code(tmp_path: Path) -> None:
    _write_en(tmp_path)
    _write_zh_cn(tmp_path)

    manager = I18nManager()
    manager.initialize(tmp_path)

    assert manager.resolve_locale(None, "zh") == "zh-cn"


def test_resolve_locale_falls_back_to_default(tmp_path: Path) -> None:
    _write_en(tmp_path)
    _write_zh_cn(tmp_path)

    manager = I18nManager()
    manager.initialize(tmp_path)

    assert manager.resolve_locale(None, "fr") == "en"


def test_resolve_locale_falls_back_to_default_when_no_locales(tmp_path: Path) -> None:
    manager = I18nManager()
    manager.initialize(tmp_path)

    assert manager.resolve_locale("zh-cn", "zh") == DEFAULT_LOCALE


def test_initialize_is_idempotent(tmp_path: Path) -> None:
    _write_en(tmp_path)
    _write_zh_cn(tmp_path)

    manager = I18nManager()
    manager.initialize(tmp_path)
    manager.initialize(tmp_path)  # second call should be a no-op

    assert len(manager.list_available_locales()) == 2


def test_english_translator_used_as_fallback(tmp_path: Path) -> None:
    _write_en(tmp_path)
    _write_zh_cn(tmp_path)

    manager = I18nManager()
    manager.initialize(tmp_path)

    zh_translator = manager.get_translator("zh-cn")
    # Key missing from both zh-cn and en -> returns the key itself.
    assert zh_translator.tr("missing.key") == "missing.key"
    # Key only in en.json -> found via the zh-cn translator's fallback chain.
    assert zh_translator.tr("bot.only_en") == "English-only key"
