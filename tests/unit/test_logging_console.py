from __future__ import annotations

import io
import os

from main import (
    _TerminalStatusLine,
    _compact_aiogram_polling_error,
    _fit_terminal_status_text,
    _format_aiogram_polling_status,
    _parse_aiogram_retry_sleep,
)


def test_compact_aiogram_polling_error_returns_short_category() -> None:
    message = (
        "Failed to fetch updates - TelegramNetworkError: HTTP Client says - "
        "ClientConnectorError: Cannot connect to host api.telegram.org:443 ssl:default [None]"
    )

    assert _compact_aiogram_polling_error(message) == "Telegram API unreachable"


def test_compact_aiogram_polling_error_classifies_aborted_windows_connection() -> None:
    message = (
        "Failed to fetch updates - TelegramNetworkError: HTTP Client says - "
        "ClientOSError: [WinError 1236] network connection aborted"
    )

    assert _compact_aiogram_polling_error(message) == "network connection aborted"


def test_format_aiogram_polling_status_stays_short() -> None:
    assert _format_aiogram_polling_status(
        "Telegram API unreachable", 2, 0.638185, "8944500007"
    ) == "Telegram polling: Telegram API unreachable | attempt=2, retry in 0.64s"



def test_fit_terminal_status_text_uses_ascii_ellipsis() -> None:
    assert _fit_terminal_status_text("abcdefghij", 8) == "abcde..."


def test_terminal_status_line_clears_before_each_update(monkeypatch) -> None:
    stream = io.StringIO()
    stream.isatty = lambda: True
    monkeypatch.setattr("main.sys.stderr", stream)
    monkeypatch.setattr(
        "main.shutil.get_terminal_size",
        lambda fallback: os.terminal_size((60, 20)),
    )

    status = _TerminalStatusLine()
    status.update(
        "Telegram polling: network connection aborted | attempt=0, retry in 1.23s"
    )
    status.update(
        "Telegram polling: Telegram API unreachable | attempt=1, retry in 2.34s"
    )

    output = stream.getvalue()
    assert output.count("\033[2K") == 2
    assert "WinError" not in output
    assert "network connection aborted | attempt=..." in output


def test_parse_aiogram_retry_sleep_message() -> None:
    assert _parse_aiogram_retry_sleep(
        "Sleep for 0.638185 seconds and try again... (tryings = 2, bot id = 8944500007)"
    ) == (0.638185, 2, "8944500007")


def test_parse_aiogram_retry_sleep_ignores_other_messages() -> None:
    assert _parse_aiogram_retry_sleep("Bot started") is None
