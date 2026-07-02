"""Unit tests for ``bot.help.scanner`` — help document directory scanning."""

from __future__ import annotations

from pathlib import Path

from bot.help.scanner import scan_help_documents


def test_scan_returns_only_md_files(tmp_path: Path) -> None:
    (tmp_path / "overview.md").write_text("# Overview", encoding="utf-8")
    (tmp_path / "settings.md").write_text("# Settings", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("not markdown", encoding="utf-8")
    (tmp_path / "config.yaml").write_text("key: value", encoding="utf-8")

    results = scan_help_documents(tmp_path)
    names = sorted(p.name for p in results)

    assert names == ["overview.md", "settings.md"]


def test_scan_skips_readme(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# README", encoding="utf-8")
    (tmp_path / "overview.md").write_text("# Overview", encoding="utf-8")

    results = scan_help_documents(tmp_path)

    assert [p.name for p in results] == ["overview.md"]


def test_scan_skips_underscore_prefix(tmp_path: Path) -> None:
    (tmp_path / "_template.md").write_text("# Template", encoding="utf-8")
    (tmp_path / "_base.md").write_text("# Base", encoding="utf-8")
    (tmp_path / "overview.md").write_text("# Overview", encoding="utf-8")

    results = scan_help_documents(tmp_path)

    assert [p.name for p in results] == ["overview.md"]


def test_scan_skips_dot_prefix(tmp_path: Path) -> None:
    (tmp_path / ".hidden.md").write_text("# Hidden", encoding="utf-8")
    (tmp_path / ".gitkeep").write_text("", encoding="utf-8")
    (tmp_path / "overview.md").write_text("# Overview", encoding="utf-8")

    results = scan_help_documents(tmp_path)

    assert [p.name for p in results] == ["overview.md"]


def test_scan_empty_directory_returns_empty(tmp_path: Path) -> None:
    results = scan_help_documents(tmp_path)

    assert results == []


def test_scan_nonexistent_directory_returns_empty(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"

    results = scan_help_documents(missing)

    assert results == []


def test_scan_path_is_file_returns_empty(tmp_path: Path) -> None:
    file_path = tmp_path / "afile.md"
    file_path.write_text("# A", encoding="utf-8")

    results = scan_help_documents(file_path)

    assert results == []


def test_scan_skips_subdirectories(tmp_path: Path) -> None:
    (tmp_path / "overview.md").write_text("# Overview", encoding="utf-8")
    (tmp_path / "subdir.md").mkdir()
    (tmp_path / "subfolder").mkdir()

    results = scan_help_documents(tmp_path)

    assert [p.name for p in results] == ["overview.md"]


def test_scan_returns_sorted_results(tmp_path: Path) -> None:
    (tmp_path / "zebra.md").write_text("# Zebra", encoding="utf-8")
    (tmp_path / "apple.md").write_text("# Apple", encoding="utf-8")
    (tmp_path / "mango.md").write_text("# Mango", encoding="utf-8")

    results = scan_help_documents(tmp_path)

    assert [p.name for p in results] == ["apple.md", "mango.md", "zebra.md"]


def test_scan_returns_path_objects(tmp_path: Path) -> None:
    (tmp_path / "overview.md").write_text("# Overview", encoding="utf-8")

    results = scan_help_documents(tmp_path)

    assert len(results) == 1
    assert isinstance(results[0], Path)
