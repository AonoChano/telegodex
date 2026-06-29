"""Application settings package.

This package replaces the legacy ``config.py`` module. Provider-specific
configuration (API keys, default model, temperature, etc.) now lives in
``provider.toml`` and is parsed by :mod:`config.provider_loader`. The
``Settings`` class here only retains non-provider runtime configuration
that is unsuited to TOML (Telegram token, database URL, rate limits,
Codex daemon toggles, etc.).

Public API:
    settings: the singleton ``Settings`` instance consumed by the app.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Non-provider runtime configuration loaded from ``.env``.

    Provider API keys, base URLs, default models, and capability flags
    are NOT read here anymore. They live in ``provider.toml`` and are
    resolved at runtime via ``api_key_env`` / ``base_url_env`` references.
    See ``config.provider_loader`` and ``provider.toml.example``.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # Ignore unknown env vars. After the provider TOML migration, the
        # user's ``.env`` may still contain ``DEFAULT_AI_PROVIDER``,
        # ``MAX_TOKENS``, ``TEMPERATURE``, ``CUSTOM_PROVIDERS_CONFIG``, and
        # the various ``*_API_KEY`` / ``*_SECRET_KEY`` vars — these are now
        # consumed by ``provider.toml`` via ``api_key_env`` references, not by
        # ``Settings`` itself. ``extra="ignore"`` lets the bot start during
        # the migration window without forcing the user to delete fields.
        extra="ignore",
    )

    # Telegram Bot
    telegram_bot_token: str

    # Database
    database_url: str = "sqlite+aiosqlite:///telegodex.db"

    # Redis (optional)
    redis_url: str | None = None

    # Security / rate limiting
    admin_user_ids: str = ""  # comma-separated Telegram User IDs
    max_requests_per_minute: int = 20
    max_context_messages: int = 50  # max messages kept per conversation

    # Codex CLI (optional — auto-detected from PATH if not set)
    codex_executable_path: str | None = None

    # Codex Daemon / Approval
    codex_daemon_auto_start: bool = True
    codex_daemon_max_restarts: int = 3
    codex_approval_timeout: int = 60

    @property
    def admin_ids(self) -> list[int]:
        """Parse the comma-separated admin user ID list into integers."""
        if not self.admin_user_ids:
            return []

        result: list[int] = []
        for uid in self.admin_user_ids.split(","):
            uid = uid.strip()
            if not uid or uid.startswith("#"):
                continue
            try:
                result.append(int(uid))
            except ValueError:
                from loguru import logger

                logger.warning(f"Ignoring invalid admin user ID: {uid}")

        return result


settings = Settings()
