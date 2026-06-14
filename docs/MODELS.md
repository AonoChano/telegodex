---
title: Model Catalog
category: reference
last_updated: 2026-06-15
relevance: high
summary: Where Telegodex defines provider model names and how maintainers should verify them
related: [CUSTOM_PROVIDERS.md, USAGE.md]
---

# Model Catalog

Telegodex keeps model names in code because providers change names, aliases, and deprecation dates often.

Check these files before editing documentation:

```text
ai/openai_provider.py
ai/anthropic_provider.py
ai/google_provider.py
ai/deepseek_provider.py
ai/china_providers.py
ai/openai_compatible_provider.py
```

## Built-In Providers

The current built-in provider list:

| Provider key | Implementation |
|---|---|
| `openai` | `OpenAIProvider` |
| `anthropic` | `AnthropicProvider` |
| `google` | `GoogleProvider` |
| `deepseek` | `DeepSeekProvider` |
| `qwen` | `QwenProvider` |
| `moonshot` | `MoonshotProvider` |
| `zhipu` | `ZhipuProvider` |
| `baidu` | `BaiduProvider` |

The model names shown in the Telegram settings UI come from each provider's `get_available_models()` method or from `custom_providers.json`.

## Custom Providers

Any OpenAI-compatible endpoint can supply its own model list:

```json
{
  "my_provider": {
    "type": "openai_compatible",
    "api_key": "sk-...",
    "base_url": "https://api.example.com/v1",
    "models": ["model-a", "model-b"],
    "default_model": "model-a"
  }
}
```

## Maintenance Rule

Do not claim a model is "latest", "best", or "officially current" from memory. Check the provider's official docs or release notes before changing model names. If you cannot verify a model, document it as a configured default, not as a recommendation.
