"""Unit tests for ``i18n.translator`` — translation lookup with fallback."""

from __future__ import annotations

from i18n.translator import Translator


def test_tr_returns_translation_when_key_found() -> None:
    translator = Translator(translations={"bot.menu.settings": "Settings"})

    assert translator.tr("bot.menu.settings") == "Settings"


def test_tr_returns_key_when_not_found_and_no_fallback() -> None:
    translator = Translator(translations={})

    assert translator.tr("missing.key") == "missing.key"


def test_tr_falls_back_to_fallback_translator() -> None:
    fallback = Translator(translations={"bot.menu.settings": "Settings"})
    translator = Translator(translations={}, fallback=fallback)

    assert translator.tr("bot.menu.settings") == "Settings"


def test_tr_returns_key_when_not_found_in_either() -> None:
    fallback = Translator(translations={})
    translator = Translator(translations={}, fallback=fallback)

    assert translator.tr("missing.key") == "missing.key"


def test_tr_fills_placeholders() -> None:
    translator = Translator(translations={"bot.welcome": "Hello, {name}!"})

    assert translator.tr("bot.welcome", name="World") == "Hello, World!"


def test_tr_missing_placeholder_keeps_original() -> None:
    translator = Translator(translations={"bot.welcome": "Hello, {name}!"})

    assert translator.tr("bot.welcome") == "Hello, {name}!"


def test_tr_multiple_placeholders() -> None:
    translator = Translator(translations={"bot.switched": "Switched to {provider} ({model})"})

    assert translator.tr("bot.switched", provider="openai", model="gpt-4") == "Switched to openai (gpt-4)"


def test_tr_partial_placeholders() -> None:
    translator = Translator(translations={"bot.msg": "{a} and {b}"})

    assert translator.tr("bot.msg", a="X") == "X and {b}"
