---
title: Architecture
category: architecture
last_updated: 2026-06-15
relevance: high
summary: Runtime layers, provider contract, Telegram rendering, and future Codex bridge boundaries
related: [CUSTOM_PROVIDERS.md, RICH_MESSAGES.md, STARTUP.md]
---

# Architecture

Telegodex is a Telegram workbench. The current code ships the chat foundation first: multi-provider routing, rich Telegram output, conversation storage, and safety checks. The next product line is the Codex bridge.

## Runtime Layout

```text
ai/          Provider abstraction and provider implementations
bot/         Telegram handlers, keyboards, rich message helpers
storage/     SQLAlchemy async ORM for users, conversations, and messages
security/    Input sanitization, rate limiting, admin gate
extensions/  Reserved bridge surface for Codex and Claude Code
prompts/     System prompts sent to model providers
docs/        Public project documentation
```

The bot starts in `run.py`, validates local config, then calls `main.py`. `main.py` creates the database, provider router, Telegram bot, dispatcher, and dependency-injection middleware.

## Provider Contract

Every provider implements `BaseAIProvider`:

```python
chat(messages, model, temperature, max_tokens) -> AIResponse
chat_stream(messages, model, temperature, max_tokens) -> AsyncIterator[str]
get_available_models() -> list[str]
validate_api_key() -> bool
```

Handlers depend on that contract, not on individual SDKs. A new built-in provider belongs in `ai/` and gets registered in `AIRouter.BUILTIN_PROVIDERS`. A user-defined provider should use `custom_providers.json` when the endpoint speaks an OpenAI-compatible chat-completions API.

## Telegram Layer

The message handler does four jobs:

1. Sanitize user text.
2. Load the user and the active conversation.
3. Call the selected provider.
4. Send the result through Telegram Rich Messages.

Rich output goes through `sendRichMessage` with `InputRichMessage.markdown`. Telegram parses headings, tables, lists, block quotes, details blocks, code, and formulas. Local code should not convert Markdown into block dictionaries unless Telegram removes the Markdown field.

`bot/utils/routing.py` extracts the Telegram route from each incoming message.
Use it whenever a handler replies:

- Keep `message_thread_id` for private threaded AI chats and forum topics.
- Keep `direct_messages_topic_id` for channel direct messages chats.
- Keep `business_connection_id` for business-connected updates.
- Use the route's storage key for conversation isolation.

Do not manually pass only `message_thread_id` in new code. Telegram keeps adding
chat surfaces, and route extraction is the compatibility boundary.

## Conversation State

The storage layer keeps user preferences and conversation messages. The short-term target is one conversation stream per Telegram AI chat topic. Private threaded AI chats use `message_thread_id`; channel direct messages topics use `direct_messages_topic_id`; plain private chats continue to use the default active conversation.

## CodexBridge v2

The Codex bridge lives under `extensions/codex/` and runs Codex CLI as a persistent `codex app-server` subprocess communicating via JSON-RPC 2.0 over stdio. Users trigger it with `/codex <prompt>` in Telegram.

```text
extensions/codex/
├── __init__.py       Public exports (CodexDaemon, CodexSessionManager, etc.)
├── daemon.py         Persistent app-server subprocess lifecycle
├── jsonrpc.py        JSON-RPC 2.0 stdio transport (JSONL, no "jsonrpc" wrapper)
├── session.py        Telegram chat_id → Codex threadId mapping
├── approvals.py      Approval requests → Telegram inline buttons
└── commands.py       Instruction prefix routing (/, !, @)
```

### Architecture

```
Telegram User
     │ /codex prompt
     ▼
bot/handlers/codex.py ──── cmd_codex_v2()
     │                           │
     │  get_or_create_session()  │  start_turn()
     ▼                           ▼
CodexSessionManager ──────── CodexDaemon
     │                           │
     │  thread/start             │  JSON-RPC stdio
     │  turn/start               │
     ▼                           ▼
Conversation (DB)          codex app-server
     │                           │
     │  codex_thread_id          │  streaming notifications
     │                           ▼
     └──────────────────── _stream_turn()
                                 │
                                 ▼
                          sendRichMessageDraft
                          sendRichMessage (final)
```

### Key Components

- **CodexDaemon**: Manages the `codex app-server` subprocess lifecycle with auto-start, restart on crash (exponential backoff), and graceful shutdown (SIGTERM → SIGKILL).
- **JsonRpcTransport**: Implements JSON-RPC 2.0 over stdio using newline-delimited JSON. Handles request/response matching, server notifications, and server requests.
- **CodexSessionManager**: Maps Telegram `chat_id` to Codex `threadId`, persisted via `Conversation.codex_thread_id`. Supports session creation, resume, fork, and shell command execution.
- **ApprovalHandler**: Converts `item/commandExecution/requestApproval` and `item/fileChange/requestApproval` server requests into Telegram inline button messages with Approve/Deny options. Auto-denies after configurable timeout (default 60s).
- **Instruction Support**: `/codex /skill` lists available skills, `/codex !command` executes shell commands, `/codex @path` reads directory listings.

### Streaming Output

Turn output is streamed via Telegram Rich Message drafts. The handler accumulates `item/agentMessage/delta` notifications, flushes draft updates every 200 characters (up to 6 drafts per turn), and persists the final result with `sendRichMessage`.

### Approval Flow

1. Codex sends `item/commandExecution/requestApproval` or `item/fileChange/requestApproval`
2. `_on_codex_server_request` formats the request as a Telegram message with inline Approve/Deny buttons
3. Message is sent to the chat matching the Codex thread's `chat_id` (reverse lookup)
4. User clicks a button → `handle_codex_approval` callback resolves the `ApprovalHandler`
5. `ApprovalHandler` returns the decision to the app-server

## Documentation Rule

`README.md` defines the public product story. Keep docs aligned with it:

- Telegodex is a Telegram Workbench project.
- The current release is a multi-provider Telegram bot foundation.
- The long-term product is mobile control for Codex and CLI agents through Telegram.
