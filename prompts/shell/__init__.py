"""Shell command proposal and result prompts."""

from pathlib import Path
from prompts._utils import load_prompt

_base_dir = Path(__file__).parent

SHELL_PROPOSAL_PROMPT: str = load_prompt("proposal", _base_dir)
SHELL_TOOL_RESULT_TEMPLATE: str = load_prompt("tool_result", _base_dir)

__all__ = ["SHELL_PROPOSAL_PROMPT", "SHELL_TOOL_RESULT_TEMPLATE"]
