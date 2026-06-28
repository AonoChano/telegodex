from pathlib import Path

SHELL_TOOL_RESULT_TEMPLATE: str = Path(__file__).with_suffix(".md").read_text(encoding="utf-8")