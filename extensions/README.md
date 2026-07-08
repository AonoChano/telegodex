# Extensions

## Codex (`codex/`)

CodexBridge connects Telegram to the local Codex CLI through a persistent
`codex app-server --listen stdio://` subprocess. Telegodex talks to that process
with newline-delimited JSON-RPC, streams turn notifications into Telegram draft
messages, and persists final output with `sendRichMessage`.

**Command:** `/codex new` creates a fresh dedicated Codex forum topic. `/codex resume <thread-id>` resumes an existing Codex app-server thread and binds it to a newly created Codex topic. Plain prompts are accepted inside active Codex-bound topics without the `/codex` prefix; All and ordinary topics do not run Codex turns directly.

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

Codex topic routing is exclusive. Active Codex-bound topics stay on the Codex
path. Historical Codex topics without an active thread ask the user to create a
fresh Codex session or cancel, and do not fall back to ordinary AI chat. Ordinary
non-Codex topics remain available for normal AI chat.

**Configuration:** Auto-detected from PATH and common install locations. Set
`CODEX_EXECUTABLE_PATH` in `.env` only if needed.

Runtime knobs:

- `CODEX_DAEMON_AUTO_START`
- `CODEX_DAEMON_MAX_RESTARTS`
- `CODEX_APPROVAL_TIMEOUT`

## Claude Code (`claude_code/`)

Reserved for future Claude Code Agent SDK integration.
