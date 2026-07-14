"""Tests for Telegram callback payload budgeting."""

from __future__ import annotations

from bot.utils.callback_data import (
    TELEGRAM_CALLBACK_DATA_MAX_BYTES,
    CallbackDataRegistry,
)


def test_short_payload_stays_readable() -> None:
    registry = CallbackDataRegistry()

    encoded = registry.encode("model", "openai:gpt-4.1")

    assert encoded == "model:openai:gpt-4.1"
    assert registry.decode(encoded, "model") == "openai:gpt-4.1"


def test_long_unicode_payload_uses_telegram_safe_token() -> None:
    registry = CallbackDataRegistry()
    payload = "provider:" + "超长模型名称" * 20

    encoded = registry.encode("model", payload)

    assert encoded.startswith("model:~")
    assert len(encoded.encode("utf-8")) <= TELEGRAM_CALLBACK_DATA_MAX_BYTES
    assert registry.decode(encoded, "model") == payload


def test_payload_starting_with_token_marker_round_trips() -> None:
    registry = CallbackDataRegistry()

    encoded = registry.encode("provider", "~local")

    assert encoded.startswith("provider:~")
    assert registry.decode(encoded, "provider") == "~local"


def test_expired_token_is_rejected() -> None:
    now = [100.0]
    registry = CallbackDataRegistry(ttl_seconds=10, clock=lambda: now[0])
    encoded = registry.encode("model", "x" * 100)

    now[0] = 111.0

    assert registry.decode(encoded, "model") is None


def test_lru_evicts_oldest_token() -> None:
    registry = CallbackDataRegistry(max_entries=2)
    first = registry.encode("model", "a" * 100)
    second = registry.encode("model", "b" * 100)
    assert registry.decode(first, "model") == "a" * 100
    third = registry.encode("model", "c" * 100)

    assert registry.decode(first, "model") == "a" * 100
    assert registry.decode(second, "model") is None
    assert registry.decode(third, "model") == "c" * 100
