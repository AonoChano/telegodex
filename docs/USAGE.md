---
title: Usage
category: guide
last_updated: 2026-06-15
relevance: high
summary: Daily use, commands, provider settings, and rich output behavior
related: [QUICKSTART.md, CUSTOM_PROVIDERS.md, RICH_MESSAGES.md]
---

# Usage

Telegodex currently runs as a Telegram AI bot with a workbench-oriented architecture. You can chat with configured providers today. The Codex bridge will use the same Telegram surface for terminal-grade workflows.

## Commands

| Command | Purpose |
|---|---|
| `/start` | Create or refresh your user record and show the main menu |
| `/new` | Start a new conversation |
| `/clear` | Clear the current conversation history |
| `/settings` | Open provider and model settings |
| `/help` | Show help |

## Provider Selection

Configure built-in provider keys in `.env`. Telegodex loads every configured provider on startup and routes requests through `AIRouter`.

Use `custom_providers.json` for OpenAI-compatible endpoints such as Ollama, LiteLLM, vLLM, LM Studio, and Azure OpenAI. See [CUSTOM_PROVIDERS.md](CUSTOM_PROVIDERS.md).

## Rich Telegram Output

Assistant replies use Telegram Rich Messages:

- headings and sections
- tables and task lists
- block quotes and collapsible `<details>` blocks
- inline code and fenced code blocks
- inline and block math

See [RICH_MESSAGES.md](RICH_MESSAGES.md) for the exact Markdown contract.

## Conversation State

Telegodex stores conversation messages in SQLite by default. `MAX_CONTEXT_MESSAGES` controls how many messages the bot sends back to a provider.

Telegram's AI chatbot integration can place conversations in separate private chat topics. Code should keep those topics separate by `message_thread_id` when Telegram sends one.

## Operational Notes

Telegram allows one active polling process per bot token. Run one Telegodex process per token. See [STARTUP.md](STARTUP.md) for the local lock and conflict behavior.

Keep `.env`, `custom_providers.json`, database files, and logs out of commits. `.env.example` and `custom_providers.example.json` are the safe templates.

## Troubleshooting

`Conflict: terminated by other getUpdates request` means another process uses the same token. Stop the other process or switch one instance to a different bot token.

If a provider call fails, confirm the API key, base URL, model name, and network path. For custom providers, test the endpoint with a minimal OpenAI-compatible chat-completions request.
