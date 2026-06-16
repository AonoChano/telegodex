"""Message hook registry for conditional system prompt injection."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from ai.base import Message, MessageRole
from core.session import SessionKey


Hook = Callable[[SessionKey, list[Message]], Awaitable[list[Message]]]


@dataclass
class HookEntry:
    name: str
    hook: Hook
    condition: Callable[[SessionKey, list[Message]], bool] | None = None


class MessageHookRegistry:
    """Conditionally inject system prompts and other message transformations.

    Hooks are applied in registration order.  Each hook receives the current
    :class:`core.session.SessionKey` and the message list, and returns a
    (possibly modified) message list.
    """

    def __init__(self) -> None:
        self._hooks: list[HookEntry] = []

    def register(
        self,
        name: str,
        hook: Hook,
        condition: Callable[[SessionKey, list[Message]], bool] | None = None,
    ) -> None:
        """Register a message hook."""
        self._hooks.append(HookEntry(name=name, hook=hook, condition=condition))

    def unregister(self, name: str) -> None:
        """Remove a hook by name."""
        self._hooks = [h for h in self._hooks if h.name != name]

    async def apply(
        self, key: SessionKey, messages: list[Message]
    ) -> list[Message]:
        """Apply all matching hooks to the message list."""
        result = list(messages)
        for entry in self._hooks:
            if entry.condition is None or entry.condition(key, result):
                result = await entry.hook(key, result)
        return result

    def add_memory_reminder(self, reminder_text: str | None = None) -> None:
        """Add a default memory-reminder hook.

        Injects a system message at the front of the list when no system
        message is already present.
        """
        text = reminder_text or "Remember previous context and user preferences."

        async def _hook(
            _key: SessionKey, messages: list[Message]
        ) -> list[Message]:
            if messages and messages[0].role == MessageRole.SYSTEM:
                return messages
            return [Message(role=MessageRole.SYSTEM, content=text)] + messages

        self.register("memory_reminder", _hook)

    def clear(self) -> None:
        """Remove all hooks."""
        self._hooks.clear()
