"""Fake Telegram client for testing aiogram-style Bot interactions.

Records every method call so tests can assert on behaviour without hitting
real Telegram servers.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


class FakeTelegramClient:
    """Drop-in recorder compatible with aiogram ``Bot`` method signatures.

    All awaited methods are stored in :attr:`calls` as
    ``(method_name, positional_args, keyword_args)``.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def _record(self, name: str) -> Callable[..., Awaitable[Any]]:
        async def _method(*args: Any, **kwargs: Any) -> Any:
            self.calls.append((name, args, kwargs))
            return {}

        return _method

    def __getattr__(self, name: str) -> Callable[..., Awaitable[Any]]:
        return self._record(name)

    # ------------------------------------------------------------------
    # Explicit signatures for common methods (IDE-friendly + assertions)
    # ------------------------------------------------------------------

    async def send_message(
        self,
        chat_id: int | str,
        text: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        self.calls.append(("send_message", (chat_id, text), kwargs))
        return {}

    async def edit_message_text(
        self,
        text: str,
        chat_id: int | str | None = None,
        message_id: int | None = None,
        inline_message_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        self.calls.append(("edit_message_text", (text,), kwargs))
        return {}

    async def send_photo(
        self,
        chat_id: int | str,
        photo: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        self.calls.append(("send_photo", (chat_id, photo), kwargs))
        return {}

    async def send_document(
        self,
        chat_id: int | str,
        document: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        self.calls.append(("send_document", (chat_id, document), kwargs))
        return {}

    async def send_chat_action(
        self,
        chat_id: int | str,
        action: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        self.calls.append(("send_chat_action", (chat_id, action), kwargs))
        return {}

    async def delete_message(
        self,
        chat_id: int | str,
        message_id: int,
        **kwargs: Any,
    ) -> dict[str, Any]:
        self.calls.append(("delete_message", (chat_id, message_id), kwargs))
        return {}

    # ------------------------------------------------------------------
    # Assertion helpers
    # ------------------------------------------------------------------

    def assert_called(self, method: str) -> None:
        assert any(c[0] == method for c in self.calls), (
            f"Method {method!r} was not called. Calls: {self.calls}"
        )

    def assert_not_called(self, method: str) -> None:
        assert not any(c[0] == method for c in self.calls), (
            f"Method {method!r} was called unexpectedly."
        )

    def get_calls(
        self, method: str
    ) -> list[tuple[str, tuple[Any, ...], dict[str, Any]]]:
        return [c for c in self.calls if c[0] == method]

    def call_count(self, method: str) -> int:
        return len(self.get_calls(method))

    def clear(self) -> None:
        self.calls.clear()
