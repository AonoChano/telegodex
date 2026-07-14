"""Telegram-safe callback data encoding for dynamic button payloads."""

from __future__ import annotations

import secrets
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass

TELEGRAM_CALLBACK_DATA_MAX_BYTES = 64


@dataclass(frozen=True)
class _CallbackEntry:
    namespace: str
    payload: str
    expires_at: float


class CallbackDataRegistry:
    """Keep oversized callback payloads behind short-lived opaque tokens."""

    def __init__(
        self,
        *,
        max_entries: int = 5000,
        ttl_seconds: float = 3600.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self._max_entries = max_entries
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._entries: OrderedDict[str, _CallbackEntry] = OrderedDict()

    def encode(self, namespace: str, payload: str) -> str:
        """Return readable callback data when it fits, otherwise a short token."""
        if not namespace or any(not part for part in namespace.split(":")):
            raise ValueError("namespace must contain non-empty path components")

        direct = f"{namespace}:{payload}"
        if (
            not payload.startswith("~")
            and len(direct.encode("utf-8")) <= TELEGRAM_CALLBACK_DATA_MAX_BYTES
        ):
            return direct

        self._prune_expired()
        token = self._new_token()
        self._entries[token] = _CallbackEntry(
            namespace=namespace,
            payload=payload,
            expires_at=self._clock() + self._ttl_seconds,
        )
        self._entries.move_to_end(token)
        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)

        encoded = f"{namespace}:~{token}"
        if len(encoded.encode("utf-8")) > TELEGRAM_CALLBACK_DATA_MAX_BYTES:
            self._entries.pop(token, None)
            raise ValueError("namespace leaves no room for a callback token")
        return encoded

    def decode(self, data: str | None, namespace: str) -> str | None:
        """Resolve callback payload for namespace, including tokenized data."""
        if data is None:
            return None
        prefix = f"{namespace}:"
        if not data.startswith(prefix):
            return None
        payload = data[len(prefix) :]
        if not payload.startswith("~"):
            return payload

        token = payload[1:]
        entry = self._entries.get(token)
        if entry is None:
            return None
        if entry.expires_at <= self._clock():
            self._entries.pop(token, None)
            return None
        if entry.namespace != namespace:
            return None
        self._entries.move_to_end(token)
        return entry.payload

    def _prune_expired(self) -> None:
        now = self._clock()
        expired = [token for token, entry in self._entries.items() if entry.expires_at <= now]
        for token in expired:
            self._entries.pop(token, None)

    def _new_token(self) -> str:
        while True:
            token = secrets.token_urlsafe(9)
            if token not in self._entries:
                return token


callback_data_registry = CallbackDataRegistry()


def encode_callback_data(namespace: str, payload: str) -> str:
    return callback_data_registry.encode(namespace, payload)


def decode_callback_data(data: str | None, namespace: str) -> str | None:
    return callback_data_registry.decode(data, namespace)
