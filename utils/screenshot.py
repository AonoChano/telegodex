"""Desktop screenshot capture and terminal rendering utilities."""

from __future__ import annotations

import asyncio
import re
import sys
from dataclasses import dataclass
from io import BytesIO
from typing import Any

from loguru import logger

_DPI_AWARENESS_ATTEMPTED = False


def _enable_windows_dpi_awareness() -> None:
    """Use physical pixel coordinates for mixed-DPI monitor layouts."""
    global _DPI_AWARENESS_ATTEMPTED
    if sys.platform != "win32" or _DPI_AWARENESS_ATTEMPTED:
        return
    _DPI_AWARENESS_ATTEMPTED = True

    try:
        import ctypes

        if ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return
    except Exception as exc:
        logger.debug(f"Per-monitor DPI awareness v2 is unavailable: {exc}")

    try:
        import ctypes

        if ctypes.windll.shcore.SetProcessDpiAwareness(2) == 0:
            return
    except Exception as exc:
        logger.debug(f"Per-monitor DPI awareness is unavailable: {exc}")

    try:
        import ctypes

        ctypes.windll.user32.SetProcessDPIAware()
    except Exception as exc:
        logger.debug(f"System DPI awareness is unavailable: {exc}")


_enable_windows_dpi_awareness()

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
    pyautogui = None  # type: ignore[assignment]
    _HAS_PYAUTOGUI = False

try:
    import pyte
    from pyte.screens import Char

    _HAS_PYTE = True
except ImportError:
    pyte = None  # type: ignore[misc,assignment]
    Char = None  # type: ignore[misc,assignment]
    _HAS_PYTE = False


@dataclass(frozen=True)
class DisplayMonitor:
    """A physical display and its virtual-desktop bounds."""

    identifier: str
    name: str
    left: int
    top: int
    right: int
    bottom: int
    is_primary: bool = False

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        return (self.left, self.top, self.right, self.bottom)


def list_display_monitors() -> list[DisplayMonitor]:
    """Return connected Windows displays in stable desktop order."""
    if sys.platform != "win32":
        return []
    _enable_windows_dpi_awareness()

    try:
        import ctypes
        from ctypes import wintypes

        class MonitorInfoEx(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT),
                ("dwFlags", wintypes.DWORD),
                ("szDevice", wintypes.WCHAR * 32),
            ]

        class DisplayDevice(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("DeviceName", wintypes.WCHAR * 32),
                ("DeviceString", wintypes.WCHAR * 128),
                ("StateFlags", wintypes.DWORD),
                ("DeviceID", wintypes.WCHAR * 128),
                ("DeviceKey", wintypes.WCHAR * 128),
            ]

        monitors: list[DisplayMonitor] = []
        callback_type = ctypes.WINFUNCTYPE(
            wintypes.BOOL,
            wintypes.HANDLE,
            wintypes.HDC,
            ctypes.POINTER(wintypes.RECT),
            wintypes.LPARAM,
        )

        @callback_type
        def collect_monitor(handle: Any, _dc: Any, _rect: Any, _data: Any) -> bool:
            info = MonitorInfoEx()
            info.cbSize = ctypes.sizeof(info)
            if not ctypes.windll.user32.GetMonitorInfoW(handle, ctypes.byref(info)):
                return True

            raw_name = str(info.szDevice) or f"DISPLAY{len(monitors) + 1}"
            short_name = raw_name.removeprefix(chr(92) * 2 + "." + chr(92))
            identifier = re.sub(r"[^A-Za-z0-9_-]", "_", short_name)[:32]
            device = DisplayDevice()
            device.cb = ctypes.sizeof(device)
            friendly_name = ""
            if ctypes.windll.user32.EnumDisplayDevicesW(raw_name, 0, ctypes.byref(device), 0):
                friendly_name = str(device.DeviceString).strip()
            name = f"{friendly_name} ({short_name})" if friendly_name else short_name
            rect = info.rcMonitor
            monitors.append(
                DisplayMonitor(
                    identifier=identifier,
                    name=name,
                    left=rect.left,
                    top=rect.top,
                    right=rect.right,
                    bottom=rect.bottom,
                    is_primary=bool(info.dwFlags & 1),
                )
            )
            return True

        if not ctypes.windll.user32.EnumDisplayMonitors(None, None, collect_monitor, 0):
            return []
        return sorted(monitors, key=lambda monitor: (not monitor.is_primary, monitor.top, monitor.left))
    except Exception as exc:
        logger.warning(f"Failed to enumerate desktop monitors: {exc}")
        return []


async def capture_desktop_screenshot(monitor: DisplayMonitor | None = None) -> bytes | None:
    """Capture one desktop monitor as PNG, or the default display if omitted."""
    _enable_windows_dpi_awareness()
    loop = asyncio.get_running_loop()

    def _save_png(img: Any) -> bytes | None:
        width, height = getattr(img, "size", (0, 0))
        if width <= 0 or height <= 0:
            raise ValueError(f"empty image size: {width}x{height}")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        data = buffer.getvalue()
        if not data:
            raise ValueError("empty PNG buffer")
        return data

    def _capture() -> bytes | None:
        if not _HAS_PIL and not _HAS_PYAUTOGUI:
            logger.warning("No screenshot library available. Install Pillow or pyautogui.")
            return None

        bbox = monitor.bbox if monitor is not None else None
        if bbox is not None and (monitor.width <= 0 or monitor.height <= 0):
            logger.warning(f"Ignoring invalid monitor bounds: {bbox}")
            return None

        if _HAS_PIL:
            try:
                if bbox is None:
                    img = ImageGrab.grab()
                elif sys.platform == "win32":
                    img = ImageGrab.grab(bbox=bbox, all_screens=True)
                else:
                    img = ImageGrab.grab(bbox=bbox)
                data = _save_png(img)
                if data:
                    return data
            except Exception as exc:
                logger.warning(f"Pillow desktop capture failed: {exc}")

        if _HAS_PYAUTOGUI:
            try:
                if bbox:
                    left, top, right, bottom = bbox
                    img = pyautogui.screenshot(region=(left, top, right - left, bottom - top))
                else:
                    img = pyautogui.screenshot()
                data = _save_png(img)
                if data:
                    return data
            except Exception as exc:
                logger.warning(f"pyautogui desktop capture failed: {exc}")

        return None

    return await loop.run_in_executor(None, _capture)


async def capture_terminal_screenshot() -> bytes | None:
    """Capture the default display for compatibility with older callers."""
    return await capture_desktop_screenshot()


# ---------------------------------------------------------------------------
# ANSI color helpers
# ---------------------------------------------------------------------------

# Standard 16 ANSI colors (0-15)
_ANSI_16: list[tuple[int, int, int]] = [
    (0, 0, 0),
    (170, 0, 0),
    (0, 170, 0),
    (170, 85, 0),
    (0, 0, 170),
    (170, 0, 170),
    (0, 170, 170),
    (170, 170, 170),
    (85, 85, 85),
    (255, 85, 85),
    (85, 255, 85),
    (255, 255, 85),
    (85, 85, 255),
    (255, 85, 255),
    (85, 255, 255),
    (255, 255, 255),
]

# Precomputed 256-color palette
_ANI_256: list[tuple[int, int, int]] = _ANSI_16[:]

# 6x6x6 RGB cube (16-231)
for r in range(6):
    for g in range(6):
        for b in range(6):
            _ANI_256.append(
                (
                    0 if r == 0 else 55 + r * 40,
                    0 if g == 0 else 55 + g * 40,
                    0 if b == 0 else 55 + b * 40,
                )
            )

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
        logger.warning("ansi_to_png requires pyte and Pillow. Install them: pip install pyte Pillow")
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
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Simple SGR matcher.
    text = re.sub(r"\x1b\[(\d*(?:;\d*)*)m", _ansi_to_html_replace, text)

    # Wrap in a pre block with a dark background.
    return (
        f'<pre style="background:#000;color:#ccc;padding:8px;font-family:monospace;white-space:pre-wrap;">{text}</pre>'
    )
