"""Send file handler — /send command with interactive directory browser."""

from __future__ import annotations

import asyncio
import hashlib
import os
import subprocess
from fnmatch import fnmatch
from pathlib import Path

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from loguru import logger

from bot.utils.routing import TelegramRoute
from storage import ContextManager

router = Router(name="send")

_MAX_FILE_SIZE = 50 * 1024 * 1024
_SECRET_PATTERNS = [
    "*.pem",
    "*.key",
    "*.p12",
    ".env",
    "*credential*",
    "*secret*",
    "*password*",
    "*token*",
]
_EXCLUDED_DIRS = {
    "node_modules",
    "__pycache__",
    ".venv",
    "dist",
    "build",
    ".git",
    ".agents",
    ".claude",
    ".codex",
    ".trae",
}

_path_registry: dict[str, str] = {}


def _path_token(path: str) -> str:
    token = hashlib.blake2b(path.encode(), digest_size=8).hexdigest()
    if len(_path_registry) > 5000:
        _path_registry.clear()
    _path_registry[token] = path
    return token


def _resolve_token(token: str) -> str | None:
    return _path_registry.get(token)


async def _session_cwd(
    context_manager: ContextManager,
    user_id: int,
    thread_id: int | None,
    chat_id: int | None,
) -> Path:
    conv = await context_manager.get_or_create_conversation(
        user_id, thread_id=thread_id, chat_id=chat_id
    )
    if conv.cwd:
        return Path(conv.cwd).resolve()
    return Path(os.getcwd()).resolve()


def _is_within_cwd(path: Path, cwd: Path) -> bool:
    try:
        path.relative_to(cwd)
        return True
    except ValueError:
        return False


def _is_hidden(path: Path) -> bool:
    return any(part.startswith(".") for part in path.parts)


def _is_secret_pattern(name: str) -> bool:
    lower = name.lower()
    return any(fnmatch(lower, pattern.lower()) for pattern in _SECRET_PATTERNS)


def _is_excluded_dir(path: Path) -> bool:
    return any(part in _EXCLUDED_DIRS for part in path.parts)


def _check_size(path: Path) -> bool:
    try:
        return path.stat().st_size <= _MAX_FILE_SIZE
    except OSError:
        return False


async def _is_gitignored(path: Path, cwd: Path) -> bool:
    try:
        proc = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(
                ["git", "check-ignore", "-q", str(path)],
                cwd=str(cwd),
                capture_output=True,
            ),
        )
        return proc.returncode == 0
    except Exception:
        return False


async def _validate_file(path: Path, cwd: Path) -> str | None:
    real_path = path.resolve()
    if not _is_within_cwd(real_path, cwd):
        return "Path is outside of working directory"
    if not real_path.exists():
        return "Path does not exist"
    if _is_hidden(real_path):
        return "Hidden files are not allowed"
    if _is_secret_pattern(real_path.name):
        return "Secret files are not allowed"
    if _is_excluded_dir(real_path):
        return "Path is in an excluded directory"
    if not _check_size(real_path):
        return "File exceeds 50 MB limit"
    if await _is_gitignored(real_path, cwd):
        return "Gitignored files are not allowed"
    return None


def _allow_listing(name: str) -> bool:
    if name.startswith("."):
        return False
    if name in _EXCLUDED_DIRS:
        return False
    return not _is_secret_pattern(name)


async def _send_file(message: Message, path: Path, route: TelegramRoute) -> None:
    fs = FSInputFile(str(path))
    kwargs = route.send_kwargs()

    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}:
        try:
            await message.answer_photo(fs, caption=path.name, **kwargs)
            return
        except Exception as exc:
            logger.warning(f"Failed to send as photo: {exc}")

    try:
        await message.answer_document(fs, caption=path.name, **kwargs)
    except Exception as exc:
        logger.error(f"Failed to send file: {exc}")
        await message.answer(f"Failed to send file: {exc}", **kwargs)


def _is_glob_pattern(text: str) -> bool:
    return any(c in text for c in "*?[")


def _glob_files(cwd: Path, pattern: str) -> list[Path]:
    results = []
    try:
        for p in cwd.rglob(pattern):
            if p.is_file() and _allow_listing(p.name):
                results.append(p)
    except PermissionError:
        pass
    return results


def _search_substring(cwd: Path, substring: str) -> list[Path]:
    results = []
    lower = substring.lower()
    try:
        for p in cwd.rglob("*"):
            if p.is_file() and lower in p.name.lower() and _allow_listing(p.name):
                results.append(p)
    except PermissionError:
        pass
    return results


def _build_picker_keyboard(paths: list[Path], cwd: Path) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    for p in paths[:10]:
        try:
            rel = str(p.relative_to(cwd))
        except ValueError:
            rel = str(p)
        token = _path_token(rel)
        label = p.name
        if len(label) > 40:
            label = label[:37] + "..."
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"[FILE] {label}",
                    callback_data=f"send:pick:{token}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _build_browser_keyboard(
    cwd: Path, current_dir: Path, page: int = 0
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []

    if current_dir != cwd:
        try:
            parent_rel = str(current_dir.parent.relative_to(cwd))
        except ValueError:
            parent_rel = "."
        parent_token = _path_token(parent_rel)
        buttons.append(
            [
                InlineKeyboardButton(
                    text="[UP] Parent",
                    callback_data=f"send:up:{parent_token}",
                )
            ]
        )

    entries: list[tuple[str, str, str]] = []

    try:
        dir_entries = list(current_dir.iterdir())
    except PermissionError:
        dir_entries = []
    except OSError:
        dir_entries = []

    for entry in sorted(dir_entries):
        if entry.is_dir():
            if not _allow_listing(entry.name):
                continue
            try:
                rel = str(entry.relative_to(cwd))
            except ValueError:
                continue
            entries.append(("[DIR] " + entry.name, rel, "open"))
        elif entry.is_file():
            if not _allow_listing(entry.name):
                continue
            try:
                rel = str(entry.relative_to(cwd))
            except ValueError:
                continue
            entries.append(("[FILE] " + entry.name, rel, "pick"))

    per_page = 20
    total_pages = (len(entries) + per_page - 1) // per_page
    page = max(0, min(page, total_pages - 1)) if total_pages else 0
    page_entries = entries[page * per_page : (page + 1) * per_page]

    for label, rel, action in page_entries:
        token = _path_token(rel)
        buttons.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"send:{action}:{token}",
                )
            ]
        )

    if total_pages > 1:
        nav: list[InlineKeyboardButton] = []
        current_rel = str(current_dir.relative_to(cwd)) if current_dir != cwd else "."
        current_token = _path_token(current_rel)
        if page > 0:
            nav.append(
                InlineKeyboardButton(
                    text="<< Prev",
                    callback_data=f"send:page:{current_token}:{page - 1}",
                )
            )
        nav.append(
            InlineKeyboardButton(
                text=f"({page + 1}/{total_pages})",
                callback_data="send:noop",
            )
        )
        if page < total_pages - 1:
            nav.append(
                InlineKeyboardButton(
                    text="Next >>",
                    callback_data=f"send:page:{current_token}:{page + 1}",
                )
            )
        buttons.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("send"))
async def cmd_send(message: Message, context_manager: ContextManager) -> None:
    route = TelegramRoute.from_message(message)
    user_id = message.from_user.id
    thread_id = route.storage_thread_id
    cwd = await _session_cwd(context_manager, user_id, thread_id, route.chat_id)

    text = message.text or ""
    if text.startswith("/send"):
        text = text[len("/send") :].strip()

    if not text:
        keyboard = _build_browser_keyboard(cwd, cwd, page=0)
        await message.answer(
            f"Browsing: `{cwd}`",
            reply_markup=keyboard,
            **route.send_kwargs(),
        )
        return

    exact = cwd / text
    if exact.exists():
        err = await _validate_file(exact, cwd)
        if err is None:
            await _send_file(message, exact, route)
        else:
            await message.answer(
                f"Access denied: {err}",
                **route.send_kwargs(),
            )
        return

    if _is_glob_pattern(text):
        matches = _glob_files(cwd, text)
        if not matches:
            await message.answer(
                "No files matched the pattern.",
                **route.send_kwargs(),
            )
            return
        if len(matches) == 1:
            err = await _validate_file(matches[0], cwd)
            if err is None:
                await _send_file(message, matches[0], route)
            else:
                await message.answer(
                    f"Access denied: {err}",
                    **route.send_kwargs(),
                )
            return
        keyboard = _build_picker_keyboard(matches, cwd)
        await message.answer(
            f"Found {len(matches)} files. Select one:",
            reply_markup=keyboard,
            **route.send_kwargs(),
        )
        return

    matches = _search_substring(cwd, text)
    if not matches:
        await message.answer(
            "No files found.",
            **route.send_kwargs(),
        )
        return
    if len(matches) == 1:
        err = await _validate_file(matches[0], cwd)
        if err is None:
            await _send_file(message, matches[0], route)
        else:
            await message.answer(
                f"Access denied: {err}",
                **route.send_kwargs(),
            )
        return
    keyboard = _build_picker_keyboard(matches, cwd)
    await message.answer(
        f"Found {len(matches)} files. Select one:",
        reply_markup=keyboard,
        **route.send_kwargs(),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("send:"))
async def handle_send_callback(
    callback: CallbackQuery, context_manager: ContextManager
) -> None:
    route = TelegramRoute.from_message(callback.message)
    user_id = callback.from_user.id
    thread_id = route.storage_thread_id
    cwd = await _session_cwd(context_manager, user_id, thread_id, route.chat_id)

    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer("Invalid callback", show_alert=True)
        return

    action = parts[1]
    token = parts[2]

    if action == "noop":
        await callback.answer()
        return

    rel_str = _resolve_token(token)
    if rel_str is None:
        await callback.answer(
            "Session expired, please run /send again",
            show_alert=True,
        )
        return

    target = cwd / rel_str
    real_target = target.resolve()

    if not _is_within_cwd(real_target, cwd):
        await callback.answer("Access denied", show_alert=True)
        return

    if action == "pick":
        err = await _validate_file(real_target, cwd)
        if err:
            await callback.answer(
                f"Access denied: {err}",
                show_alert=True,
            )
            return
        await _send_file(callback.message, real_target, route)
        await callback.answer()
        return

    if action == "open":
        if not real_target.is_dir():
            await callback.answer("Not a directory", show_alert=True)
            return
        page = 0
        if len(parts) >= 4:
            try:
                page = int(parts[3])
            except ValueError:
                page = 0
        keyboard = _build_browser_keyboard(cwd, real_target, page=page)
        try:
            await callback.message.edit_reply_markup(reply_markup=keyboard)
        except Exception as exc:
            logger.warning(f"Failed to update browser: {exc}")
            await callback.message.answer(
                f"Browsing: `{real_target}`",
                reply_markup=keyboard,
                **route.send_kwargs(),
            )
        await callback.answer()
        return

    if action == "up":
        parent = real_target.parent if real_target != cwd else cwd
        if not _is_within_cwd(parent, cwd):
            parent = cwd
        keyboard = _build_browser_keyboard(cwd, parent, page=0)
        try:
            await callback.message.edit_reply_markup(reply_markup=keyboard)
        except Exception as exc:
            logger.warning(f"Failed to update browser: {exc}")
            await callback.message.answer(
                f"Browsing: `{parent}`",
                reply_markup=keyboard,
                **route.send_kwargs(),
            )
        await callback.answer()
        return

    if action == "page":
        if len(parts) < 4:
            await callback.answer("Invalid page", show_alert=True)
            return
        try:
            page = int(parts[3])
        except ValueError:
            page = 0
        keyboard = _build_browser_keyboard(cwd, real_target, page=page)
        try:
            await callback.message.edit_reply_markup(reply_markup=keyboard)
        except Exception as exc:
            logger.warning(f"Failed to update browser: {exc}")
            await callback.message.answer(
                f"Browsing: `{real_target}`",
                reply_markup=keyboard,
                **route.send_kwargs(),
            )
        await callback.answer()
        return

    await callback.answer("Unknown action", show_alert=True)
