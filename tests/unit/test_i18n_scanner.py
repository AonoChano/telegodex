"""Unit tests for ``i18n.scanner`` — locale directory scanning."""

from __future__ import annotations

from pathlib import Path

from i18n.scanner import scan_locales_directory


def _write_json(directory: Path, name: str) -> Path:
    """Create an empty JSON file named *name* inside *directory*."""
    path = directory / name
    path.write_text("{}", encoding="utf-8")
    return path


def test_scan_returns_json_files(tmp_path: Path) -> None:
    _write_json(tmp_path, "en.json")
    _write_json(tmp_path, "zh-cn.json")
    _write_json(tmp_path, "fr.json")

    results = scan_locales_directory(tmp_path)
    names = sorted(p.name for p in results)

    assert names == ["en.json", "fr.json", "zh-cn.json"]


def test_scan_skips_non_json_files(tmp_path: Path) -> None:
    (tmp_path / "readme.md").write_text("readme", encoding="utf-8")
    (tmp_path / "config.yaml").write_text("key: value", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("notes", encoding="utf-8")

    results = scan_locales_directory(tmp_path)

    assert results == []


def test_scan_skips_underscore_prefix(tmp_path: Path) -> None:
    _write_json(tmp_path, "_template.json")
    _write_json(tmp_path, "_base.json")

    results = scan_locales_directory(tmp_path)

    assert results == []


def test_scan_skips_dot_prefix(tmp_path: Path) -> None:
    (tmp_path / ".gitkeep").write_text("", encoding="utf-8")
    _write_json(tmp_path, ".hidden.json")

    results = scan_locales_directory(tmp_path)

    assert results == []


def test_scan_missing_directory_returns_empty(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"

    results = scan_locales_directory(missing)

    assert results == []


def test_scan_returns_sorted_results(tmp_path: Path) -> None:
    _write_json(tmp_path, "zebra.json")
    _write_json(tmp_path, "apple.json")
    _write_json(tmp_path, "mango.json")

    results = scan_locales_directory(tmp_path)

    assert [p.name for p in results] == ["apple.json", "mango.json", "zebra.json"]
