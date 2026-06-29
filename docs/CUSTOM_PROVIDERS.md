---
title: Provider Configuration Guide
category: reference
last_updated: 2026-06-29
relevance: high
summary: How to add, remove, and configure AI providers via provider.toml (TOML-driven registry)
related: [MODELS.md, ANTHROPIC_COMPATIBILITY.md, ARCHITECTURE.md, STARTUP.md]
---

# Provider Configuration Guide

Telegodex configures every AI provider through a single TOML file: `provider.toml`. Copy the template to start:

```bash
cp provider.toml.example provider.toml
```

Then edit `provider.toml` and add the corresponding API key env vars to `.env`. No code changes are required to add, remove, or switch providers.

## Core Concepts

### Three transports, one registry

Every provider entry maps to one of three transports via the `transport` field:

| Transport | SDK | When to use |
|---|---|---|
| `openai` | Native OpenAI SDK | OpenAI itself, or a proxy exposing the OpenAI protocol under the reserved `openai` id |
| `anthropic` | Native Anthropic SDK | Anthropic itself, or an Anthropic-compatible endpoint (e.g. DeepSeek's `/anthropic` mode) |
| `openai_compatible` | Generic OpenAI-compatible HTTP client | Anything else — gemini, qwen, kimi, zhipu, baidu, ollama, lmstudio, vLLM, LiteLLM, Azure, custom gateways |

The native SDKs are only used when `transport` declares `openai` or `anthropic`. Every other vendor goes through the generic `OpenAICompatibleProvider`.

### `available_providers` is a mandatory filter

A `[providers.<id>]` block in TOML is **not** instantiated unless its `<id>` is listed under `[global].available_providers`. This is a strict filter:

- An empty `available_providers = []` activates NOTHING — the user must explicitly list every provider they want active.
- A provider block can stay in TOML but be temporarily disabled by removing it from `available_providers` (no need to delete the block).

### Secrets never live in TOML

API keys and other secrets are resolved at runtime from environment variables referenced by `api_key_env` / `secret_key_env` / `base_url_env`. The literal `api_key_literal` field exists ONLY for local servers (ollama, lmstudio) that accept any non-empty token — never put a real API key there.

Resolution precedence:

```text
api_key:  api_key_literal > api_key_env > provider is skipped at startup
base_url: base_url        > base_url_env > provider SDK default
```

### Reserved provider IDs

`openai` and `anthropic` are reserved for the built-in native SDK transports. You MAY keep `[providers.openai]` / `[providers.anthropic]` blocks in TOML — they configure the native SDK transports (base_url, api_key_env, default_model). You CANNOT use these IDs with a different transport (e.g. `[providers.openai]` with `transport = "openai_compatible"` will be rejected by the loader). To register a custom OpenAI-compatible endpoint, use a different id (e.g. `openai-custom` or `my-gateway`).

## Field Reference

See `provider.toml.example` for the canonical, fully-commented template. Key fields per `[providers.<id>]` block:

| Field | Required | Description |
|---|---|---|
| `transport` | Recommended | `openai` / `anthropic` / `openai_compatible` (default if omitted: `openai_compatible`) |
| `api_key_env` | One of `api_key_*` | Env var name to read the API key from |
| `api_key_literal` | One of `api_key_*` | Literal non-secret token (local servers only) |
| `base_url` | One of `base_url_*` | Literal API base URL |
| `base_url_env` | One of `base_url_*` | Env var name to read the base URL from |
| `default_model` | Recommended | Default model id; falls back to first entry of `models` |
| `models` | Recommended | List of available model ids |
| `headers` | Optional | Extra HTTP headers to send with each request |
| `query` | Optional | Extra query parameters appended to each request URL |
| `supports_stream` | Optional | Default `true` |
| `supports_tools` / `supports_vision` / `supports_json_schema` / `supports_audio` / `supports_files` | Optional | Capability flags; all default to `false` (conservative) |
| `secret_key_env` | Reserved | Phase 2 — parsed but not consumed in Phase 1 |

## Common Scenarios

### Local Ollama

```toml
[global]
default_provider = "ollama"
available_providers = ["ollama"]

[providers.ollama]
transport = "openai_compatible"
api_key_literal = "ollama"
base_url = "http://localhost:11434/v1"
default_model = "llama3.2"
models = ["llama3.2", "qwen2.5", "deepseek-coder"]
```

### LiteLLM Proxy

```toml
[global]
default_provider = "litellm"
available_providers = ["litellm"]

[providers.litellm]
transport = "openai_compatible"
api_key_env = "LITELLM_API_KEY"
base_url = "http://localhost:4000"
default_model = "gpt-4o"
models = ["gpt-4o", "claude-sonnet-4-6", "gemini-3.5-flash"]
```

### Azure OpenAI

```toml
[global]
default_provider = "azure"
available_providers = ["azure"]

[providers.azure]
transport = "openai_compatible"
api_key_env = "AZURE_API_KEY"
base_url = "https://your-resource.openai.azure.com/openai/deployments"
default_model = "gpt-4o"
models = ["gpt-4o", "gpt-35-turbo"]
```

### Anthropic-compatible variant (DeepSeek `/anthropic` mode)

```toml
[global]
default_provider = "deepseek_anthropic"
available_providers = ["deepseek_anthropic"]

[providers.deepseek_anthropic]
transport = "anthropic"
api_key_env = "DEEPSEEK_API_KEY"
base_url = "https://api.deepseek.com/anthropic"
default_model = "deepseek-v4-pro"
models = ["deepseek-v4-pro"]
```

## Migration From `custom_providers.json`

The legacy JSON-based custom provider system (`custom_providers.json` + `CUSTOM_PROVIDERS_CONFIG` env var) is removed. To migrate:

1. Copy `provider.toml.example` to `provider.toml`.
2. For each entry in your old `custom_providers.json`, create a `[providers.<id>]` block in `provider.toml`:
   - `type: "openai_compatible"` → `transport = "openai_compatible"`
   - `api_key: "sk-..."` → move to `.env` as `<ID>_API_KEY=sk-...` and reference via `api_key_env = "<ID>_API_KEY"`
   - `base_url`, `models`, `default_model` carry over unchanged.
3. List every active provider id under `[global].available_providers`.
4. Set `[global].default_provider` to the id you want as the default.
5. Remove the deprecated env vars from `.env`: `DEFAULT_AI_PROVIDER`, `DEFAULT_MODEL`, `MAX_TOKENS`, `TEMPERATURE`, `CUSTOM_PROVIDERS_CONFIG`.
6. Run `python run.py --check-config` to verify.

The old `custom_providers.example.json` / `custom_providers.schema.json` / `configure_provider.py` files are kept as migration references and marked as deprecated at the top of each file.

## Verifying Configuration

```bash
python run.py --check-config
```

This loads `provider.toml`, validates the structure, and checks that `available_providers` is non-empty and that `default_provider` is in the list. It does NOT validate API keys (those are resolved lazily at request time). On success you will see a list of parsed provider blocks; on failure you get a clear error pointing at `provider.toml.example`.

## Reserved Sections (Phase 2)

`[secrets]`, `[routing]`, and `[policy]` are parsed by the loader but NOT consumed in Phase 1. They are reserved for future features (secret manager integration, capability-based routing, per-provider policy overrides). You can leave them in your TOML without breaking anything.
