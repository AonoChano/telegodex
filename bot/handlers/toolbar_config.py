"""Toolbar TOML configuration support.

Loads a custom keyboard layout from ``~/.telegodex/toolbar.toml``
with fallback to the built-in default layout.
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger
from pydantic import BaseModel, Field

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]


class ToolbarAction(BaseModel):
    """A single button in the toolbar."""

    name: str
    label: str
    row: int = Field(default=0, ge=0)
    condition: str | None = Field(default=None)
    callback_data_template: str | None = Field(default=None)


class ToolbarLayout(BaseModel):
    """A row group of toolbar actions."""

    row: int = Field(default=0, ge=0)
    actions: list[ToolbarAction] = Field(default_factory=list)


class ToolbarConfig(BaseModel):
    """Complete toolbar configuration."""

    actions: list[ToolbarAction] = Field(default_factory=list)

    def rows(self) -> dict[int, list[ToolbarAction]]:
        """Group actions by row index."""
        result: dict[int, list[ToolbarAction]] = {}
        for action in self.actions:
            result.setdefault(action.row, []).append(action)
        return result


def _default_config() -> ToolbarConfig:
    """Return the built-in default toolbar configuration."""
    actions = [
        ToolbarAction(name="ctrl_c", label="Ctrl-C", row=0),
        ToolbarAction(name="live", label="Live", row=0),
        ToolbarAction(name="last_reply", label="Last Reply", row=0),
        ToolbarAction(name="esc", label="Esc", row=1, condition="codex_active"),
        ToolbarAction(name="tab", label="Tab", row=1, condition="codex_active"),
        ToolbarAction(name="mode", label="Mode", row=1, condition="codex_active"),
        ToolbarAction(name="up", label="Up", row=2, condition="active"),
        ToolbarAction(name="enter", label="Enter", row=2, condition="active"),
        ToolbarAction(name="down", label="Down", row=2, condition="active"),
        ToolbarAction(name="close", label="Close Toolbar", row=3),
    ]
    return ToolbarConfig(actions=actions)


def _load_toml_config(path: Path) -> ToolbarConfig | None:
    """Parse a TOML file into a ``ToolbarConfig``."""
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except Exception as exc:
        logger.warning(f"Toolbar: failed to parse TOML config at {path}: {exc}")
        return None

    actions: list[ToolbarAction] = []
    raw_actions = data.get("actions", [])
    if not isinstance(raw_actions, list):
        logger.warning("Toolbar: 'actions' must be a list in TOML config")
        return None

    for idx, raw in enumerate(raw_actions):
        if not isinstance(raw, dict):
            logger.warning(f"Toolbar: action {idx} is not a dict, skipping")
            continue
        try:
            actions.append(ToolbarAction(**raw))
        except Exception as exc:
            logger.warning(f"Toolbar: invalid action at index {idx}: {exc}")

    return ToolbarConfig(actions=actions)


def load_toolbar_config() -> ToolbarConfig:
    """Load toolbar configuration from file or return defaults.

    Searches ``~/.telegodex/toolbar.toml`` (user home directory).
    Falls back to the built-in default layout if the file is missing
    or cannot be parsed.
    """
    home = Path.home()
    config_path = home / ".telegodex" / "toolbar.toml"

    if config_path.exists():
        config = _load_toml_config(config_path)
        if config is not None:
            logger.info(f"Toolbar: loaded custom layout from {config_path}")
            return config

    logger.debug("Toolbar: using default layout")
    return _default_config()
