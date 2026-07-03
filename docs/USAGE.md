---
title: Usage
category: guide
last_updated: 2026-06-27
relevance: high
summary: Daily use, commands, provider settings, and rich output behavior
related: [QUICKSTART.md, PRODUCT_EXPERIENCE.md, CUSTOM_PROVIDERS.md, RICH_MESSAGES.md]
---

# Usage

Telegodex runs as a Telegram Workbench. You can chat with configured providers, use Telegram Rich Messages for structured output, and run Codex CLI sessions through the CodexBridge. Ordinary AI chat and Codex sessions keep separate context.

## Commands

| Command | Purpose |
|---|---|
| `/start` | Create or refresh your user record and show the main menu |
| `/new` | Start a new conversation |
| `/clear` | Clear the current conversation history |
| `/settings` | Open provider and model settings |
| `/help` | Show help |
| `/codex` | Run Codex CLI tasks through the app-server bridge |
| `/model` | Switch the current AI provider |
| `/shell` | Ask AI to propose a shell command, or run a raw command with `!`/`--` |
| `/send` | Send a local file or open the file picker |
| `/history` | Browse conversation history |
| `/status` | Show current session status |
| `/stop` | Interrupt the active Codex turn or shell process |
| `/live` | Toggle live session status |
| `/last` | Resend the last assistant reply |
| `/screenshot` | Capture the current desktop |

Telegodex syncs this command menu with Telegram on startup through `setMyCommands`. BotFather is still where the bot token and platform-level bot settings live, but users should not need to maintain the slash-command menu manually.

## Chat Tool Permissions

Open `/settings` and use the `权限:<等级>` button to cycle normal-chat tool access:

- `仅对话` blocks local tools. If the AI tries to inspect local state, run commands, or call a capability, Telegodex stops it and tells you to raise the permission level.
- `用户确认` lets the chat AI request a local shell command, but Telegodex shows the proposed command, reason, and risk with inline Run/Cancel buttons before anything executes.
- `⚠️ 完全访问` lets approved chat tools run directly. Shell output is fed back into the model so the AI can retry or finish the answer based on the real command result.

The normal chat AI receives a Telegodex capability prompt, so it should understand that it is operating inside Telegodex and should not claim it ran tools unless Telegodex actually returns tool results.

Examples of normal-chat tool intents include “帮我打开B站”, which should request `Start-Process https://www.bilibili.com`, and “帮我启动电脑的记事本”, which should request `Start-Process notepad`. If the user only says “执行 shell 指令” without a concrete command or task, the AI should ask what to run instead of inventing a demo command.

## Shell Commands

`/shell` remains a manual escape hatch. Use `/shell <natural language task>` to ask the active chat AI provider to propose a shell command. Telegodex shows the generated command with Run, Revise, and Cancel buttons; it does not execute the generated command until you choose Run.

Use raw mode when you already know the exact command:

```text
/shell !git status
/shell -- git status
```

Dangerous raw commands and dangerous AI-generated proposals still require an inline confirmation before execution. `/shell`, `/shell -h`, `/shell help`, and `/shell --help` show the usage summary. For ordinary tasks, prefer normal chat plus the permission mode that matches how much autonomy you want to grant.

On Windows, Telegodex runs shell commands through PowerShell. Command results are sent as Rich Message summaries with the command, exit code, and folded stdout/stderr blocks. If the rendered output exceeds Telegram text limits, Telegodex sends `shell_output.txt` instead.

## Provider Selection

Telegodex reads provider routing from `provider.toml`. Configure API keys in `.env`, list active provider IDs in `[global].available_providers`, and set `[global].default_provider` to the default provider for normal chat. `python run.py --check-config` validates the TOML structure and fails closed if the configured default provider cannot be instantiated.

Use `provider.toml` for OpenAI-compatible endpoints such as Ollama, LiteLLM, vLLM, LM Studio, and Azure OpenAI. See [CUSTOM_PROVIDERS.md](CUSTOM_PROVIDERS.md).

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

On startup, Telegodex checks whether Telegram reports private-chat Threaded Mode as enabled for the bot. If it is disabled or not reported, configured admins receive a private warning with BotFather guidance. This does not replace forum group setup: forum supergroup topics still need Topics enabled on the group and suitable bot admin permissions.

## Streaming Output

When a provider supports `chat_stream()`, Telegodex streams temporary Rich Message drafts in private chats, then persists the complete answer with `sendRichMessage`. Drafts are previews, not stored messages. If Telegram rejects drafts, the bot skips the preview and still sends the final answer.

## CodexBridge

Use `/codex <prompt>` to run Codex CLI tasks from Telegram. The bot runs a persistent `codex app-server` subprocess and communicates via JSON-RPC 2.0 over stdio. Each Telegram route is keyed by `SessionKey` (`chat_id` plus topic when present), so private chats and Codex-bound forum topics keep separate Codex sessions.

**Commands:**

| Prefix | Usage | Purpose |
|---|---|---|
| (none) | `/codex <prompt>` | Send a prompt to Codex for code generation/analysis |
| `/` | `/codex /<skill>` | List or invoke Codex skills |
| `!` | `/codex !<command>` | Execute a shell command in the session |
| `@` | `/codex @<path>` | List files in a directory |
| `new` | `/codex new` | Start a fresh Codex session |
| `status` | `/codex status` | Show current Codex thread, cwd, and turn state |

**Examples:**

```
/codex Write a Python FastAPI endpoint for user login
/codex /status
/codex !ls -la
/codex @src/
/codex new
```

**Approvals:** When Codex wants to execute a command or modify a file, it sends an approval request with inline Approve/Deny buttons. Approvals auto-deny after 60 seconds (configurable via `CODEX_APPROVAL_TIMEOUT`).

**Forum topics:** In a forum supergroup, `/codex new` creates a fresh Codex session and binds it to a forum topic. Messages sent inside that Codex-bound topic continue the session without repeating the `/codex` prefix.

Codex topic ownership is strict. Active Codex-bound topics route directly to Codex. If a historical Codex topic has no active thread binding, Telegodex asks whether to create a fresh Codex session in that topic or cancel. Canceling, ignoring, or letting the prompt expire leaves the user message unhandled; it does not fall back to ordinary AI chat. Ordinary non-Codex forum topics still fall through to the normal AI chat handler.

**Controls:** While a Codex turn or Shell process is active, Telegodex can show a temporary ReplyKeyboard with controls such as Stop, Live, Last Reply, and Status. Equivalent slash commands are always available: `/stop`, `/live`, `/last`, and `/status`.

**Streaming:** Codex output is streamed as Rich Message drafts in private chats and forum topics, then persisted as a final Rich Message. Command execution output deltas are included in the same stream so long-running commands show progress before completion.

**Errors:** If Codex reports a generic structured failure but the daemon logs a more useful provider/runtime error, Telegodex refreshes the live status message with `Codex runtime detail` and includes the raw detail in the final Rich Message. Repeated generic `Unknown error` lines are removed so quota, auth, rate-limit, and concurrency errors remain readable.

**Configuration:**

- Codex CLI is auto-detected from PATH and common installation locations. Set `CODEX_EXECUTABLE_PATH` in `.env` only if auto-detection fails.
- `CODEX_DAEMON_AUTO_START` (default: `true`) — start the app-server daemon on bot startup.
- `CODEX_DAEMON_MAX_RESTARTS` (default: `3`) — max crash restart attempts with exponential backoff.
- `CODEX_APPROVAL_TIMEOUT` (default: `60`) — seconds before auto-denying unresponded approvals.

Telegram allows one active polling process per bot token. Run one Telegodex process per token. See [STARTUP.md](STARTUP.md) for the local lock and conflict behavior.

Keep `.env`, local `provider.toml`, database files, and logs out of commits. `.env.example` and `provider.toml.example` are the safe templates.

## Troubleshooting

`Conflict: terminated by other getUpdates request` means another process uses the same token. Stop the other process or switch one instance to a different bot token.

If a provider call fails, confirm the API key, base URL, model name, and network path. For custom providers, test the endpoint with a minimal OpenAI-compatible chat-completions request.

If `/screenshot` fails with an empty-image warning even though Pillow is installed, focus or unminimize the terminal/window and retry. Telegodex falls back from terminal-window capture to full-screen capture, but Windows can still return an empty image for minimized, protected, or unavailable capture surfaces.
