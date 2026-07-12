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
async def test_capture_selected_monitor_uses_virtual_desktop_bounds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[tuple[int, int, int, int] | None, bool]] = []

    def grab(*, bbox=None, all_screens=False):
        calls.append((bbox, all_screens))
        return _FakeImage()

    monkeypatch.setattr(screenshot, "_HAS_PIL", True)
    monkeypatch.setattr(screenshot, "_HAS_PYAUTOGUI", False)
    monkeypatch.setattr(screenshot, "_enable_windows_dpi_awareness", lambda: None)
    monkeypatch.setattr(screenshot.sys, "platform", "win32")
    monkeypatch.setattr(screenshot.ImageGrab, "grab", grab)
    monitor = screenshot.DisplayMonitor(
        identifier="DISPLAY2",
        name="DISPLAY2",
        left=-1920,
        top=0,
        right=0,
        bottom=1080,
    )

    data = await screenshot.capture_desktop_screenshot(monitor)

    assert data is not None
    assert calls == [((-1920, 0, 0, 1080), True)]


@pytest.mark.asyncio
async def test_capture_selected_monitor_falls_back_to_pyautogui_region(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pil_calls = []
    pyautogui_calls = []

    def grab(*, bbox=None, all_screens=False):
        pil_calls.append((bbox, all_screens))
        return _FakeImage(size=(0, 0))

    class FakePyAutoGui:
        @staticmethod
        def screenshot(*, region=None):
            pyautogui_calls.append(region)
            return _FakeImage()

    monkeypatch.setattr(screenshot, "_HAS_PIL", True)
    monkeypatch.setattr(screenshot, "_HAS_PYAUTOGUI", True)
    monkeypatch.setattr(screenshot, "_enable_windows_dpi_awareness", lambda: None)
    monkeypatch.setattr(screenshot.sys, "platform", "win32")
    monkeypatch.setattr(screenshot.ImageGrab, "grab", grab)
    monkeypatch.setattr(screenshot, "pyautogui", FakePyAutoGui())
    monitor = screenshot.DisplayMonitor(
        identifier="DISPLAY1",
        name="DISPLAY1",
        left=10,
        top=20,
        right=810,
        bottom=620,
    )

    data = await screenshot.capture_desktop_screenshot(monitor)

    assert data is not None
    assert pil_calls == [((10, 20, 810, 620), True)]
    assert pyautogui_calls == [(10, 20, 800, 600)]


@pytest.mark.asyncio
async def test_capture_rejects_invalid_monitor_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    def grab(**_kwargs):
        raise AssertionError("capture should not be attempted")

    monkeypatch.setattr(screenshot, "_HAS_PIL", True)
    monkeypatch.setattr(screenshot, "_HAS_PYAUTOGUI", False)
    monkeypatch.setattr(screenshot, "_enable_windows_dpi_awareness", lambda: None)
    monkeypatch.setattr(screenshot.ImageGrab, "grab", grab)
    monitor = screenshot.DisplayMonitor(
        identifier="DISPLAY1",
        name="DISPLAY1",
        left=10,
        top=10,
        right=10,
        bottom=100,
    )

    assert await screenshot.capture_desktop_screenshot(monitor) is None
