"""Internal prompt loading utilities."""

import re
from pathlib import Path

_YAML_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def load_prompt(name: str, base_dir: Path) -> str:
    """Load a .md prompt file and strip YAML frontmatter."""
    path = base_dir / f"{name}.md"
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    return _YAML_FRONTMATTER_RE.sub("", text).strip()
