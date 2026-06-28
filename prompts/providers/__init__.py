"""Provider-specific behavior prompts."""

from pathlib import Path

DEFAULT_BEHAVIOUR_PROMPT: str = Path(__file__).parent.joinpath("default.md").read_text(encoding="utf-8")
DEEPSEEK_BEHAVIOUR_PROMPT: str = Path(__file__).parent.joinpath("deepseek.md").read_text(encoding="utf-8")

__all__ = ["DEFAULT_BEHAVIOUR_PROMPT", "DEEPSEEK_BEHAVIOUR_PROMPT"]
