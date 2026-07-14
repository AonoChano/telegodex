"""Unit tests for ``bot.help.renderer`` — chapter cache, keyboards, and page rendering."""

from __future__ import annotations

from pathlib import Path

import pytest
from aiogram.types import InlineKeyboardMarkup

from bot.help.renderer import BASE_LOCALE, TOC_PAGE_SIZE, HelpRenderer
from bot.utils.callback_data import decode_callback_data


def _write_chapter(
    directory: Path,
    name: str,
    title: str,
    order: int,
    pages: list[str],
) -> Path:
    """Write a help chapter Markdown file into *directory*."""
    directory.mkdir(parents=True, exist_ok=True)
    body = "\n---\n\n".join(pages)
    content = f'---\ntitle: "{title}"\norder: {order}\n---\n\n{body}\n'
    path = directory / f"{name}.md"
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def help_root(tmp_path: Path) -> Path:
    """Create a temp help root with ``en/`` and ``zh-cn/`` locales.

    Creates 8 chapters per locale (orders 1-8). Chapter 3 has 3 pages so
    chapter pagination can be tested.
    """
    for locale_dir, prefix in [(tmp_path / "en", "EN"), (tmp_path / "zh-cn", "ZH")]:
        for i in range(1, 9):
            pages = [f"# {prefix} Chapter {i}\n\nContent of chapter {i}."]
            if i == 3:
                pages.extend(
                    [
                        f"# {prefix} Chapter {i} — Page 2\n\nMore content.",
                        f"# {prefix} Chapter {i} — Page 3\n\nFinal page.",
                    ]
                )
            _write_chapter(locale_dir, f"chapter_{i:02d}", f"{prefix} Chapter {i}", i, pages)
    return tmp_path


@pytest.fixture
def renderer(help_root: Path) -> HelpRenderer:
    """Return an initialized ``HelpRenderer`` pointing at the temp help root."""
    r = HelpRenderer(help_root)
    r.initialize()
    return r


# ---------------------------------------------------------------------------
# initialize
# ---------------------------------------------------------------------------


def test_initialize_caches_both_locales(renderer: HelpRenderer) -> None:
    assert "en" in renderer._cache
    assert "zh-cn" in renderer._cache
    assert len(renderer._cache["en"]) == 8
    assert len(renderer._cache["zh-cn"]) == 8


def test_initialize_skips_log_directory(tmp_path: Path) -> None:
    en_dir = tmp_path / "en"
    _write_chapter(en_dir, "chapter_01", "Chapter 1", 1, ["# Chapter 1"])
    (tmp_path / "log").mkdir()

    r = HelpRenderer(tmp_path)
    r.initialize()

    assert "log" not in r._cache
    assert "en" in r._cache


def test_initialize_nonexistent_root_does_not_crash(tmp_path: Path) -> None:
    r = HelpRenderer(tmp_path / "does-not-exist")
    r.initialize()

    assert r._cache == {}


# ---------------------------------------------------------------------------
# get_chapters
# ---------------------------------------------------------------------------


def test_get_chapters_returns_sorted_by_order(renderer: HelpRenderer) -> None:
    chapters = renderer.get_chapters("en")

    assert len(chapters) == 8
    assert [c.order for c in chapters] == list(range(1, 9))


def test_get_chapters_unknown_locale_falls_back_to_base(renderer: HelpRenderer) -> None:
    chapters = renderer.get_chapters("fr")

    assert len(chapters) == 8
    assert chapters == renderer.get_chapters(BASE_LOCALE)


def test_get_chapters_no_fallback_available(tmp_path: Path) -> None:
    """When neither the locale nor base locale exists, return empty list."""
    fr_dir = tmp_path / "fr"
    _write_chapter(fr_dir, "chapter_01", "Chapitre 1", 1, ["# Chapitre 1"])

    r = HelpRenderer(tmp_path)
    r.initialize()

    assert r.get_chapters("de") == []


# ---------------------------------------------------------------------------
# get_chapter
# ---------------------------------------------------------------------------


def test_get_chapter_returns_correct_chapter(renderer: HelpRenderer) -> None:
    chapter = renderer.get_chapter("en", "chapter_03")

    assert chapter is not None
    assert chapter.chapter_id == "chapter_03"
    assert chapter.order == 3
    assert len(chapter.pages) == 3


def test_get_chapter_unknown_id_returns_none(renderer: HelpRenderer) -> None:
    assert renderer.get_chapter("en", "nonexistent") is None


def test_get_chapter_falls_back_to_base_locale(renderer: HelpRenderer) -> None:
    chapter = renderer.get_chapter("fr", "chapter_01")

    assert chapter is not None
    assert chapter.chapter_id == "chapter_01"


# ---------------------------------------------------------------------------
# get_toc_pages
# ---------------------------------------------------------------------------


def test_get_toc_pages_splits_correctly(renderer: HelpRenderer) -> None:
    pages = renderer.get_toc_pages("en")

    assert len(pages) == 2
    assert len(pages[0]) == TOC_PAGE_SIZE
    assert len(pages[1]) == 2


def test_get_toc_pages_empty_locale_returns_empty(tmp_path: Path) -> None:
    """When neither the locale nor base locale has chapters, return empty."""
    fr_dir = tmp_path / "fr"
    _write_chapter(fr_dir, "chapter_01", "Chapitre 1", 1, ["# Chapitre 1"])

    r = HelpRenderer(tmp_path)
    r.initialize()

    assert r.get_toc_pages("de") == []


# ---------------------------------------------------------------------------
# build_toc_keyboard
# ---------------------------------------------------------------------------


def test_build_toc_keyboard_page1_structure(renderer: HelpRenderer) -> None:
    kb = renderer.build_toc_keyboard("en", current_page=1, total_pages=2)
    rows = kb.inline_keyboard

    # 6 chapter rows + 1 pagination row + 1 close row = 8 rows.
    assert len(rows) == 8
    # Chapter buttons.
    for i, row in enumerate(rows[:6]):
        assert len(row) == 1
        expected_id = f"chapter_{i + 1:02d}"
        assert row[0].callback_data == f"help:ch:{expected_id}:1"
    # Pagination row.
    assert len(rows[6]) == 3
    assert rows[6][0].callback_data == "help:toc:2"  # prev wraps to last
    assert rows[6][1].callback_data == "help:noop"   # indicator
    assert rows[6][2].callback_data == "help:toc:2"  # next
    # Close row.
    assert len(rows[7]) == 1
    assert rows[7][0].callback_data == "help:close"


def test_build_toc_keyboard_page2_structure(renderer: HelpRenderer) -> None:
    kb = renderer.build_toc_keyboard("en", current_page=2, total_pages=2)
    rows = kb.inline_keyboard

    # 2 chapter rows + 1 pagination row + 1 close row = 4 rows.
    assert len(rows) == 4
    assert rows[0][0].callback_data == "help:ch:chapter_07:1"
    assert rows[1][0].callback_data == "help:ch:chapter_08:1"
    # Pagination: prev=1, next=1 (wraps to first).
    assert len(rows[2]) == 3
    assert rows[2][0].callback_data == "help:toc:1"
    assert rows[2][2].callback_data == "help:toc:1"
    # Close.
    assert rows[3][0].callback_data == "help:close"


def test_build_toc_keyboard_single_page_no_pagination(renderer: HelpRenderer) -> None:
    kb = renderer.build_toc_keyboard("en", current_page=1, total_pages=1)
    rows = kb.inline_keyboard

    # 6 chapter rows + 1 close row = 7 rows (no pagination).
    assert len(rows) == 7
    assert rows[-1][0].callback_data == "help:close"


def test_long_chapter_id_uses_safe_callback_token(tmp_path: Path) -> None:
    chapter_id = "chapter_" + "非常长" * 12
    en_dir = tmp_path / "en"
    _write_chapter(en_dir, chapter_id, "Long chapter", 1, ["# Long"])
    renderer = HelpRenderer(tmp_path)
    renderer.initialize()

    keyboard = renderer.build_toc_keyboard("en", current_page=1, total_pages=1)
    callback_data = keyboard.inline_keyboard[0][0].callback_data

    assert callback_data is not None
    assert len(callback_data.encode("utf-8")) <= 64
    assert decode_callback_data(callback_data, "help:ch") == f"{chapter_id}:1"


# ---------------------------------------------------------------------------
# build_chapter_keyboard
# ---------------------------------------------------------------------------


def test_build_chapter_keyboard_single_page(renderer: HelpRenderer) -> None:
    """chapter_01 is the first chapter (no prev) with a single page.

    Layout: [Contents][Close] + [Next ➡️] (only-next single-page row).
    """
    kb = renderer.build_chapter_keyboard("chapter_01", "en", current_page=1, total_pages=1)
    rows = kb.inline_keyboard

    assert len(rows) == 2
    # Bottom row: [Contents] [Close].
    assert len(rows[0]) == 2
    assert rows[0][0].callback_data == "help:toc:1"
    assert rows[0][1].callback_data == "help:close"
    # Single-page chapter nav row: only Next (no prev chapter).
    assert len(rows[1]) == 1
    assert rows[1][0].callback_data == "help:ch:chapter_02:1"
    assert rows[1][0].text == "Next ➡️"


def test_build_chapter_keyboard_multi_page(renderer: HelpRenderer) -> None:
    """chapter_03 page 1: multi-page, first page, has prev chapter_02.

    Layout: pagination + [Contents][Close] + [⬅️ Previous: EN Chapter 2].
    """
    kb = renderer.build_chapter_keyboard("chapter_03", "en", current_page=1, total_pages=3)
    rows = kb.inline_keyboard

    # Pagination row + bottom row + chapter nav row = 3 rows.
    assert len(rows) == 3
    # Pagination: prev wraps to 3, next = 2.
    assert len(rows[0]) == 3
    assert rows[0][0].callback_data == "help:ch:chapter_03:3"
    assert rows[0][1].callback_data == "help:noop"
    assert rows[0][2].callback_data == "help:ch:chapter_03:2"
    # Bottom row.
    assert len(rows[1]) == 2
    assert rows[1][0].callback_data == "help:toc:1"
    assert rows[1][1].callback_data == "help:close"
    # Chapter nav row on page 1 of multi-page chapter: prev with title.
    assert len(rows[2]) == 1
    assert rows[2][0].callback_data == "help:ch:chapter_02:1"
    assert rows[2][0].text == "⬅️ Previous: EN Chapter 2"


# ---------------------------------------------------------------------------
# build_chapter_keyboard — cross-chapter navigation
# ---------------------------------------------------------------------------


def test_chapter_nav_single_page_with_both_neighbors(renderer: HelpRenderer) -> None:
    """chapter_02 is single-page with both prev (chapter_01) and next (chapter_03).

    Layout: [Contents][Close] + [⬅️ Previous][Next ➡️] (two buttons, no titles).
    """
    kb = renderer.build_chapter_keyboard("chapter_02", "en", current_page=1, total_pages=1)
    rows = kb.inline_keyboard

    assert len(rows) == 2
    assert rows[0][0].callback_data == "help:toc:1"
    assert rows[0][1].callback_data == "help:close"
    # Both neighbors → two-button row, no titles.
    assert len(rows[1]) == 2
    assert rows[1][0].callback_data == "help:ch:chapter_01:1"
    assert rows[1][0].text == "⬅️ Previous"
    assert rows[1][1].callback_data == "help:ch:chapter_03:1"
    assert rows[1][1].text == "Next ➡️"


def test_chapter_nav_single_page_first_chapter_only_next(renderer: HelpRenderer) -> None:
    """chapter_01 is the first chapter (no prev) — single-page, only Next button."""
    kb = renderer.build_chapter_keyboard("chapter_01", "en", current_page=1, total_pages=1)
    rows = kb.inline_keyboard

    assert len(rows) == 2
    assert len(rows[1]) == 1
    assert rows[1][0].callback_data == "help:ch:chapter_02:1"
    assert rows[1][0].text == "Next ➡️"


def test_chapter_nav_single_page_last_chapter_only_prev(renderer: HelpRenderer) -> None:
    """chapter_08 is the last chapter (no next) — single-page, only Previous button."""
    kb = renderer.build_chapter_keyboard("chapter_08", "en", current_page=1, total_pages=1)
    rows = kb.inline_keyboard

    assert len(rows) == 2
    assert len(rows[1]) == 1
    assert rows[1][0].callback_data == "help:ch:chapter_07:1"
    assert rows[1][0].text == "⬅️ Previous"


def test_chapter_nav_multi_page_first_page_shows_prev_with_title(
    renderer: HelpRenderer,
) -> None:
    """chapter_03 page 1 — multi-page first page shows prev button with title."""
    kb = renderer.build_chapter_keyboard("chapter_03", "en", current_page=1, total_pages=3)
    rows = kb.inline_keyboard

    # Last row is the prev-chapter nav (single button, with title).
    nav_row = rows[-1]
    assert len(nav_row) == 1
    assert nav_row[0].callback_data == "help:ch:chapter_02:1"
    assert nav_row[0].text == "⬅️ Previous: EN Chapter 2"


def test_chapter_nav_multi_page_last_page_shows_next_with_title(
    renderer: HelpRenderer,
) -> None:
    """chapter_03 last page (page 3) — multi-page last page shows next with title."""
    kb = renderer.build_chapter_keyboard("chapter_03", "en", current_page=3, total_pages=3)
    rows = kb.inline_keyboard

    # Pagination row + bottom row + next-chapter nav row.
    assert len(rows) == 3
    nav_row = rows[-1]
    assert len(nav_row) == 1
    assert nav_row[0].callback_data == "help:ch:chapter_04:1"
    assert nav_row[0].text == "Next: EN Chapter 4 ➡️"


def test_chapter_nav_multi_page_middle_page_no_nav_row(renderer: HelpRenderer) -> None:
    """chapter_03 page 2 (middle) — no chapter nav row appended."""
    kb = renderer.build_chapter_keyboard("chapter_03", "en", current_page=2, total_pages=3)
    rows = kb.inline_keyboard

    # Only pagination + bottom row; no chapter nav on middle pages.
    assert len(rows) == 2
    assert rows[0][1].callback_data == "help:noop"
    assert rows[1][0].callback_data == "help:toc:1"
    assert rows[1][1].callback_data == "help:close"


def test_chapter_nav_multi_page_first_chapter_page1_no_prev_button(
    tmp_path: Path,
) -> None:
    """A multi-page first chapter on page 1 has no prev button (no prev chapter)."""
    en_dir = tmp_path / "en"
    _write_chapter(
        en_dir,
        "chapter_01",
        "First Chapter",
        1,
        ["# First — Page 1", "# First — Page 2"],
    )
    _write_chapter(en_dir, "chapter_02", "Second Chapter", 2, ["# Second"])
    r = HelpRenderer(tmp_path)
    r.initialize()

    kb = r.build_chapter_keyboard("chapter_01", "en", current_page=1, total_pages=2)
    rows = kb.inline_keyboard

    # Pagination + [Contents][Close]; no prev-chapter nav on page 1 since
    # chapter_01 has no previous chapter.
    assert len(rows) == 2
    assert rows[0][1].callback_data == "help:noop"
    assert rows[1][0].callback_data == "help:toc:1"
    assert rows[1][1].callback_data == "help:close"


def test_chapter_nav_multi_page_last_chapter_last_page_no_next_button(
    tmp_path: Path,
) -> None:
    """A multi-page last chapter on its last page has no next button."""
    en_dir = tmp_path / "en"
    _write_chapter(en_dir, "chapter_01", "First Chapter", 1, ["# First"])
    _write_chapter(
        en_dir,
        "chapter_02",
        "Second Chapter",
        2,
        ["# Second — Page 1", "# Second — Page 2"],
    )
    r = HelpRenderer(tmp_path)
    r.initialize()

    kb = r.build_chapter_keyboard("chapter_02", "en", current_page=2, total_pages=2)
    rows = kb.inline_keyboard

    # Pagination + [Contents][Close]; no next-chapter nav since chapter_02
    # is the last chapter.
    assert len(rows) == 2
    assert rows[0][1].callback_data == "help:noop"
    assert rows[1][0].callback_data == "help:toc:1"
    assert rows[1][1].callback_data == "help:close"


def test_chapter_nav_single_chapter_no_nav_row(tmp_path: Path) -> None:
    """A single-chapter help has no prev/next neighbors → no nav row."""
    en_dir = tmp_path / "en"
    _write_chapter(en_dir, "chapter_01", "Only Chapter", 1, ["# Only"])
    r = HelpRenderer(tmp_path)
    r.initialize()

    kb = r.build_chapter_keyboard("chapter_01", "en", current_page=1, total_pages=1)
    rows = kb.inline_keyboard

    # Only [Contents][Close]; no nav row.
    assert len(rows) == 1
    assert rows[0][0].callback_data == "help:toc:1"
    assert rows[0][1].callback_data == "help:close"


def test_chapter_nav_callback_targets_open_first_page(renderer: HelpRenderer) -> None:
    """All cross-chapter nav callback data must end with ``:1`` (open first page)."""
    for chapter_id in ["chapter_01", "chapter_02", "chapter_03", "chapter_08"]:
        chapter = renderer.get_chapter("en", chapter_id)
        assert chapter is not None
        for page in range(1, len(chapter.pages) + 1):
            kb = renderer.build_chapter_keyboard(
                chapter_id, "en", current_page=page, total_pages=len(chapter.pages)
            )
            for row in kb.inline_keyboard:
                for btn in row:
                    if not btn.callback_data.startswith("help:ch:"):
                        continue
                    # Page-nav buttons within the same chapter may target
                    # other pages; chapter-nav buttons must target page 1.
                    target_chapter, _, target_page = btn.callback_data.rpartition(":")
                    if target_chapter.split(":")[-1] != chapter_id:
                        assert target_page == "1", (
                            f"chapter-nav button {btn.callback_data!r} "
                            f"does not target page 1"
                        )


# ---------------------------------------------------------------------------
# render_toc_page
# ---------------------------------------------------------------------------


def test_render_toc_page_returns_text_and_keyboard(renderer: HelpRenderer) -> None:
    text, kb = renderer.render_toc_page("en", page=1)

    assert isinstance(text, str)
    assert len(text) > 0
    assert isinstance(kb, InlineKeyboardMarkup)
    assert len(kb.inline_keyboard) == 8


def test_render_toc_page_uses_translated_title(renderer: HelpRenderer) -> None:
    text_en, _ = renderer.render_toc_page("en", page=1)
    text_zh, _ = renderer.render_toc_page("zh-cn", page=1)

    assert text_en != text_zh


# ---------------------------------------------------------------------------
# render_chapter_page
# ---------------------------------------------------------------------------


def test_render_chapter_page_returns_markdown_and_keyboard(renderer: HelpRenderer) -> None:
    result = renderer.render_chapter_page("en", "chapter_01", page=1)

    assert result is not None
    text, kb = result
    assert "Chapter 1" in text
    assert isinstance(kb, InlineKeyboardMarkup)


def test_render_chapter_page_multi_page(renderer: HelpRenderer) -> None:
    result = renderer.render_chapter_page("en", "chapter_03", page=2)

    assert result is not None
    text, kb = result
    assert "Page 2" in text
    # 3-page chapter -> pagination row + bottom row.
    assert len(kb.inline_keyboard) == 2


def test_render_chapter_page_nonexistent_chapter_returns_none(renderer: HelpRenderer) -> None:
    assert renderer.render_chapter_page("en", "nonexistent", page=1) is None


def test_render_chapter_page_out_of_range_page_returns_none(renderer: HelpRenderer) -> None:
    assert renderer.render_chapter_page("en", "chapter_01", page=5) is None


def test_render_chapter_page_zero_page_returns_none(renderer: HelpRenderer) -> None:
    assert renderer.render_chapter_page("en", "chapter_01", page=0) is None
