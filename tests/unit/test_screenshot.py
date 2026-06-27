from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from utils import screenshot


class _FakeImage:
    def __init__(self, size=(2, 2)) -> None:
        self.size = size

    def save(self, buffer: BytesIO, format: str) -> None:
        img = Image.new("RGB", self.size, (255, 0, 0))
        img.save(buffer, format=format)


@pytest.mark.asyncio
async def test_capture_screenshot_ignores_invalid_bbox_and_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def grab(*, bbox=None):
        calls.append(bbox)
        return _FakeImage()

    monkeypatch.setattr(screenshot, "_HAS_PIL", True)
    monkeypatch.setattr(screenshot, "_HAS_PYAUTOGUI", False)
    monkeypatch.setattr(screenshot, "_get_terminal_window_rect", lambda: (10, 10, 10, 20))
    monkeypatch.setattr(screenshot.ImageGrab, "grab", grab)

    data = await screenshot.capture_terminal_screenshot()

    assert data is not None
    assert calls == [None]


@pytest.mark.asyncio
async def test_capture_screenshot_retries_fullscreen_after_empty_window_image(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def grab(*, bbox=None):
        calls.append(bbox)
        if bbox is not None:
            return _FakeImage(size=(0, 0))
        return _FakeImage(size=(2, 2))

    monkeypatch.setattr(screenshot, "_HAS_PIL", True)
    monkeypatch.setattr(screenshot, "_HAS_PYAUTOGUI", False)
    monkeypatch.setattr(screenshot, "_get_terminal_window_rect", lambda: (1, 2, 20, 30))
    monkeypatch.setattr(screenshot.ImageGrab, "grab", grab)

    data = await screenshot.capture_terminal_screenshot()

    assert data is not None
    assert calls == [(1, 2, 20, 30), None]
