"""Base prompts for identity and formatting."""

from pathlib import Path

from prompts._utils import load_prompt

_base_dir = Path(__file__).parent

IDENTITY_PROMPT: str = load_prompt("identity", _base_dir)
FORMATTING_PROMPT: str = load_prompt("formatting", _base_dir)

__all__ = ["IDENTITY_PROMPT", "FORMATTING_PROMPT"]