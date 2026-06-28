from pathlib import Path

TELEGODEX_CAPABILITY_CHAT_PROMPT: str = Path(__file__).with_suffix(".md").read_text(encoding="utf-8")