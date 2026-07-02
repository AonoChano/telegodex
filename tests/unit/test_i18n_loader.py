"""Unit tests for ``i18n.loader`` — locale JSON file loading and validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from i18n.loader import load_locale_file


def _write_json(path: Path, data: Any) -> Path:
    """Write *data* as JSON to *path* and return the path."""
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f)
    return path


def test_load_valid_file(tmp_path: Path) -> None:
    path = _write_json(
        tmp_path / "en.json",
        {
            "_meta": {"locale": "en", "display_name": "English"},
            "bot": {"menu": {"settings": "Settings"}},
        },
    )

    info = load_locale_file(path)

    assert info is not None
    assert info.locale == "en"
    assert info.display_name == "English"
    assert info.translations == {"bot.menu.settings": "Settings"}


def test_load_invalid_json_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{not valid json", encoding="utf-8")

    info = load_locale_file(path)

    assert info is None


def test_load_missing_meta_returns_none(tmp_path: Path) -> None:
    path = _write_json(tmp_path / "no_meta.json", {"bot": {"menu": "Settings"}})

    info = load_locale_file(path)

    assert info is None


def test_load_missing_display_name_returns_none(tmp_path: Path) -> None:
    path = _write_json(tmp_path / "no_display.json", {"_meta": {"locale": "en"}})

    info = load_locale_file(path)

    assert info is None


def test_load_missing_locale_returns_none(tmp_path: Path) -> None:
    path = _write_json(tmp_path / "no_locale.json", {"_meta": {"display_name": "English"}})

    info = load_locale_file(path)

    assert info is None


def test_load_meta_with_non_string_fields_returns_none(tmp_path: Path) -> None:
    path = _write_json(
        tmp_path / "numeric_locale.json",
        {"_meta": {"locale": 123, "display_name": "English"}},
    )

    info = load_locale_file(path)

    assert info is None


def test_load_empty_meta_values_returns_none(tmp_path: Path) -> None:
    path = _write_json(
        tmp_path / "empty_locale.json",
        {"_meta": {"locale": "", "display_name": "English"}},
    )

    info = load_locale_file(path)

    assert info is None


def test_load_flattens_nested_keys(tmp_path: Path) -> None:
    path = _write_json(
        tmp_path / "nested.json",
        {
            "_meta": {"locale": "en", "display_name": "English"},
            "a": {"b": {"c": "deep"}},
            "x": {"y": "shallow"},
            "top": "leaf",
        },
    )

    info = load_locale_file(path)

    assert info is not None
    assert info.translations == {
        "a.b.c": "deep",
        "x.y": "shallow",
        "top": "leaf",
    }
