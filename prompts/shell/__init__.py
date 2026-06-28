"""Shell command proposal and result prompts."""

from pathlib import Path

SHELL_PROPOSAL_PROMPT: str = Path(__file__).parent.joinpath("proposal.md").read_text(encoding="utf-8")
SHELL_TOOL_RESULT_TEMPLATE: str = Path(__file__).parent.joinpath("tool_result.md").read_text(encoding="utf-8")

__all__ = ["SHELL_PROPOSAL_PROMPT", "SHELL_TOOL_RESULT_TEMPLATE"]
