---
title: Architecture
category: architecture
last_updated: 2026-06-18
relevance: high
summary: Runtime layers, provider contract, Telegram rendering, and Codex bridge boundaries
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
extensions/  Bridge surface for Codex and future CLI agents
prompts/     System prompts sent to model providers
docs/        Public project documentation
core/        Orchestration, session keys, message bus, routing contracts
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

`bot/utils/routing.py` extracts the Telegram route from each incoming message. Use it whenever a handler replies:

- Keep `message_thread_id` for private threaded AI chats and forum topics.
- Keep `direct_messages_topic_id` for channel direct messages chats.
- Keep `business_connection_id` for business-connected updates.
- Use the route's storage key for conversation isolation.

Do not manually pass only `message_thread_id` in new code. Telegram keeps adding chat surfaces, and route extraction is the compatibility boundary.

## Conversation State

The storage layer keeps user preferences and conversation messages. The short-term target is one conversation stream per Telegram AI chat topic. Private threaded AI chats use `message_thread_id`; channel direct messages topics use `direct_messages_topic_id`; plain private chats continue to use the default active conversation.

`core/session` normalizes active runtime state through `SessionKey(transport, chat_id, topic_id)`. Provider-specific buckets keep OpenAI-compatible, Anthropic, Codex, and future agent contexts isolated under the same Telegram route.

## CodexBridge v2

The Codex bridge lives under `extensions/codex/` and runs Codex CLI as a persistent `codex app-server` subprocess communicating via JSON-RPC 2.0 over stdio. Users trigger it with `/codex <prompt>` in Telegram.

```text
extensions/codex/
|-- __init__.py       Public exports (CodexDaemon, CodexSessionManager, etc.)
|-- daemon.py         Persistent app-server subprocess lifecycle
|-- jsonrpc.py        JSON-RPC 2.0 stdio transport
|-- session.py        Telegram SessionKey -> Codex threadId mapping
|-- approvals.py      Approval requests -> Telegram inline buttons
`-- commands.py       Instruction prefix routing (/, !, @)
```

### Architecture

```text
Telegram User
  -> /codex prompt or Codex-bound topic message
  -> bot/handlers/codex.py
  -> core/orchestrator/core.py
  -> CodexSessionManager
  -> CodexDaemon
  -> JsonRpcTransport over stdio
  -> codex app-server
  -> streaming notifications
  -> sendRichMessageDraft / sendRichMessage
```

### Key Components

- **CodexDaemon**: Manages the `codex app-server` subprocess lifecycle with auto-start, restart on crash, stderr logging, and graceful shutdown.
- **JsonRpcTransport**: Implements newline-delimited JSON-RPC over stdio. Handles request/response matching, server notifications, and server requests.
- **CodexSessionManager**: Maps Telegram `SessionKey` (`transport`, `chat_id`, `topic_id`) to Codex `threadId`, persisted via `Conversation.codex_thread_id` and the Codex provider bucket. Supports session creation, resume, topic binding, fork, and shell command execution.
- **ApprovalHandler**: Converts `item/commandExecution/requestApproval` and `item/fileChange/requestApproval` server requests into Telegram inline button messages with Approve/Deny options. Auto-denies after configurable timeout.
- **Instruction Support**: `/codex /skill` lists available skills, `/codex !command` executes shell commands, `/codex @path` reads directory listings.
- **Telegram Controls**: `bot/handlers/toolbar.py` owns temporary ReplyKeyboard controls while a Codex turn or Shell process is active. Slash commands such as `/stop`, `/live`, `/last`, and `/status` remain available without the keyboard.
- **MessageBus**: `core/bus/` carries background results through explicit delivery modes and can inject eligible updates back into an active session.
- **Topic Routing Guard**: Codex topic messages stay on the Codex path. Active Codex-bound topics route directly to Codex; historical Codex topics without an active binding ask the user to create a fresh Codex session or cancel. Ordinary non-Codex forum topics fall through to the normal AI chat handler.

### Streaming Output

Turn output is streamed via Telegram Rich Message drafts. The handler accumulates `item/agentMessage/delta` notifications, filters short internal status chatter, flushes draft updates every 200 characters, streams command output deltas into the same visible text, and persists the final result with `sendRichMessage`.

### Approval Flow

1. Codex sends `item/commandExecution/requestApproval` or `item/fileChange/requestApproval`.
2. `_on_codex_server_request` asks `ApprovalHandler` to track the request and invokes the Telegram approval UI sender.
3. The message is sent to the chat and forum topic matching the Codex thread's reverse lookup.
4. User clicks a button, and `handle_codex_approval` resolves the `ApprovalHandler`.
5. `ApprovalHandler` returns the decision to the app-server.

## Documentation Rule

`README.md` defines the public product story. Keep docs aligned with it:

- Telegodex is a Telegram Workbench project.
- The current release is a multi-provider Telegram bot foundation.
- The long-term product is mobile control for Codex and CLI agents through Telegram.
