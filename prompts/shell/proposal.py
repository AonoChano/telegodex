from pathlib import Path

SHELL_PROPOSAL_PROMPT: str = Path(__file__).with_suffix(".md").read_text(encoding="utf-8")