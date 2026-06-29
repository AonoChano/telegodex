#!/usr/bin/env python3
"""
Telegodex startup script.

Usage:
    python run.py
    python run.py --check-config
"""

import asyncio
import re
import sys
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).parent))

from config import settings


def _project_version() -> str:
    """Read the package version from pyproject.toml."""
    pyproject = Path(__file__).parent / "pyproject.toml"
    in_project = False
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == "[project]":
            in_project = True
            continue
        if in_project and stripped.startswith("["):
            break
        if in_project and stripped.startswith("version"):
            match = re.match(r'version\s*=\s*"([^"]+)"', stripped)
            if match:
                return match.group(1)
    return "0.0.0"


def check_configuration() -> bool:
    """Validate required local configuration before starting the bot."""
    logger.info("Preflight: checking local configuration...")
    errors: list[str] = []

    if not settings.telegram_bot_token:
        errors.append("TELEGRAM_BOT_TOKEN is not configured")
    else:
        logger.info("Preflight: Telegram Bot Token is configured")

    # Provider configuration is loaded from provider.toml (single source of truth).
    # The .env file only stores the API key env vars referenced by api_key_env.
    from config.provider_loader import load_provider_toml

    try:
        provider_configs, global_config = load_provider_toml("provider.toml")
    except FileNotFoundError as e:
        errors.append(str(e))
        provider_configs = []
        global_config = None
    except Exception as e:
        errors.append(f"Failed to load provider.toml: {e}")
        provider_configs = []
        global_config = None

    if global_config is not None:
        listed = global_config.available_providers
        loaded = [c.name for c in provider_configs]
        if not listed:
            errors.append("[global].available_providers is empty in provider.toml")
        else:
            logger.info(
                f"Preflight: provider.toml lists {len(listed)} provider(s) in "
                f"available_providers: {', '.join(listed)}"
            )
        if loaded:
            logger.info(f"Preflight: parsed provider blocks: {', '.join(loaded)}")
        if global_config.default_provider and global_config.default_provider not in listed:
            errors.append(
                f"default_provider '{global_config.default_provider}' is not in "
                f"available_providers {listed}"
            )

    logger.info(f"Preflight: database URL: {settings.database_url}")

    if settings.admin_ids:
        logger.info(f"Preflight: admin user IDs: {settings.admin_ids}")
    else:
        logger.warning("Preflight: no admin user IDs configured")

    if errors:
        logger.error("Preflight: configuration check failed:")
        for error in errors:
            logger.error(f"- {error}")
        return False

    logger.success("Preflight: configuration check passed")
    return True


def _terminal_link(text: str, url: str) -> str:
    """Return an OSC 8 terminal hyperlink."""
    return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"


def print_banner() -> None:
    """Print the startup banner."""
    blue = "\033[38;2;34;158;217m"
    white = "\033[97m"
    reset = "\033[0m"
    repo_url = "https://github.com/AonoChano/telegodex"
    repo_label = "github.com/AonoChano/telegodex"
    repo_link = _terminal_link(repo_label, repo_url)
    version = _project_version()
    logo_lines = [
        "   ████████╗███████╗██╗     ███████╗ ██████╗  ██████╗ ██████╗ ███████╗██╗  ██╗   ",
        "   ╚══██╔══╝██╔════╝██║     ██╔════╝██╔════╝ ██╔═══██╗██╔══██╗██╔════╝╚██╗██╔╝   ",
        "      ██║   █████╗  ██║     █████╗  ██║  ███╗██║   ██║██║  ██║█████╗   ╚███╔╝    ",
        "      ██║   ██╔══╝  ██║     ██╔══╝  ██║   ██║██║   ██║██║  ██║██╔══╝   ██╔██╗    ",
        "      ██║   ███████╗███████╗███████╗╚██████╔╝╚██████╔╝██████╔╝███████╗██╔╝ ██╗   ",
        "      ╚═╝   ╚══════╝╚══════╝╚══════╝ ╚═════╝  ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝   ",
    ]
    tagline = "       AI Workbench Telegram Bot   |   Codex, ClaudeCode, and more"
    repo_line = f"  {repo_label}                  v{version}"
    ansi_pattern = re.compile(r"\033\]8;;.*?\033\\|\033\]8;;\033\\|\033\[[0-9;]*m")

    def visible_len(content: str) -> int:
        plain = content.replace(repo_link, repo_label)
        return len(ansi_pattern.sub("", plain))

    width = max(81, max(visible_len(line) for line in logo_lines + [tagline, repo_line]))

    def box_line(content: str = "") -> str:
        padding = " " * max(width - visible_len(content), 0)
        return f"{white}║{reset}{content}{padding}{white}║{reset}"

    print()
    print(f"{white}╔{'═' * width}╗{reset}")
    print(box_line())
    for index, line in enumerate(logo_lines):
        color = blue if index % 2 == 0 else white
        print(box_line(f"{color}{line}{reset}"))
    print(box_line())
    print(box_line(f"{white}{tagline}{reset}"))
    print(box_line())
    print(box_line(f"{blue}  {repo_link}{reset}{white}                  v{version}{reset}"))
    print(box_line())
    print(f"{white}╚{'═' * width}╝{reset}")
    print()

async def main() -> None:
    """Run the startup flow."""
    print_banner()

    if "--check-config" in sys.argv:
        check_configuration()
        return

    if not check_configuration():
        logger.error("Fix the configuration errors and restart Telegodex")
        sys.exit(1)

    logger.info("Preflight passed; entering runtime startup...")
    from main import main as bot_main

    await bot_main()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Telegodex stopped")
    except Exception as e:
        logger.exception(f"Startup failed: {e}")
        sys.exit(1)
