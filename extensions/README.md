# Extensions

## Codex (`codex/`)

CodexBridge connects Telegram to the local Codex CLI through a persistent
`codex app-server --listen stdio://` subprocess. Telegodex talks to that process
with newline-delimited JSON-RPC, streams turn notifications into Telegram draft
messages, and persists final output with `sendRichMessage`.

**Command:** `/codex <prompt>` in private chats or Codex-bound forum topics.

**Architecture:**

```text
Telegram Message
  -> bot/handlers/codex.py
  -> core/orchestrator/core.py
  -> extensions/codex/session.py    (Telegram SessionKey -> Codex thread)
  -> extensions/codex/daemon.py     (persistent app-server subprocess)
  -> extensions/codex/jsonrpc.py    (stdio JSON-RPC transport)
  -> sendRichMessageDraft / sendRichMessage
```

`approvals.py` converts app-server approval requests into Telegram inline
buttons. Approval messages are routed back to the Telegram topic bound to the
Codex thread when one exists.

**Configuration:** Auto-detected from PATH and common install locations. Set
`CODEX_EXECUTABLE_PATH` in `.env` only if needed.

Runtime knobs:

- `CODEX_DAEMON_AUTO_START`
- `CODEX_DAEMON_MAX_RESTARTS`
- `CODEX_APPROVAL_TIMEOUT`

## Claude Code (`claude_code/`)

Reserved for future Claude Code Agent SDK integration.
