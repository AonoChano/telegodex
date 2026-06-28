"""Telegodex capability prompts."""

from pathlib import Path
from prompts._utils import load_prompt

_base_dir = Path(__file__).parent

TELEGODEX_CAPABILITY_CHAT_PROMPT: str = load_prompt("capability_chat", _base_dir)
TELEGODEX_CAPABILITY_TOOL_TEMPLATE: str = load_prompt("capability_tool", _base_dir)

__all__ = ["TELEGODEX_CAPABILITY_CHAT_PROMPT", "TELEGODEX_CAPABILITY_TOOL_TEMPLATE"]
