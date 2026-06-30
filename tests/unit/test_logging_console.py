from __future__ import annotations

from main import _compact_aiogram_polling_error, _parse_aiogram_retry_sleep


def test_compact_aiogram_polling_error_removes_noisy_prefixes() -> None:
    message = (
        "Failed to fetch updates - TelegramNetworkError: HTTP Client says - "
        "ClientConnectorError: Cannot connect to host api.telegram.org:443 ssl:default [None]"
    )

    assert _compact_aiogram_polling_error(message) == (
        "Cannot connect to host api.telegram.org:443 ssl:default [None]"
    )


def test_parse_aiogram_retry_sleep_message() -> None:
    assert _parse_aiogram_retry_sleep(
        "Sleep for 0.638185 seconds and try again... (tryings = 2, bot id = 8944500007)"
    ) == (0.638185, 2, "8944500007")


def test_parse_aiogram_retry_sleep_ignores_other_messages() -> None:
    assert _parse_aiogram_retry_sleep("Bot started") is None
