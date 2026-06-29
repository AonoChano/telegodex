"""Provider-specific behavior prompts."""

from pathlib import Path

from prompts._utils import load_prompt

_base_dir = Path(__file__).parent

DEFAULT_BEHAVIOUR_PROMPT: str = load_prompt("default", _base_dir)
DEEPSEEK_BEHAVIOUR_PROMPT: str = load_prompt("deepseek", _base_dir)

__all__ = ["DEFAULT_BEHAVIOUR_PROMPT", "DEEPSEEK_BEHAVIOUR_PROMPT"]
