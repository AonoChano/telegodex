"""Base prompts for identity and formatting."""

from pathlib import Path

IDENTITY_PROMPT: str = Path(__file__).parent.joinpath("identity.md").read_text(encoding="utf-8")
FORMATTING_PROMPT: str = Path(__file__).parent.joinpath("formatting.md").read_text(encoding="utf-8")

__all__ = ["IDENTITY_PROMPT", "FORMATTING_PROMPT"]
