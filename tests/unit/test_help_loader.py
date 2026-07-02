"""Unit tests for ``bot.help.loader`` — Markdown help file parsing and validation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from bot.help.loader import HelpChapter, load_help_file, load_help_locale


def _write_file(path: Path, content: str) -> Path:
    """Write *content* to *path* and return the path."""
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# load_help_file
# ---------------------------------------------------------------------------


def test_load_valid_file_returns_chapter(tmp_path: Path) -> None:
    path = _write_file(
        tmp_path / "overview.md",
        '---\ntitle: "Overview"\norder: 1\n---\n\n# Telegodex\n\nContent here.\n',
    )

    chapter = load_help_file(path)

    assert chapter is not None
    assert chapter.chapter_id == "overview"
    assert chapter.title == "Overview"
    assert chapter.order == 1
    assert len(chapter.pages) == 1
    assert "Telegodex" in chapter.pages[0]


def test_load_file_with_multiple_pages(tmp_path: Path) -> None:
    content = (
        '---\ntitle: "Overview"\norder: 1\n---\n\n'
        "# Telegodex\n\nContent here.\n\n"
        "---\n\n"
        "## Page 2\n\nMore content.\n\n"
        "---\n\n"
        "## Page 3\n\nEnd.\n"
    )
    path = _write_file(tmp_path / "overview.md", content)

    chapter = load_help_file(path)

    assert chapter is not None
    assert len(chapter.pages) == 3
    assert "Telegodex" in chapter.pages[0]
    assert "Page 2" in chapter.pages[1]
    assert "Page 3" in chapter.pages[2]


def test_load_file_missing_frontmatter_returns_none(tmp_path: Path) -> None:
    path = _write_file(tmp_path / "no_frontmatter.md", "# Just content\n\nNo frontmatter.\n")

    chapter = load_help_file(path)

    assert chapter is None


def test_load_file_missing_title_returns_none(tmp_path: Path) -> None:
    path = _write_file(
        tmp_path / "no_title.md",
        '---\norder: 1\n---\n\n# Content\n',
    )

    chapter = load_help_file(path)

    assert chapter is None


def test_load_file_missing_order_returns_none(tmp_path: Path) -> None:
    path = _write_file(
        tmp_path / "no_order.md",
        '---\ntitle: "Test"\n---\n\n# Content\n',
    )

    chapter = load_help_file(path)

    assert chapter is None


def test_load_file_empty_returns_none(tmp_path: Path) -> None:
    path = _write_file(tmp_path / "empty.md", "")

    chapter = load_help_file(path)

    assert chapter is None


def test_load_file_invalid_order_non_number_returns_none(tmp_path: Path) -> None:
    path = _write_file(
        tmp_path / "bad_order.md",
        '---\ntitle: "Test"\norder: abc\n---\n\n# Content\n',
    )

    chapter = load_help_file(path)

    assert chapter is None


def test_load_file_invalid_order_zero_returns_none(tmp_path: Path) -> None:
    path = _write_file(
        tmp_path / "zero_order.md",
        '---\ntitle: "Test"\norder: 0\n---\n\n# Content\n',
    )

    chapter = load_help_file(path)

    assert chapter is None


def test_load_file_invalid_order_negative_returns_none(tmp_path: Path) -> None:
    path = _write_file(
        tmp_path / "neg_order.md",
        '---\ntitle: "Test"\norder: -1\n---\n\n# Content\n',
    )

    chapter = load_help_file(path)

    assert chapter is None


def test_load_file_unquotes_title(tmp_path: Path) -> None:
    path = _write_file(
        tmp_path / "quoted.md",
        "---\ntitle: 'Single Quoted'\norder: 2\n---\n\n# Content\n",
    )

    chapter = load_help_file(path)

    assert chapter is not None
    assert chapter.title == "Single Quoted"


def test_load_file_creates_log_on_error(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    path = _write_file(tmp_path / "bad.md", "# No frontmatter\n")

    chapter = load_help_file(path, log_dir=log_dir)

    assert chapter is None
    log_files = list(log_dir.glob("*.jsonl"))
    assert len(log_files) == 1
    today = datetime.now().strftime("%Y-%m-%d")
    assert log_files[0].name == f"{today}.jsonl"


def test_load_file_no_log_dir_does_not_crash(tmp_path: Path) -> None:
    path = _write_file(tmp_path / "bad.md", "# No frontmatter\n")

    chapter = load_help_file(path, log_dir=None)

    assert chapter is None


# ---------------------------------------------------------------------------
# load_help_locale
# ---------------------------------------------------------------------------


def test_load_locale_multiple_valid_files_sorted(tmp_path: Path) -> None:
    _write_file(
        tmp_path / "settings.md",
        '---\ntitle: "Settings"\norder: 3\n---\n\n# Settings\n',
    )
    _write_file(
        tmp_path / "overview.md",
        '---\ntitle: "Overview"\norder: 1\n---\n\n# Overview\n',
    )
    _write_file(
        tmp_path / "providers.md",
        '---\ntitle: "Providers"\norder: 2\n---\n\n# Providers\n',
    )

    chapters = load_help_locale(tmp_path)

    assert len(chapters) == 3
    assert [c.order for c in chapters] == [1, 2, 3]
    assert [c.chapter_id for c in chapters] == ["overview", "providers", "settings"]


def test_load_locale_duplicate_order_skips_second(tmp_path: Path) -> None:
    _write_file(
        tmp_path / "first.md",
        '---\ntitle: "First"\norder: 1\n---\n\n# First\n',
    )
    _write_file(
        tmp_path / "second.md",
        '---\ntitle: "Second"\norder: 1\n---\n\n# Second\n',
    )

    chapters = load_help_locale(tmp_path)

    assert len(chapters) == 1
    assert chapters[0].chapter_id == "first"


def test_load_locale_duplicate_order_logs_to_log_dir(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    _write_file(
        tmp_path / "first.md",
        '---\ntitle: "First"\norder: 1\n---\n\n# First\n',
    )
    _write_file(
        tmp_path / "second.md",
        '---\ntitle: "Second"\norder: 1\n---\n\n# Second\n',
    )

    load_help_locale(tmp_path, log_dir=log_dir)

    log_files = list(log_dir.glob("*.jsonl"))
    assert len(log_files) == 1
    log_content = log_files[0].read_text(encoding="utf-8")
    assert "duplicate_order" in log_content


def test_load_locale_mixed_valid_invalid(tmp_path: Path) -> None:
    _write_file(
        tmp_path / "valid.md",
        '---\ntitle: "Valid"\norder: 1\n---\n\n# Valid\n',
    )
    _write_file(
        tmp_path / "no_frontmatter.md",
        "# No frontmatter\n",
    )
    _write_file(
        tmp_path / "bad_order.md",
        '---\ntitle: "Bad"\norder: notanumber\n---\n\n# Bad\n',
    )

    chapters = load_help_locale(tmp_path)

    assert len(chapters) == 1
    assert chapters[0].chapter_id == "valid"


def test_load_locale_empty_directory_returns_empty(tmp_path: Path) -> None:
    chapters = load_help_locale(tmp_path)

    assert chapters == []


def test_load_locale_nonexistent_directory_returns_empty(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"

    chapters = load_help_locale(missing)

    assert chapters == []


def test_load_locale_skips_readme_and_underscore(tmp_path: Path) -> None:
    _write_file(
        tmp_path / "overview.md",
        '---\ntitle: "Overview"\norder: 1\n---\n\n# Overview\n',
    )
    _write_file(
        tmp_path / "README.md",
        '---\ntitle: "README"\norder: 0\n---\n\n# README\n',
    )
    _write_file(
        tmp_path / "_template.md",
        '---\ntitle: "Template"\norder: 2\n---\n\n# Template\n',
    )

    chapters = load_help_locale(tmp_path)

    assert len(chapters) == 1
    assert chapters[0].chapter_id == "overview"


def test_load_locale_returns_helpchapter_instances(tmp_path: Path) -> None:
    _write_file(
        tmp_path / "overview.md",
        '---\ntitle: "Overview"\norder: 1\n---\n\n# Overview\n',
    )

    chapters = load_help_locale(tmp_path)

    assert len(chapters) == 1
    assert isinstance(chapters[0], HelpChapter)
