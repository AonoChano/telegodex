"""Slash command registration and prefix matching."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any


CommandHandler = Callable[..., Awaitable[Any]]


@dataclass
class RegisteredCommand:
    """A registered command entry."""

    name: str
    handler: CommandHandler
    description: str = ""
    aliases: list[str] = field(default_factory=list)


class CommandRegistry:
    """Slash command registration and prefix matching.

    Supports commands like ``/codex``, ``/shell``, ``/status`` and their
    sub-command routing via the matched handler.
    """

    def __init__(self) -> None:
        self._commands: dict[str, RegisteredCommand] = {}
        self._prefix_pattern = re.compile(r"^/(\w+)(?:\s+|$)(.*)", re.DOTALL)

    def register(
        self,
        name: str,
        handler: CommandHandler,
        *,
        description: str = "",
        aliases: list[str] | None = None,
    ) -> None:
        """Register a command handler."""
        self._commands[name] = RegisteredCommand(
            name=name,
            handler=handler,
            description=description,
            aliases=aliases or [],
        )
        for alias in aliases or []:
            self._commands[alias] = RegisteredCommand(
                name=name,
                handler=handler,
                description=description,
                aliases=[],
            )

    def unregister(self, name: str) -> None:
        """Remove a command registration."""
        self._commands.pop(name, None)

    def match(self, text: str) -> tuple[str | None, str, CommandHandler | None]:
        """Match text against registered commands.

        Returns:
            ``(command_name, rest, handler)`` or ``(None, original_text, None)``.
        """
        match = self._prefix_pattern.match(text.strip())
        if not match:
            return None, text, None

        cmd_name = match.group(1).lower()
        rest = match.group(2).strip()

        reg = self._commands.get(cmd_name)
        if reg is None:
            return None, text, None

        return cmd_name, rest, reg.handler

    def list_commands(self) -> list[RegisteredCommand]:
        """Return all unique registered commands."""
        seen: set[str] = set()
        result: list[RegisteredCommand] = []
        for reg in self._commands.values():
            if reg.name not in seen:
                seen.add(reg.name)
                result.append(reg)
        return result
