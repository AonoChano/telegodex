"""Unit tests for provider.toml hot reload."""

from __future__ import annotations

import pytest

from ai.router import AIRouter
from config.provider_hot_reload import ProviderTomlReloader
from config.provider_loader import load_provider_toml


def _write_provider_toml(path, model: str) -> None:
    path.write_text(
        f'''
[global]
default_provider = "local"
default_model = "{model}"
available_providers = ["local"]

[providers.local]
transport = "openai_compatible"
base_url = "http://localhost:11434/v1"
api_key_literal = "local-test"
default_model = "{model}"
models = ["{model}"]
'''.strip()
        + "\n",
        encoding="utf-8",
    )


@pytest.mark.asyncio
async def test_provider_toml_reloader_applies_model_changes(tmp_path) -> None:
    config_path = tmp_path / "provider.toml"
    _write_provider_toml(config_path, "model-a")
    provider_configs, global_config = load_provider_toml(config_path)
    router = AIRouter(provider_configs, global_config)
    reloader = ProviderTomlReloader(config_path, router, interval_seconds=0.01)

    assert router.default_model == "model-a"
    assert router.get_all_models() == {"local": ["model-a"]}

    _write_provider_toml(config_path, "model-b")

    assert await reloader.reload_once() is True
    assert router.default_model == "model-b"
    assert router.get_all_models() == {"local": ["model-b"]}


@pytest.mark.asyncio
async def test_provider_toml_reloader_preserves_router_on_invalid_toml(tmp_path) -> None:
    config_path = tmp_path / "provider.toml"
    _write_provider_toml(config_path, "model-a")
    provider_configs, global_config = load_provider_toml(config_path)
    router = AIRouter(provider_configs, global_config)
    reloader = ProviderTomlReloader(config_path, router, interval_seconds=0.01)

    config_path.write_text("[global\n", encoding="utf-8")

    assert await reloader.reload_once() is False
    assert router.default_model == "model-a"
    assert router.get_all_models() == {"local": ["model-a"]}