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
| `/codex` | Run Codex CLI tasks through the app-server bridge |

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

Telegram's AI chatbot integration can place conversations in separate private chat topics. Code keeps those topics separate by the route Telegram sends with each message. Threaded private AI chats use `message_thread_id`; channel direct messages topics use `direct_messages_topic_id`.

## Streaming Output

When a provider supports `chat_stream()`, Telegodex streams temporary Rich Message drafts in private chats, then persists the complete answer with `sendRichMessage`. Drafts are previews, not stored messages. If Telegram rejects drafts, the bot skips the preview and still sends the final answer.

## CodexBridge

Use `/codex <prompt>` to run Codex CLI tasks from Telegram. The bot runs a persistent `codex app-server` subprocess and communicates via JSON-RPC 2.0 over stdio. Each Telegram private chat gets its own Codex session (thread) with persistent context across turns.

**Commands:**

| Prefix | Usage | Purpose |
|---|---|---|
| (none) | `/codex <prompt>` | Send a prompt to Codex for code generation/analysis |
| `/` | `/codex /<skill>` | List or invoke Codex skills |
| `!` | `/codex !<command>` | Execute a shell command in the session |
| `@` | `/codex @<path>` | List files in a directory |
| `new` | `/codex new` | Start a fresh Codex session |

**Examples:**

```
/codex Write a Python FastAPI endpoint for user login
/codex /status
/codex !ls -la
/codex @src/
/codex new
```

**Approvals:** When Codex wants to execute a command or modify a file, it sends an approval request with inline Approve/Deny buttons. Approvals auto-deny after 60 seconds (configurable via `CODEX_APPROVAL_TIMEOUT`).

**Streaming:** Codex output is streamed as Rich Message drafts in private chats (up to 6 drafts per turn), then persisted as a final Rich Message.

**Configuration:**

- Codex CLI is auto-detected from PATH and common installation locations. Set `CODEX_EXECUTABLE_PATH` in `.env` only if auto-detection fails.
- `CODEX_DAEMON_AUTO_START` (default: `true`) — start the app-server daemon on bot startup.
- `CODEX_DAEMON_MAX_RESTARTS` (default: `3`) — max crash restart attempts with exponential backoff.
- `CODEX_APPROVAL_TIMEOUT` (default: `60`) — seconds before auto-denying unresponded approvals.

Telegram allows one active polling process per bot token. Run one Telegodex process per token. See [STARTUP.md](STARTUP.md) for the local lock and conflict behavior.

Keep `.env`, `custom_providers.json`, database files, and logs out of commits. `.env.example` and `custom_providers.example.json` are the safe templates.

## Troubleshooting

`Conflict: terminated by other getUpdates request` means another process uses the same token. Stop the other process or switch one instance to a different bot token.

If a provider call fails, confirm the API key, base URL, model name, and network path. For custom providers, test the endpoint with a minimal OpenAI-compatible chat-completions request.
