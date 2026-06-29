"""Provider configuration loader for ``provider.toml``.

This module is the single entry point for resolving AI provider
configuration. It reads a TOML file, validates structure, resolves
secrets from environment variables, and returns ready-to-use
``ProviderConfig`` / ``GlobalConfig`` value objects.

Design goals (mirrors ``docs/CodexSourceCode/codex-rs/model-provider-info``):

* One generic ``OpenAICompatibleProvider`` covers any OpenAI-compatible
  endpoint. Native SDKs (``openai`` / ``anthropic``) are only used when
  ``transport`` declares them.
* Secrets NEVER appear in TOML. They are resolved at runtime from
  environment variables referenced by ``api_key_env`` /
  ``secret_key_env`` / ``base_url_env``.
* ``available_providers`` is a single filter list — a provider block
  exists in TOML but is NOT instantiated unless its name is listed.
* Reserved sections (``[secrets]`` / ``[routing]`` / ``[policy]``) are
  parsed but silently ignored in Phase 1. They are reserved for future
  features (secret manager integration, capability-based routing,
  per-provider policy overrides).

Resolution precedence (highest first):
    1. ``api_key_literal`` (literal non-secret, e.g. for local servers)
    2. ``api_key_env`` (env var name → ``os.environ`` value)
    3. provider skipped with a warning log

For ``base_url``:
    1. ``base_url`` (literal)
    2. ``base_url_env`` (env var name → ``os.environ`` value)
    3. ``None`` (provider SDK uses its own default)

Public API:
    ProviderConfig, GlobalConfig, RESERVED_PROVIDER_IDS, load_provider_toml
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

# Python 3.11+ ships ``tomllib`` in the stdlib. Older Python (3.10) uses the
# ``tomli`` backport, which exposes the same ``load``/``loads`` API. The
# project officially requires Python 3.11+ (see ``pyproject.toml``), but we
# keep this fallback so local development on 3.10 still works.
try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised only on 3.10
    import tomli as tomllib  # type: ignore[no-redef]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Provider IDs that are reserved for built-in transports.
#:
#: ``openai`` and ``anthropic`` are reserved because they map to native SDK
#: providers (``OpenAIProvider`` / ``AnthropicProvider``). User-defined
#: provider blocks may use these IDs ONLY when ``transport`` matches the
#: ID (i.e. ``[providers.openai]`` with ``transport = "openai"`` configures
#: the built-in OpenAI transport; using ``transport = "openai_compatible"``
#: with the same name would be a confusing override and is rejected).
RESERVED_PROVIDER_IDS: frozenset[str] = frozenset({"openai", "anthropic"})

#: Valid transport strings.
_VALID_TRANSPORTS: frozenset[str] = frozenset({"openai", "anthropic", "openai_compatible"})

#: Default redaction list for sensitive field names in logs.
_DEFAULT_REDACT_FIELDS: list[str] = [
    "api_key",
    "api_key_env",
    "secret_key_env",
    "authorization",
    "cookie",
    "set-cookie",
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ProviderConfig:
    """Resolved configuration for a single provider entry.

    ``api_key_literal`` / ``api_key_env`` / ``base_url`` / ``base_url_env``
    are stored as-is; resolution happens in :meth:`resolve_api_key` and
    :meth:`resolve_base_url` so callers can introspect the unresolved
    config (useful for tests and ``--check-config`` output).
    """

    name: str
    transport: str  # "openai" | "anthropic" | "openai_compatible"
    default_model: str
    models: list[str]

    base_url: str | None = None
    base_url_env: str | None = None
    api_key_env: str | None = None
    api_key_literal: str | None = None
    secret_key_env: str | None = None  # Phase 2 reserved; not consumed in Phase 1

    headers: dict[str, str] | None = None
    query: dict[str, str] | None = None

    # Capability flags. Defaults follow the conservative policy in the spec:
    # streaming is widely supported, everything else defaults to off.
    supports_stream: bool = True
    supports_tools: bool = False
    supports_vision: bool = False
    supports_json_schema: bool = False
    supports_audio: bool = False
    supports_files: bool = False

    def resolve_api_key(self) -> str | None:
        """Resolve the API key. Returns ``None`` if env var is missing.

        Precedence: ``api_key_literal`` > ``api_key_env`` > ``None``.
        """
        if self.api_key_literal is not None:
            return self.api_key_literal
        if self.api_key_env:
            value = os.environ.get(self.api_key_env)
            if not value:
                return None
            return value
        return None

    def resolve_base_url(self) -> str | None:
        """Resolve the base URL.

        Precedence: ``base_url`` (literal) > ``base_url_env`` > ``None``.
        """
        if self.base_url:
            return self.base_url
        if self.base_url_env:
            return os.environ.get(self.base_url_env)
        return None


@dataclass
class GlobalConfig:
    """Global settings parsed from the ``[global]`` section.

    These values replace the legacy ``Settings.default_ai_provider`` /
    ``default_model`` / ``max_tokens`` / ``temperature`` fields that used
    to live in ``.env``.
    """

    default_provider: str = "openai"
    default_model: str = ""
    temperature: float = 0.7
    max_output_tokens: int = 4096
    streaming: bool = True

    #: Filter list — only providers whose name appears here are instantiated.
    available_providers: list[str] = field(default_factory=list)

    #: Phase 2 reserved — stored but not consumed in Phase 1.
    fallback_chain: list[str] = field(default_factory=list)

    #: Field names that loguru sinks should redact.
    redact_sensitive_fields: list[str] = field(
        default_factory=lambda: list(_DEFAULT_REDACT_FIELDS)
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def load_provider_toml(path: str | Path) -> tuple[list[ProviderConfig], GlobalConfig]:
    """Load and validate ``provider.toml``.

    Args:
        path: Path to the TOML file (e.g. ``"provider.toml"``).

    Returns:
        ``(provider_configs, global_config)`` — the list of provider
        configs (already filtered by ``available_providers``) and the
        global settings.

    Raises:
        FileNotFoundError: if the file does not exist. The caller should
            surface the error to the user with a pointer to
            ``provider.toml.example``.
        ValueError: if a reserved provider ID is used with a mismatched
            transport (see :data:`RESERVED_PROVIDER_IDS`).
    """
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"provider.toml is required; see provider.toml.example "
            f"(expected at: {config_path.resolve()})"
        )

    with config_path.open("rb") as f:
        data: dict[str, Any] = tomllib.load(f)

    global_config = _parse_global_config(data.get("global", {}))
    provider_configs = _parse_providers(data.get("providers", {}), global_config.available_providers)

    logger.info(
        f"Loaded provider.toml: {len(provider_configs)} provider(s) activated, "
        f"{len(global_config.available_providers)} listed in available_providers"
    )

    return provider_configs, global_config


# ---------------------------------------------------------------------------
# Internal parsers
# ---------------------------------------------------------------------------


def _parse_global_config(raw: dict[str, Any]) -> GlobalConfig:
    """Parse the ``[global]`` section.

    Accepts both ``default_provider`` / ``default_model`` (spec names)
    and ``current_provider`` / ``current_model`` (legacy example file
    names) as aliases — the spec names take precedence.
    """
    default_provider = raw.get("default_provider") or raw.get("current_provider") or "openai"
    default_model = raw.get("default_model") or raw.get("current_model") or ""

    available = raw.get("available_providers")
    if available is None:
        available = []
    elif not isinstance(available, list):
        logger.warning("[global].available_providers is not a list; ignoring")
        available = []

    fallback = raw.get("fallback_chain", [])
    if not isinstance(fallback, list):
        logger.warning("[global].fallback_chain is not a list; ignoring")
        fallback = []

    redact = raw.get("redact_sensitive_fields", _DEFAULT_REDACT_FIELDS)
    if not isinstance(redact, list):
        logger.warning("[global].redact_sensitive_fields is not a list; using defaults")
        redact = list(_DEFAULT_REDACT_FIELDS)

    return GlobalConfig(
        default_provider=str(default_provider),
        default_model=str(default_model),
        temperature=float(raw.get("temperature", 0.7)),
        max_output_tokens=int(raw.get("max_output_tokens", 4096)),
        streaming=bool(raw.get("streaming", True)),
        available_providers=[str(p) for p in available],
        fallback_chain=[str(p) for p in fallback],
        redact_sensitive_fields=[str(f) for f in redact],
    )


def _parse_providers(
    raw_providers: dict[str, Any], available_providers: list[str]
) -> list[ProviderConfig]:
    """Parse the ``[providers.*]`` section.

    Filters by ``available_providers``: configured but unlisted providers
    are NOT instantiated (their blocks stay in TOML for future
    re-enabling). An empty list activates NOTHING — the user must
    explicitly list every provider they want instantiated.
    """
    configs: list[ProviderConfig] = []

    for name, raw in raw_providers.items():
        if not isinstance(raw, dict):
            logger.warning(f"Skipping provider '{name}': section is not a table")
            continue

        # Mandatory filter: even an empty available_providers list activates
        # nothing. There is no "no filter" mode — every provider must be
        # explicitly listed.
        if name not in available_providers:
            logger.debug(
                f"Provider '{name}' is configured but not in [global].available_providers; "
                f"skipping instantiation"
            )
            continue

        configs.append(_parse_single_provider(name, raw))

    return configs


def _parse_single_provider(name: str, raw: dict[str, Any]) -> ProviderConfig:
    """Parse a single ``[providers.<name>]`` block."""
    transport = str(raw.get("transport", "openai_compatible"))
    if transport not in _VALID_TRANSPORTS:
        logger.warning(
            f"Provider '{name}': unknown transport '{transport}'; defaulting to 'openai_compatible'"
        )
        transport = "openai_compatible"

    # Reserved ID check: openai/anthropic names must use their matching transport.
    # This prevents users from hijacking the built-in provider names with a
    # different transport (e.g. ``[providers.openai]`` with
    # ``transport = "openai_compatible"`` would shadow the native SDK).
    # Using ``[providers.openai]`` with ``transport = "openai"`` IS allowed
    # — it configures the built-in OpenAI transport (base_url, api_key_env,
    # default_model, etc.).
    if name in RESERVED_PROVIDER_IDS and transport != name:
        raise ValueError(
            f"'{name}' is a reserved provider ID for the built-in '{name}' transport. "
            f"It cannot be used with transport='{transport}'. "
            f"Rename your custom provider (e.g., '{name}-custom')."
        )

    models = list(raw.get("models", []))
    if not isinstance(models, list):
        logger.warning(f"Provider '{name}': 'models' is not a list; treating as empty")
        models = []

    models = [str(m) for m in models]
    default_model = str(raw.get("default_model") or (models[0] if models else ""))

    headers = raw.get("headers")
    query = raw.get("query")

    return ProviderConfig(
        name=name,
        transport=transport,
        base_url=str(raw["base_url"]) if raw.get("base_url") else None,
        base_url_env=str(raw["base_url_env"]) if raw.get("base_url_env") else None,
        api_key_env=str(raw["api_key_env"]) if raw.get("api_key_env") else None,
        api_key_literal=str(raw["api_key_literal"]) if raw.get("api_key_literal") else None,
        secret_key_env=str(raw["secret_key_env"]) if raw.get("secret_key_env") else None,
        default_model=default_model,
        models=models,
        headers=dict(headers) if isinstance(headers, dict) else None,
        query=dict(query) if isinstance(query, dict) else None,
        supports_stream=bool(raw.get("supports_stream", True)),
        supports_tools=bool(raw.get("supports_tools", False)),
        supports_vision=bool(raw.get("supports_vision", False)),
        supports_json_schema=bool(raw.get("supports_json_schema", False)),
        supports_audio=bool(raw.get("supports_audio", False)),
        supports_files=bool(raw.get("supports_files", False)),
    )
