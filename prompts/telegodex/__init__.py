"""Telegodex capability prompts."""

from pathlib import Path

TELEGODEX_CAPABILITY_CHAT_PROMPT: str = Path(__file__).parent.joinpath("capability_chat.md").read_text(encoding="utf-8")
TELEGODEX_CAPABILITY_TOOL_TEMPLATE: str = Path(__file__).parent.joinpath("capability_tool.md").read_text(encoding="utf-8")

__all__ = ["TELEGODEX_CAPABILITY_CHAT_PROMPT", "TELEGODEX_CAPABILITY_TOOL_TEMPLATE"]
