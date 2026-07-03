"""Manage multi-language help chapter cache and render TOC/chapter pages."""

from __future__ import annotations

from pathlib import Path

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from loguru import logger

from i18n import tr

from .loader import HelpChapter, load_help_locale

BASE_LOCALE = "en"
TOC_PAGE_SIZE = 6


class HelpRenderer:
    """Cache help chapters per locale and render TOC/chapter pages.

    The renderer scans locale subdirectories under a help root, loads
    chapters into an in-memory cache, and provides methods to build
    Telegram inline keyboards and render page text.
    """

    def __init__(self, help_root: Path) -> None:
        self._help_root = help_root
        self._log_dir = help_root / "log"
        self._cache: dict[str, list[HelpChapter]] = {}

    def initialize(self) -> None:
        """Scan all locale directories under ``help_root`` and cache chapters.

        Subdirectories named ``log`` are skipped. Logs a summary of how many
        locales and chapters were loaded.
        """
        if not self._help_root.exists() or not self._help_root.is_dir():
            logger.warning(f"Help root does not exist or is not a directory: {self._help_root}")
            return

        for entry in sorted(self._help_root.iterdir()):
            if not entry.is_dir() or entry.name == "log":
                continue
            chapters = load_help_locale(entry, self._log_dir)
            self._cache[entry.name] = chapters
            logger.info(f"Loaded {len(chapters)} help chapter(s) for locale '{entry.name}'")

        total = sum(len(c) for c in self._cache.values())
        logger.info(f"HelpRenderer initialized: {len(self._cache)} locale(s), {total} total chapter(s)")

    def get_chapters(self, locale: str) -> list[HelpChapter]:
        """Return chapters for *locale* with fallback.

        Fallback chain: *locale* -> ``BASE_LOCALE`` -> empty list.

        Args:
            locale: Locale code (e.g., ``"en"``, ``"zh-cn"``).

        Returns:
            List of ``HelpChapter`` objects (may be empty).
        """
        chapters = self._cache.get(locale)
        if chapters is not None:
            return chapters
        if locale != BASE_LOCALE:
            fallback = self._cache.get(BASE_LOCALE)
            if fallback is not None:
                return fallback
        return []

    def get_chapter(self, locale: str, chapter_id: str) -> HelpChapter | None:
        """Return a single chapter by ID.

        Args:
            locale: Locale code.
            chapter_id: Chapter filename stem.

        Returns:
            ``HelpChapter`` if found, otherwise ``None``.
        """
        for chapter in self.get_chapters(locale):
            if chapter.chapter_id == chapter_id:
                return chapter
        return None

    def get_toc_pages(self, locale: str) -> list[list[HelpChapter]]:
        """Split chapters into TOC pages of at most ``TOC_PAGE_SIZE`` each.

        Args:
            locale: Locale code.

        Returns:
            List of pages, each a list of at most ``TOC_PAGE_SIZE`` chapters.
        """
        chapters = self.get_chapters(locale)
        if not chapters:
            return []
        return [chapters[i : i + TOC_PAGE_SIZE] for i in range(0, len(chapters), TOC_PAGE_SIZE)]

    def build_toc_keyboard(
        self, locale: str, current_page: int, total_pages: int
    ) -> InlineKeyboardMarkup:
        """Build the TOC inline keyboard.

        Layout:
            - One chapter button per row (``callback_data = "help:ch:<id>:1"``).
            - Pagination row (only if ``total_pages > 1``): prev / indicator / next.
            - Close button on its own row.

        Args:
            locale: Locale code for button labels.
            current_page: Current TOC page (1-indexed).
            total_pages: Total number of TOC pages.

        Returns:
            ``InlineKeyboardMarkup`` for the TOC page.
        """
        pages = self.get_toc_pages(locale)
        page_chapters = pages[current_page - 1] if 1 <= current_page <= len(pages) else []

        rows: list[list[InlineKeyboardButton]] = []
        for chapter in page_chapters:
            rows.append(
                [
                    InlineKeyboardButton(
                        text=chapter.title,
                        callback_data=f"help:ch:{chapter.chapter_id}:1",
                    )
                ]
            )

        if total_pages > 1:
            rows.append(self._build_pagination_row(locale, current_page, total_pages, "toc"))

        rows.append([InlineKeyboardButton(text=tr("bot.help.close", locale), callback_data="help:close")])
        return InlineKeyboardMarkup(inline_keyboard=rows)

    def build_chapter_keyboard(
        self, chapter_id: str, locale: str, current_page: int, total_pages: int
    ) -> InlineKeyboardMarkup:
        """Build the chapter-page inline keyboard.

        Layout:
            - Pagination row (only if ``total_pages > 1``).
            - Bottom row: [Contents] [Close].
            - Cross-chapter navigation row (optional, see
              ``_build_chapter_nav_row``).

        Args:
            chapter_id: The chapter being viewed.
            locale: Locale code for button labels.
            current_page: Current chapter page (1-indexed).
            total_pages: Total pages in the chapter.

        Returns:
            ``InlineKeyboardMarkup`` for the chapter page.
        """
        rows: list[list[InlineKeyboardButton]] = []

        if total_pages > 1:
            rows.append(
                self._build_pagination_row(locale, current_page, total_pages, "chapter", chapter_id)
            )

        rows.append(
            [
                InlineKeyboardButton(text=tr("bot.help.contents", locale), callback_data="help:toc:1"),
                InlineKeyboardButton(text=tr("bot.help.close", locale), callback_data="help:close"),
            ]
        )

        prev_chapter, next_chapter = self._get_adjacent_chapters(locale, chapter_id)
        nav_row = self._build_chapter_nav_row(
            locale, current_page, total_pages, prev_chapter, next_chapter
        )
        if nav_row:
            rows.append(nav_row)

        return InlineKeyboardMarkup(inline_keyboard=rows)

    def _get_adjacent_chapters(
        self, locale: str, chapter_id: str
    ) -> tuple[HelpChapter | None, HelpChapter | None]:
        """Return ``(prev, next)`` chapters relative to *chapter_id*.

        Chapters are ordered by their ``order`` field. The first chapter has
        no previous; the last has no next.

        Args:
            locale: Locale code.
            chapter_id: Chapter filename stem to locate.

        Returns:
            ``(prev_chapter, next_chapter)`` tuple. Either element is
            ``None`` when no neighbor exists or when *chapter_id* is not
            found.
        """
        chapters = self.get_chapters(locale)
        for i, chapter in enumerate(chapters):
            if chapter.chapter_id == chapter_id:
                prev = chapters[i - 1] if i > 0 else None
                nxt = chapters[i + 1] if i < len(chapters) - 1 else None
                return prev, nxt
        return None, None

    def _build_chapter_nav_row(
        self,
        locale: str,
        current_page: int,
        total_pages: int,
        prev_chapter: HelpChapter | None,
        next_chapter: HelpChapter | None,
    ) -> list[InlineKeyboardButton] | None:
        """Build the cross-chapter navigation row for a chapter page.

        Rules (per spec):
            - Multi-page chapter:
                * Page 1 appends a single-button row "⬅️ Previous: <title>"
                  if *prev_chapter* exists.
                * Last page appends a single-button row "Next: <title> ➡️"
                  if *next_chapter* exists.
                * Middle pages append nothing.
            - Single-page chapter (``total_pages == 1``):
                * Append one row with both "⬅️ Previous" and "Next ➡️"
                  buttons (no titles) when both neighbors exist.
                * Append a single button when only one neighbor exists.
                * Append nothing when neither neighbor exists.

        Callback targets always open page 1 of the neighbor chapter.

        Args:
            locale: Locale code for button labels.
            current_page: Current chapter page (1-indexed).
            total_pages: Total pages in the current chapter.
            prev_chapter: Previous chapter in reading order, or ``None``.
            next_chapter: Next chapter in reading order, or ``None``.

        Returns:
            List of ``InlineKeyboardButton`` for the nav row, or ``None``
            when no row should be appended.
        """
        is_first_page = current_page == 1
        is_last_page = current_page == total_pages

        if total_pages > 1:
            if is_first_page and prev_chapter is not None:
                return [
                    InlineKeyboardButton(
                        text=tr(
                            "bot.help.prev_chapter_with_title",
                            locale,
                            title=prev_chapter.title,
                        ),
                        callback_data=f"help:ch:{prev_chapter.chapter_id}:1",
                    )
                ]
            if is_last_page and next_chapter is not None:
                return [
                    InlineKeyboardButton(
                        text=tr(
                            "bot.help.next_chapter_with_title",
                            locale,
                            title=next_chapter.title,
                        ),
                        callback_data=f"help:ch:{next_chapter.chapter_id}:1",
                    )
                ]
            return None

        buttons: list[InlineKeyboardButton] = []
        if prev_chapter is not None:
            buttons.append(
                InlineKeyboardButton(
                    text=tr("bot.help.prev_chapter", locale),
                    callback_data=f"help:ch:{prev_chapter.chapter_id}:1",
                )
            )
        if next_chapter is not None:
            buttons.append(
                InlineKeyboardButton(
                    text=tr("bot.help.next_chapter", locale),
                    callback_data=f"help:ch:{next_chapter.chapter_id}:1",
                )
            )
        return buttons if buttons else None

    def _build_pagination_row(
        self,
        locale: str,
        current_page: int,
        total_pages: int,
        mode: str,
        chapter_id: str | None = None,
    ) -> list[InlineKeyboardButton]:
        """Build a [prev] [page/total] [next] pagination row.

        Wrap-around navigation: prev of page 1 goes to last page, next of
        last page goes to page 1.

        Args:
            locale: Locale code for button labels.
            current_page: Current page (1-indexed).
            total_pages: Total number of pages.
            mode: ``"toc"`` or ``"chapter"`` — determines callback prefix.
            chapter_id: Required when ``mode == "chapter"``.

        Returns:
            List of three ``InlineKeyboardButton`` objects.
        """
        prev_page = current_page - 1 if current_page > 1 else total_pages
        next_page = current_page + 1 if current_page < total_pages else 1

        if mode == "chapter" and chapter_id is not None:
            prev_cb = f"help:ch:{chapter_id}:{prev_page}"
            next_cb = f"help:ch:{chapter_id}:{next_page}"
        else:
            prev_cb = f"help:toc:{prev_page}"
            next_cb = f"help:toc:{next_page}"

        return [
            InlineKeyboardButton(text=tr("bot.help.prev", locale), callback_data=prev_cb),
            InlineKeyboardButton(
                text=tr("bot.help.page_indicator", locale, page=current_page, total=total_pages),
                callback_data="help:noop",
            ),
            InlineKeyboardButton(text=tr("bot.help.next", locale), callback_data=next_cb),
        ]

    def render_toc_page(self, locale: str, page: int) -> tuple[str, InlineKeyboardMarkup]:
        """Render TOC page text and keyboard.

        Args:
            locale: Locale code.
            page: TOC page number (1-indexed).

        Returns:
            ``(text, keyboard)`` tuple.
        """
        pages = self.get_toc_pages(locale)
        total_pages = len(pages) if pages else 1
        text = tr("bot.help.toc_title", locale)
        keyboard = self.build_toc_keyboard(locale, page, total_pages)
        return text, keyboard

    def render_chapter_page(
        self, locale: str, chapter_id: str, page: int
    ) -> tuple[str, InlineKeyboardMarkup] | None:
        """Render a chapter page's Markdown and keyboard.

        Args:
            locale: Locale code.
            chapter_id: Chapter filename stem.
            page: Chapter page number (1-indexed).

        Returns:
            ``(text, keyboard)`` if the chapter and page exist, otherwise
            ``None``.
        """
        chapter = self.get_chapter(locale, chapter_id)
        if chapter is None:
            return None
        if page < 1 or page > len(chapter.pages):
            return None
        text = chapter.pages[page - 1]
        total_pages = len(chapter.pages) if chapter.pages else 1
        keyboard = self.build_chapter_keyboard(chapter_id, locale, page, total_pages)
        return text, keyboard
