"""Directive parser for ``@codex``, ``@claude``, ``@session``, etc."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Directive:
    """A parsed directive."""

    name: str
    target: str | None = None
    rest: str = ""


class DirectiveParser:
    """Parse directives like ``@codex``, ``@claude``, ``@session`` from message text.

    Directives appear at the start of a message and route the message to a
    specific subsystem or session.
    """

    _DIRECTIVE_PATTERN = re.compile(r"^@(\w+)\s*(.*)$", re.DOTALL)

    def __init__(self) -> None:
        self._known: set[str] = {"codex", "claude", "session", "ai", "shell"}

    def parse(self, text: str) -> Directive | None:
        """Parse a directive from the start of text.

        Returns:
            :class:`Directive` if matched, ``None`` otherwise.
        """
        stripped = text.strip()
        match = self._DIRECTIVE_PATTERN.match(stripped)
        if not match:
            return None

        name = match.group(1).lower()
        rest = match.group(2).strip()

        if name not in self._known:
            return None

        parts = rest.split(None, 1)
        target = parts[0] if parts else None
        rest_text = parts[1] if len(parts) > 1 else ""

        return Directive(name=name, target=target, rest=rest_text)

    def is_directive(self, text: str) -> bool:
        """Check if text starts with a known directive."""
        return self.parse(text) is not None

    def register_directive(self, name: str) -> None:
        """Register a new known directive name."""
        self._known.add(name.lower())

    def unregister_directive(self, name: str) -> None:
        """Remove a known directive name."""
        self._known.discard(name.lower())
