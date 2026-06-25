"""Unit tests for Telegram draft degradation behavior."""

from __future__ import annotations

from typing import Any

import pytest

import bot.telegram_draft as telegram_draft
from bot.telegram_draft import DraftStream


@pytest.fixture(autouse=True)
def reset_draft_state() -> None:
    telegram_draft._DRAFT_UNAVAILABLE = False
    telegram_draft._UNSUPPORTED_PEERS.clear()
    telegram_draft._last_log_time.clear()


@pytest.mark.asyncio
async def test_legacy_rich_preview_is_edited_as_rich_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    telegram_draft._UNSUPPORTED_PEERS.add((100, 222))

    async def fake_post(
        _token: str,
        method: str,
        payload: dict[str, Any],
    ) -> tuple[bool, str, Any]:
        calls.append((method, payload))
        if method == "sendRichMessage":
            return True, "", {"message_id": 42}
        if method == "editMessageText":
            return True, "", {"message_id": 42}
        raise AssertionError(f"unexpected method: {method}")

    monkeypatch.setattr(telegram_draft, "_post_bot_method", fake_post)

    stream = DraftStream("TOKEN", 100, message_thread_id=222, use_rich=True)

    assert await stream.push("first") is True
    assert await stream.push("second") is True

    assert [method for method, _ in calls] == ["sendRichMessage", "editMessageText"]
    assert calls[0][1]["message_thread_id"] == 222
    edit_payload = calls[1][1]
    assert edit_payload["chat_id"] == 100
    assert edit_payload["message_id"] == 42
    assert edit_payload["rich_message"] == {"markdown": "second"}
    assert "text" not in edit_payload
    assert "message_thread_id" not in edit_payload


@pytest.mark.asyncio
async def test_legacy_send_without_message_id_does_not_fall_back_to_plain_send(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    telegram_draft._UNSUPPORTED_PEERS.add((100, 222))

    async def fake_post(
        _token: str,
        method: str,
        payload: dict[str, Any],
    ) -> tuple[bool, str, Any]:
        calls.append((method, payload))
        if method == "sendRichMessage":
            return True, "", True
        raise AssertionError(f"unexpected method: {method}")

    monkeypatch.setattr(telegram_draft, "_post_bot_method", fake_post)

    stream = DraftStream("TOKEN", 100, message_thread_id=222, use_rich=True)

    assert await stream.push("partial") is True
    assert stream.state == "GIVE_UP"
    assert await stream.push("new partial") is False

    assert [method for method, _ in calls] == ["sendRichMessage"]


@pytest.mark.asyncio
async def test_legacy_edit_failure_stops_preview_resends_until_final(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    telegram_draft._UNSUPPORTED_PEERS.add((100, 222))

    async def fake_post(
        _token: str,
        method: str,
        payload: dict[str, Any],
    ) -> tuple[bool, str, Any]:
        calls.append((method, payload))
        if method == "sendRichMessage":
            return True, "", {"message_id": 42}
        if method == "editMessageText":
            return False, "Bad Request: message to edit not found", None
        if method == "deleteMessage":
            return True, "", True
        raise AssertionError(f"unexpected method: {method}")

    monkeypatch.setattr(telegram_draft, "_post_bot_method", fake_post)

    stream = DraftStream("TOKEN", 100, message_thread_id=222, use_rich=True)

    assert await stream.push("first") is True
    assert await stream.push("second") is False
    assert stream.state == "GIVE_UP"
    assert await stream.push("third") is False
    assert await stream.finalize("final") is True

    methods = [method for method, _ in calls]
    assert methods == [
        "sendRichMessage",
        "editMessageText",
        "editMessageText",
        "sendRichMessage",
        "deleteMessage",
    ]
    assert calls[1][1]["rich_message"] == {"markdown": "second"}
    assert calls[2][1]["text"] == "second"
    assert calls[3][1]["rich_message"] == {"markdown": "final"}
