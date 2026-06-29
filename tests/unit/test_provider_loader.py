"""Unit tests for ``config.provider_loader``.

Covers TOML parsing, secret resolution precedence, ``available_providers``
filtering, reserved ID validation, capability flag defaults/overrides, and
the silent-ignore behavior for Phase 2 reserved sections.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from config.provider_loader import (
    RESERVED_PROVIDER_IDS,
    GlobalConfig,
    ProviderConfig,
    load_provider_toml,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_toml(tmp_path: Path, content: str, name: str = "provider.toml") -> Path:
    """Write *content* to a temp TOML file and return its path."""
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


_MINIMAL_TOML = """\
[global]
default_provider = "openai"
default_model = "gpt-4o"
available_providers = ["openai"]

[providers.openai]
transport = "openai"
api_key_env = "OPENAI_API_KEY"
default_model = "gpt-4o"
models = ["gpt-4o", "gpt-4o-mini"]
"""


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_parse_valid_toml_returns_configs_and_global(tmp_path: Path) -> None:
    path = _write_toml(tmp_path, _MINIMAL_TOML)

    configs, global_config = load_provider_toml(path)

    assert isinstance(global_config, GlobalConfig)
    assert global_config.default_provider == "openai"
    assert global_config.default_model == "gpt-4o"
    assert global_config.available_providers == ["openai"]

    assert len(configs) == 1
    openai = configs[0]
    assert isinstance(openai, ProviderConfig)
    assert openai.name == "openai"
    assert openai.transport == "openai"
    assert openai.default_model == "gpt-4o"
    assert openai.models == ["gpt-4o", "gpt-4o-mini"]
    assert openai.api_key_env == "OPENAI_API_KEY"


def test_global_config_defaults_when_fields_omitted(tmp_path: Path) -> None:
    toml = """\
[global]
available_providers = []

[providers.openai]
transport = "openai"
"""
    path = _write_toml(tmp_path, toml)
    _, global_config = load_provider_toml(path)

    assert global_config.default_provider == "openai"
    assert global_config.default_model == ""
    assert global_config.temperature == 0.7
    assert global_config.max_output_tokens == 4096
    assert global_config.streaming is True
    assert global_config.fallback_chain == []
    assert "api_key" in global_config.redact_sensitive_fields


def test_legacy_current_provider_alias_accepted(tmp_path: Path) -> None:
    toml = """\
[global]
current_provider = "anthropic"
current_model = "claude-sonnet-4-6"
available_providers = ["anthropic"]

[providers.anthropic]
transport = "anthropic"
"""
    path = _write_toml(tmp_path, toml)
    _, global_config = load_provider_toml(path)

    assert global_config.default_provider == "anthropic"
    assert global_config.default_model == "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# Secret / base_url resolution
# ---------------------------------------------------------------------------


def test_api_key_env_resolved_from_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    path = _write_toml(tmp_path, _MINIMAL_TOML)

    configs, _ = load_provider_toml(path)
    assert configs[0].resolve_api_key() == "sk-test-123"


def test_api_key_literal_takes_precedence_over_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")
    toml = """\
[global]
available_providers = ["local"]

[providers.local]
transport = "openai_compatible"
api_key_literal = "ollama"
api_key_env = "OPENAI_API_KEY"
base_url = "http://localhost:11434/v1"
default_model = "llama3"
"""
    path = _write_toml(tmp_path, toml)

    configs, _ = load_provider_toml(path)
    assert configs[0].resolve_api_key() == "ollama"


def test_api_key_returns_none_when_env_var_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    path = _write_toml(tmp_path, _MINIMAL_TOML)

    configs, _ = load_provider_toml(path)
    # Loader returns the config; resolution yields None — the router is
    # responsible for the actual "skip with warning" step at instantiation.
    assert configs[0].resolve_api_key() is None


def test_base_url_env_resolved_from_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_BASE_URL", "https://proxy.example.com/v1")
    toml = """\
[global]
available_providers = ["openai"]

[providers.openai]
transport = "openai"
api_key_env = "OPENAI_API_KEY"
base_url_env = "OPENAI_BASE_URL"
default_model = "gpt-4o"
"""
    path = _write_toml(tmp_path, toml)

    configs, _ = load_provider_toml(path)
    assert configs[0].resolve_base_url() == "https://proxy.example.com/v1"


def test_literal_base_url_takes_precedence_over_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_BASE_URL", "https://from-env.example.com/v1")
    toml = """\
[global]
available_providers = ["openai"]

[providers.openai]
transport = "openai"
api_key_env = "OPENAI_API_KEY"
base_url = "https://literal.example.com/v1"
base_url_env = "OPENAI_BASE_URL"
default_model = "gpt-4o"
"""
    path = _write_toml(tmp_path, toml)

    configs, _ = load_provider_toml(path)
    assert configs[0].resolve_base_url() == "https://literal.example.com/v1"


def test_resolve_base_url_returns_none_when_unspecified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    path = _write_toml(tmp_path, _MINIMAL_TOML)

    configs, _ = load_provider_toml(path)
    assert configs[0].resolve_base_url() is None


# ---------------------------------------------------------------------------
# available_providers filter
# ---------------------------------------------------------------------------


def test_unlisted_provider_is_not_instantiated(tmp_path: Path) -> None:
    toml = """\
[global]
available_providers = ["openai"]

[providers.openai]
transport = "openai"
api_key_env = "OPENAI_API_KEY"

[providers.anthropic]
transport = "anthropic"
api_key_env = "ANTHROPIC_API_KEY"
"""
    path = _write_toml(tmp_path, toml)

    configs, _ = load_provider_toml(path)
    names = [c.name for c in configs]
    assert names == ["openai"]
    assert "anthropic" not in names


def test_empty_available_providers_keeps_nothing(tmp_path: Path) -> None:
    toml = """\
[global]
available_providers = []

[providers.openai]
transport = "openai"
"""
    path = _write_toml(tmp_path, toml)

    configs, _ = load_provider_toml(path)
    assert configs == []


# ---------------------------------------------------------------------------
# Missing file
# ---------------------------------------------------------------------------


def test_missing_provider_toml_raises_filenotfound(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError) as exc_info:
        load_provider_toml(tmp_path / "nonexistent.toml")

    message = str(exc_info.value)
    assert "provider.toml" in message
    assert "provider.toml.example" in message


# ---------------------------------------------------------------------------
# Reserved IDs
# ---------------------------------------------------------------------------


def test_reserved_id_with_mismatched_transport_rejected(tmp_path: Path) -> None:
    toml = """\
[global]
available_providers = ["openai"]

[providers.openai]
transport = "openai_compatible"
api_key_env = "OPENAI_API_KEY"
default_model = "gpt-4o"
"""
    path = _write_toml(tmp_path, toml)

    with pytest.raises(ValueError) as exc_info:
        load_provider_toml(path)

    message = str(exc_info.value)
    assert "openai" in message
    assert "reserved" in message.lower()


def test_anthropic_reserved_id_with_wrong_transport_rejected(tmp_path: Path) -> None:
    toml = """\
[global]
available_providers = ["anthropic"]

[providers.anthropic]
transport = "openai_compatible"
api_key_env = "ANTHROPIC_API_KEY"
"""
    path = _write_toml(tmp_path, toml)

    with pytest.raises(ValueError, match="reserved"):
        load_provider_toml(path)


def test_reserved_id_with_matching_transport_allowed(tmp_path: Path) -> None:
    """``[providers.openai]`` with ``transport = "openai"`` configures the
    built-in OpenAI transport and MUST be allowed."""
    path = _write_toml(tmp_path, _MINIMAL_TOML)

    configs, _ = load_provider_toml(path)
    assert len(configs) == 1
    assert configs[0].name == "openai"
    assert configs[0].transport == "openai"


def test_reserved_provider_ids_constant_is_frozen() -> None:
    assert "openai" in RESERVED_PROVIDER_IDS
    assert "anthropic" in RESERVED_PROVIDER_IDS


# ---------------------------------------------------------------------------
# Capability flags
# ---------------------------------------------------------------------------


def test_capability_flag_defaults_when_omitted(tmp_path: Path) -> None:
    toml = """\
[global]
available_providers = ["openai"]

[providers.openai]
transport = "openai"
api_key_env = "OPENAI_API_KEY"
default_model = "gpt-4o"
"""
    path = _write_toml(tmp_path, toml)

    configs, _ = load_provider_toml(path)
    c = configs[0]
    assert c.supports_stream is True
    assert c.supports_tools is False
    assert c.supports_vision is False
    assert c.supports_json_schema is False
    assert c.supports_audio is False
    assert c.supports_files is False


def test_capability_flag_user_values_override_defaults(tmp_path: Path) -> None:
    toml = """\
[global]
available_providers = ["openai"]

[providers.openai]
transport = "openai"
api_key_env = "OPENAI_API_KEY"
default_model = "gpt-4o"
supports_stream = false
supports_tools = true
supports_vision = true
supports_json_schema = true
supports_audio = true
supports_files = true
"""
    path = _write_toml(tmp_path, toml)

    configs, _ = load_provider_toml(path)
    c = configs[0]
    assert c.supports_stream is False
    assert c.supports_tools is True
    assert c.supports_vision is True
    assert c.supports_json_schema is True
    assert c.supports_audio is True
    assert c.supports_files is True


# ---------------------------------------------------------------------------
# Reserved sections (Phase 2)
# ---------------------------------------------------------------------------


def test_reserved_sections_silently_ignored(tmp_path: Path) -> None:
    toml = """\
[global]
available_providers = ["openai"]

[providers.openai]
transport = "openai"
api_key_env = "OPENAI_API_KEY"
default_model = "gpt-4o"

[secrets]
backend = "vault"
path = "secret/telegodex"

[routing]
strategy = "capability"
fallback_chain = ["openai", "anthropic"]

[policy]
redact_sensitive_fields = true
audit_log = true
"""
    path = _write_toml(tmp_path, toml)

    configs, global_config = load_provider_toml(path)

    assert len(configs) == 1
    # fallback_chain under [global] is honored, but [routing].fallback_chain
    # must NOT override the [global] one (loader ignores [routing]).
    assert global_config.fallback_chain == []


# ---------------------------------------------------------------------------
# Misc: model list / default_model fallback
# ---------------------------------------------------------------------------


def test_default_model_falls_back_to_first_model(tmp_path: Path) -> None:
    toml = """\
[global]
available_providers = ["custom"]

[providers.custom]
transport = "openai_compatible"
api_key_env = "CUSTOM_API_KEY"
base_url = "https://api.example.com/v1"
models = ["my-model-v1", "my-model-v2"]
"""
    path = _write_toml(tmp_path, toml)

    configs, _ = load_provider_toml(path)
    assert configs[0].default_model == "my-model-v1"
    assert configs[0].models == ["my-model-v1", "my-model-v2"]


def test_unknown_transport_defaults_to_openai_compatible(tmp_path: Path) -> None:
    toml = """\
[global]
available_providers = ["custom"]

[providers.custom]
transport = "bogus_transport"
api_key_env = "CUSTOM_API_KEY"
default_model = "m"
"""
    path = _write_toml(tmp_path, toml)

    configs, _ = load_provider_toml(path)
    assert configs[0].transport == "openai_compatible"


def test_headers_and_query_parsed_when_present(tmp_path: Path) -> None:
    toml = """\
[global]
available_providers = ["custom"]

[providers.custom]
transport = "openai_compatible"
api_key_env = "CUSTOM_API_KEY"
base_url = "https://api.example.com/v1"
default_model = "m"
headers = { X-Custom-Header = "value" }
query = { version = "v1" }
"""
    path = _write_toml(tmp_path, toml)

    configs, _ = load_provider_toml(path)
    assert configs[0].headers == {"X-Custom-Header": "value"}
    assert configs[0].query == {"version": "v1"}
