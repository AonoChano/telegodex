# Extensions

## Codex (`codex/`)

CodexBridge connects Telegram to the local Codex CLI. It spawns `codex exec
--json` as an async subprocess, parses the JSONL event stream, and delivers
structured Rich Markdown back to Telegram via `sendRichMessageDraft` and
`sendRichMessage`.

**Command:** `/codex <prompt>` in any private chat.

**Architecture:**

```
Telegram Message → bot/handlers/codex.py
                   → extensions/codex/bridge.py  (subprocess management)
                   → extensions/codex/event_parser.py  (JSONL → Rich Markdown)
                   → sendRichMessageDraft / sendRichMessage
```

**Configuration:** Auto-detected from PATH and common install locations.
Set `CODEX_EXECUTABLE_PATH` in `.env` only if needed.

## Claude Code (`claude_code/`)

Reserved for future Claude Code Agent SDK integration.
