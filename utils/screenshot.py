"""Screenshot utilities for capturing the terminal window."""

from __future__ import annotations

import asyncio
import re
import sys
from io import BytesIO
from typing import Any

from aiogram.types import BufferedInputFile, Message
from loguru import logger

from bot.utils.routing import TelegramRoute

# Optional dependencies — handled via ImportError
try:
    from PIL import Image, ImageDraw, ImageFont, ImageGrab

    _HAS_PIL = True
except ImportError:
    Image = None  # type: ignore[misc,assignment]
    ImageDraw = None  # type: ignore[misc,assignment]
    ImageFont = None  # type: ignore[misc,assignment]
    _HAS_PIL = False

try:
    import pyautogui

    _HAS_PYAUTOGUI = True
except ImportError:
    _HAS_PYAUTOGUI = False

try:
    import pygetwindow

    _HAS_PYGETWINDOW = True
except ImportError:
    _HAS_PYGETWINDOW = False

try:
    import win32gui

    _HAS_WIN32GUI = True
except ImportError:
    _HAS_WIN32GUI = False

try:
    import pyte
    from pyte.screens import Char

    _HAS_PYTE = True
except ImportError:
    pyte = None  # type: ignore[misc,assignment]
    Char = None  # type: ignore[misc,assignment]
    _HAS_PYTE = False


def _get_terminal_window_rect() -> tuple[int, int, int, int] | None:
    """Attempt to locate the terminal window and return its bounding box.

    Returns ``(left, top, right, bottom)`` or ``None`` if detection fails.
    """
    if sys.platform != "win32":
        return None

    # Primary: use the current console window via ctypes.
    try:
        import ctypes

        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            if _HAS_WIN32GUI:
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                return (left, top, right, bottom)
            # Fallback via ctypes if win32gui is missing.
            rect = ctypes.wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
            return (rect.left, rect.top, rect.right, rect.bottom)
    except Exception as exc:
        logger.debug(f"Failed to get console window rect: {exc}")

    # Secondary: try pygetwindow with common terminal titles.
    if _HAS_PYGETWINDOW:
        for keyword in ("PowerShell", "Windows Terminal", "cmd", "Command Prompt"):
            try:
                windows = pygetwindow.getWindowsWithTitle(keyword)
                if windows:
                    win = windows[0]
                    return (win.left, win.top, win.right, win.bottom)
            except Exception as exc:
                logger.debug(f"pygetwindow search failed for '{keyword}': {exc}")

    # Tertiary: enumerate visible windows with win32gui.
    if _HAS_WIN32GUI:
        try:
            results: list[tuple[int, int, int, int]] = []

            def _enum_handler(hwnd: Any, _: Any) -> None:
                if not win32gui.IsWindowVisible(hwnd):
                    return
                title = win32gui.GetWindowText(hwnd)
                if any(k in title for k in ("PowerShell", "Windows Terminal", "cmd")):
                    results.append(win32gui.GetWindowRect(hwnd))

            win32gui.EnumWindows(_enum_handler, None)
            if results:
                return results[0]
        except Exception as exc:
            logger.debug(f"win32gui enumeration failed: {exc}")

    return None


async def capture_terminal_screenshot() -> bytes | None:
    """Capture the current terminal window as a PNG image.

    Returns PNG bytes or ``None`` if capture fails.
    """
    loop = asyncio.get_running_loop()

    def _capture() -> bytes | None:
        if not _HAS_PIL and not _HAS_PYAUTOGUI:
            logger.warning(
                "No screenshot library available. Install Pillow or pyautogui."
            )
            return None

        bbox = _get_terminal_window_rect()

        try:
            if _HAS_PIL:
                if bbox:
                    img = ImageGrab.grab(bbox=bbox)
                else:
                    img = ImageGrab.grab()
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                return buffer.getvalue()

            if _HAS_PYAUTOGUI:
                if bbox:
                    img = pyautogui.screenshot(region=bbox)
                else:
                    img = pyautogui.screenshot()
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                return buffer.getvalue()
        except Exception as exc:
            logger.warning(f"Screenshot capture failed: {exc}")
            return None

        return None

    return await loop.run_in_executor(None, _capture)


# ---------------------------------------------------------------------------
# ANSI color helpers
# ---------------------------------------------------------------------------

# Standard 16 ANSI colors (0-15)
_ANSI_16: list[tuple[int, int, int]] = [
    (0, 0, 0), (170, 0, 0), (0, 170, 0), (170, 85, 0),
    (0, 0, 170), (170, 0, 170), (0, 170, 170), (170, 170, 170),
    (85, 85, 85), (255, 85, 85), (85, 255, 85), (255, 255, 85),
    (85, 85, 255), (255, 85, 255), (85, 255, 255), (255, 255, 255),
]

# Precomputed 256-color palette
_ANI_256: list[tuple[int, int, int]] = _ANSI_16[:]

# 6x6x6 RGB cube (16-231)
for r in range(6):
    for g in range(6):
        for b in range(6):
            _ANI_256.append((
                0 if r == 0 else 55 + r * 40,
                0 if g == 0 else 55 + g * 40,
                0 if b == 0 else 55 + b * 40,
            ))

# Grayscale ramp (232-255)
for i in range(24):
    v = 8 + i * 10
    _ANI_256.append((v, v, v))


_NAMED_COLORS: dict[str, tuple[int, int, int]] = {
    "black": (0, 0, 0),
    "red": (170, 0, 0),
    "green": (0, 170, 0),
    "brown": (170, 85, 0),
    "yellow": (170, 85, 0),
    "blue": (0, 0, 170),
    "magenta": (170, 0, 170),
    "cyan": (0, 170, 170),
    "white": (170, 170, 170),
}


def _resolve_color(
    color: Any,
    default: tuple[int, int, int] = (0, 0, 0),
) -> tuple[int, int, int]:
    """Convert a pyte color value to an RGB tuple."""
    if color is None or color == "default":
        return default
    if isinstance(color, str):
        if color.startswith("#") and len(color) == 7:
            try:
                return (
                    int(color[1:3], 16),
                    int(color[3:5], 16),
                    int(color[5:7], 16),
                )
            except ValueError:
                return default
        lower = color.lower()
        if lower in _NAMED_COLORS:
            return _NAMED_COLORS[lower]
        return default
    if isinstance(color, int):
        if 0 <= color < 256:
            return _ANI_256[color]
        return default
    return default


def ansi_to_png(
    ansi_text: str,
    columns: int = 80,
    rows: int = 24,
    cell_width: int = 8,
    cell_height: int = 16,
) -> bytes | None:
    """Convert ANSI escape sequences to a PNG image.

    Uses ``pyte`` to emulate a terminal and ``Pillow`` to render the
    resulting screen buffer as a PNG.

    Returns PNG bytes or ``None`` if rendering fails.
    """
    if not _HAS_PIL or not _HAS_PYTE:
        logger.warning(
            "ansi_to_png requires pyte and Pillow. "
            "Install them: pip install pyte Pillow"
        )
        return None

    try:
        screen = pyte.Screen(columns, rows)
        stream = pyte.Stream(screen)
        stream.feed(ansi_text)
    except Exception as exc:
        logger.warning(f"ANSI parsing failed: {exc}")
        return None

    img_width = columns * cell_width
    img_height = rows * cell_height

    try:
        img = Image.new("RGB", (img_width, img_height), (0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Try to load a monospace font; fall back to default.
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None
        try:
            font = ImageFont.truetype("DejaVuSansMono.ttf", cell_height - 2)
        except Exception:
            try:
                font = ImageFont.truetype("consola.ttf", cell_height - 2)
            except Exception:
                try:
                    font = ImageFont.truetype("cour.ttf", cell_height - 2)
                except Exception:
                    font = ImageFont.load_default()

        for row_idx in range(rows):
            for col_idx in range(columns):
                char: Any = screen.buffer.get(row_idx, {}).get(col_idx)
                if char is None:
                    continue

                bg = _resolve_color(char.bg, default=(0, 0, 0))
                fg = _resolve_color(char.fg, default=(170, 170, 170))
                ch = char.data if char.data else " "

                x = col_idx * cell_width
                y = row_idx * cell_height

                # Draw background
                draw.rectangle(
                    [x, y, x + cell_width - 1, y + cell_height - 1],
                    fill=bg,
                )

                # Draw character
                if ch != " ":
                    draw.text((x, y), ch, fill=fg, font=font)

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()
    except Exception as exc:
        logger.warning(f"ANSI to PNG rendering failed: {exc}")
        return None


def _ansi_to_html_replace(match: re.Match[str]) -> str:
    """Replace an ANSI escape sequence with an HTML span (basic 8-color)."""
    codes = match.group(1)
    if not codes:
        return "</span>"
    parts = codes.split(";")
    styles: list[str] = []
    for part in parts:
        try:
            code = int(part)
        except ValueError:
            continue
        if 30 <= code <= 37:
            styles.append(f"color:ansi{code - 30}")
        elif 40 <= code <= 47:
            styles.append(f"background-color:ansi{code - 40}")
        elif code == 0:
            return "</span>"
    if styles:
        return f'<span style="{";".join(styles)}">'
    return ""


def ansi_to_html(ansi_text: str) -> str:
    """Convert ANSI escape sequences to colored HTML.

    This is a lightweight fallback when ``ansi_to_png`` is unavailable.
    Only basic SGR codes (colors 30-37, 40-47, reset) are handled.
    """
    # Strip unsupported OSC hyperlinks and other complex sequences.
    text = re.sub(r"\x1b\]8;.*?;.*?\x1b\\", "", ansi_text)
    text = re.sub(r"\x1b\]\d+;.*?\x07", "", text)

    # Escape HTML first so we don't escape the spans we insert later.
    text = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    # Simple SGR matcher.
    text = re.sub(r"\x1b\[(\d*(?:;\d*)*)m", _ansi_to_html_replace, text)

    # Wrap in a pre block with a dark background.
    return (
        '<pre style="background:#000;color:#ccc;padding:8px;'
        'font-family:monospace;white-space:pre-wrap;">'
        f"{text}</pre>"
    )


async def send_screenshot_to_chat(
    message: Message,
    route: TelegramRoute,
) -> None:
    """Capture a screenshot and send it to the chat."""
    png_bytes = await capture_terminal_screenshot()
    if png_bytes is None:
        await message.answer(
            "Failed to capture screenshot. "
            "Please install Pillow (`pip install Pillow`) or pyautogui.",
            **route.send_kwargs(),
        )
        return

    try:
        await message.answer_photo(
            photo=BufferedInputFile(png_bytes, filename="screenshot.png"),
            caption="Terminal screenshot",
            **route.send_kwargs(),
        )
    except Exception as exc:
        logger.warning(f"Failed to send screenshot: {exc}")
        await message.answer(
            f"Failed to send screenshot: {exc}",
            **route.send_kwargs(),
        )
