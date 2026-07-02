---
title: "🤖 AI Providers"
order: 3
---

# AI Providers

Telegodex supports multiple AI providers so you can pick the right model for
each task without leaving Telegram.

---

## Built-in Providers

| Provider | Family | Examples |
|---|---|---|
| OpenAI | GPT | GPT-4o, GPT-4 Turbo |
| Anthropic | Claude | Claude 3.5 Sonnet, Claude 3 Opus |
| Google | Gemini | Gemini 1.5 Pro, Gemini Flash |

Built-in providers are configured on the server side. Once their API keys are
in place, they appear automatically in the provider selector.

---

## Custom Providers

Any OpenAI-compatible endpoint can be added as a **custom provider** through a
JSON config file. This lets you plug in self-hosted models, proxy gateways, or
niche vendors without changing Telegodex's code.

Custom providers behave exactly like built-ins: they show up in Settings, keep
their own model list, and can be switched to on the fly.

---

## Switching Providers

1. Open `/settings`.
2. Tap **🤖 Switch AI provider**.
3. Pick a provider from the list.
4. The bot confirms the switch. Messages sent afterwards use the new provider.

Each forum thread keeps its own provider, so you can run GPT in one topic and
Claude in another without them interfering.

---

## Selecting a Model

Each provider exposes several models. Inside **⚙️ Settings → 🎯 Select model**
you can pick which model the active provider should use. Models with larger
context windows are better for long conversations; smaller models are faster
and cheaper.

---

## Temperature

Temperature controls how creative the output is:

| Value | Behavior |
|---|---|
| `0.2` | Focused, deterministic |
| `1.0` | Balanced, creative |
| `1.3` | Very creative, less predictable |

Adjust it under **⚙️ Settings → 🌡️ Adjust temperature**. The change applies
to the next message you send.
