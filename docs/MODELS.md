---
title: Model Catalog
category: reference
last_updated: 2026-06-29
relevance: high
summary: Where Telegodex defines provider model names and how maintainers should verify them
related: [CUSTOM_PROVIDERS.md, USAGE.md]
---

# Model Catalog

Provider model names live in `provider.toml` (the `default_model` and `models` fields on each `[providers.<id>]` block). The Telegram settings UI reads the model list from each instantiated provider's `get_available_models()` method, which is populated from the TOML config.

## Where To Look

```text
provider.toml.example   # canonical, fully-commented template
config/provider_loader.py  # parses [providers.<id>] blocks into ProviderConfig
```

The legacy `ai/*_provider.py` files still contain hardcoded fallback model lists (used when a provider is instantiated outside the TOML path, e.g. in tests), but production configuration is TOML-driven:

```text
ai/openai_provider.py
ai/anthropic_provider.py
ai/google_provider.py
ai/deepseek_provider.py
ai/china_providers.py
ai/openai_compatible_provider.py
```

## Transports, Not Built-In Providers

Telegodex no longer ships a fixed "built-in providers" dict. Instead, the registry is three transports resolved at runtime:

| Transport | Implementation | Notes |
|---|---|---|
| `openai` | `OpenAIProvider` | Reserved id `openai` — native SDK |
| `anthropic` | `AnthropicProvider` | Reserved id `anthropic` — native SDK |
| `openai_compatible` | `OpenAICompatibleProvider` | Generic — used by gemini, deepseek, qwen, kimi, zhipu, baidu, ollama, lmstudio, and any custom endpoint |

A provider is active if and only if (1) its `[providers.<id>]` block exists in `provider.toml`, (2) its `<id>` is listed under `[global].available_providers`, and (3) its `api_key_env` (or `api_key_literal`) resolves to a non-empty value at startup.

## Custom Providers

Any OpenAI-compatible endpoint supplies its own model list directly in `provider.toml`:

```toml
[providers.my_provider]
transport = "openai_compatible"
api_key_env = "MY_PROVIDER_API_KEY"
base_url = "https://api.example.com/v1"
models = ["model-a", "model-b"]
default_model = "model-a"
```

See `docs/CUSTOM_PROVIDERS.md` for the full configuration guide.

## Maintenance Rule

Do not claim a model is "latest", "best", or "officially current" from memory. Check the provider's official docs or release notes before changing model names. If you cannot verify a model, document it as a configured default, not as a recommendation.
