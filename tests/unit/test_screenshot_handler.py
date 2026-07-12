"""Unit tests for the Telegram-native screenshot monitor picker."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.types import Message

from bot.handlers import screenshot
from utils.screenshot import DisplayMonitor


def _monitor(
    identifier: str,
    *,
    name: str | None = None,
    left: int = 0,
    width: int = 1920,
    height: int = 1080,
    primary: bool = False,
) -> DisplayMonitor:
    return DisplayMonitor(
        identifier=identifier,
        name=name or identifier,
        left=left,
        top=0,
        right=left + width,
        bottom=height,
        is_primary=primary,
    )


def _message(*, bot: AsyncMock | None = None, message_thread_id: int = 222) -> Message:
    payload = {
        "message_id": 1,
        "date": int(datetime.now().timestamp()),
        "chat": {"id": 100, "type": "supergroup"},
        "from": {
            "id": 7,
            "is_bot": False,
            "first_name": "Test",
            "language_code": "en",
        },
        "text": "/screenshot",
        "message_thread_id": message_thread_id,
        "is_topic_message": True,
    }
    return Message.model_validate(payload).as_(bot or AsyncMock())


def test_monitor_keyboard_uses_one_row_per_display_and_bounded_callbacks() -> None:
    monitors = [
        _monitor("DISPLAY1", primary=True),
        _monitor("D" * 80, name="Wide secondary display", left=-2560, width=2560, height=1440),
    ]

    keyboard = screenshot.build_monitor_keyboard(monitors, user_id=7, locale="en")

    assert len(keyboard.inline_keyboard) == 2
    assert all(len(row) == 1 for row in keyboard.inline_keyboard)
    assert "DISPLAY1" in keyboard.inline_keyboard[0][0].text
    assert "1920x1080" in keyboard.inline_keyboard[0][0].text
    assert "Primary" in keyboard.inline_keyboard[0][0].text
    assert all(len((row[0].callback_data or "").encode("utf-8")) <= 64 for row in keyboard.inline_keyboard)


@pytest.mark.asyncio
async def test_command_prompts_when_multiple_monitors_are_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = _message()
    monitors = [_monitor("DISPLAY1", primary=True), _monitor("DISPLAY2", left=1920)]
    send_monitor_screenshot = AsyncMock()
    monkeypatch.setattr(screenshot, "_resolve_user_locale", AsyncMock(return_value="en"))
    monkeypatch.setattr(screenshot, "list_display_monitors", lambda: monitors)
    monkeypatch.setattr(screenshot, "_send_monitor_screenshot", send_monitor_screenshot)

    await screenshot.cmd_screenshot(message)

    send_monitor_screenshot.assert_not_awaited()
    method = message.bot.await_args.args[0]
    assert method.message_thread_id == 222
    assert len(method.reply_markup.inline_keyboard) == 2


@pytest.mark.asyncio
async def test_command_captures_single_monitor_in_same_topic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = _message()
    monitor = _monitor("DISPLAY1", primary=True)
    send_monitor_screenshot = AsyncMock(return_value=True)
    monkeypatch.setattr(screenshot, "_resolve_user_locale", AsyncMock(return_value="en"))
    monkeypatch.setattr(screenshot, "list_display_monitors", lambda: [monitor])
    monkeypatch.setattr(screenshot, "_send_monitor_screenshot", send_monitor_screenshot)

    await screenshot.cmd_screenshot(message)

    send_monitor_screenshot.assert_awaited_once()
    args = send_monitor_screenshot.await_args.args
    assert args[0] is message
    assert args[1].chat_id == 100
    assert args[1].message_thread_id == 222
    assert args[3] is monitor


@pytest.mark.asyncio
async def test_monitor_callback_rejects_other_users(monkeypatch: pytest.MonkeyPatch) -> None:
    monitor = _monitor("DISPLAY1")
    data = screenshot._monitor_callback_data(7, monitor)
    callback = SimpleNamespace(
        data=data,
        from_user=SimpleNamespace(id=8, language_code="en"),
        message=None,
        answer=AsyncMock(),
    )
    monkeypatch.setattr(screenshot, "_resolve_user_locale", AsyncMock(return_value="en"))

    await screenshot.handle_screenshot_callback(callback)

    callback.answer.assert_awaited_once()
    assert callback.answer.await_args.kwargs["show_alert"] is True


@pytest.mark.asyncio
async def test_monitor_callback_captures_selected_monitor_in_same_topic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = _message()
    monitor = _monitor("DISPLAY2", left=1920)
    data = screenshot._monitor_callback_data(7, monitor)
    callback = SimpleNamespace(
        data=data,
        from_user=message.from_user,
        message=message,
        answer=AsyncMock(),
    )
    send_monitor_screenshot = AsyncMock(return_value=True)
    monkeypatch.setattr(screenshot, "_resolve_user_locale", AsyncMock(return_value="en"))
    monkeypatch.setattr(screenshot, "list_display_monitors", lambda: [monitor])
    monkeypatch.setattr(screenshot, "_send_monitor_screenshot", send_monitor_screenshot)

    await screenshot.handle_screenshot_callback(callback)

    send_monitor_screenshot.assert_awaited_once()
    args = send_monitor_screenshot.await_args.args
    assert args[0] is message
    assert args[1].message_thread_id == 222
    assert args[3] is monitor
