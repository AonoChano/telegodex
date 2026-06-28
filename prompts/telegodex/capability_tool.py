from pathlib import Path

TELEGODEX_CAPABILITY_TOOL_TEMPLATE: str = Path(__file__).with_suffix(".md").read_text(encoding="utf-8")