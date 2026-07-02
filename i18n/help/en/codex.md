---
title: "🛠️ Codex Bridge"
order: 4
---

# Codex Bridge

Codex Bridge turns Telegodex into a **remote control surface for Codex CLI**.
Unlike an AI provider, Codex runs as a local subprocess — Telegodex drives it
through JSON-RPC, streams its output back to Telegram, and routes every
approval prompt to inline buttons you can tap from your phone.

Think of it as a remote terminal: Codex does the heavy lifting on your
machine, you supervise it from anywhere.

---

## What It Is Not

Codex Bridge is **not** another model provider. It does not call an OpenAI-
compatible chat endpoint. Instead it spawns the local `codex app-server`
binary, talks to it over stdio, and exposes its agentic abilities (file
edits, shell execution, skill calls) through Telegram.

| Aspect | AI Provider | Codex Bridge |
|---|---|---|
| Where it runs | Remote API | Local subprocess |
| What it does | Chat completion | Agentic work, file edits, shell |
| Transport | HTTPS | JSON-RPC over stdio |
| Approvals | N/A | Inline buttons in Telegram |

---

## Invoking Codex

The basic command is `/codex <prompt>`:

- In a private chat, it starts a one-shot Codex turn.
- In a forum supergroup, use `/codex new` to create and bind a fresh Codex
  topic. Every message inside that topic continues the same Codex session
  without needing the `/codex` prefix again.

Codex-bound topics are exclusive — they never fall back to ordinary AI chat.
A historical Codex topic without an active thread asks you to start a new
session or cancel.

---

## Instruction Prefixes

Inside a Codex session, the first character of your message changes how it
is routed:

| Prefix | Meaning | Example |
|---|---|---|
| `/` | Slash command (Codex skill) | `/status` |
| `!` | Raw shell command | `!ls -la` |
| `@` | File path lookup | `@src/main.py` |
| (none) | Normal natural-language prompt | `refactor the auth module` |

Prefixes are how you tell Telegodex "I want a skill, not a chat turn" without
leaving the keyboard.

---

## Approvals

When Codex wants to run a shell command or modify files, Telegodex shows the
exact proposal as an inline keyboard:

- **✅ Approve** — let it run
- **✅ Approve for session** — pre-approve similar actions this session
- **❌ Deny** — refuse and let Codex adapt

Approvals time out automatically if you do not respond, defaulting to a safe
decline. The timeout is configurable via `CODEX_APPROVAL_TIMEOUT`.

---

## Streaming Output

Codex output is streamed into the chat as it is produced:

1. Telegodex opens a draft message and updates it as tokens arrive.
2. stderr lines are surfaced separately so you can see warnings.
3. When the turn finishes, the final Markdown is re-rendered through the
   Rich Message API — tables, code blocks, and LaTeX render natively.

A **⏹ Stop** inline button appears under each active turn. Tap it to
interrupt Codex mid-execution.

---

## Shell Proposals

The `/shell` command lets you ask the AI to propose a shell command in plain
language, then run it through Codex with one tap:

- `/shell find large files in the logs folder` — AI proposes, you approve
- `/shell !du -sh logs/*` — direct execution, no proposal step
- `/shell -- git status` — literal command, no AI involvement

This is the fastest path from "I want this done" to "it is running".

---

## Screenshots

`/screenshot` captures the current terminal window where Codex is running
and sends it as a photo. Use it when you want to verify what Codex is
looking at right now — file listings, editor state, build output — without
leaving Telegram.

---

## Configuration

Codex Bridge auto-detects the `codex` binary from `PATH` and common install
locations. Set these environment variables only if you need to override:

| Variable | Purpose |
|---|---|
| `CODEX_EXECUTABLE_PATH` | Force a specific Codex binary |
| `CODEX_DAEMON_AUTO_START` | Start the daemon on bot launch |
| `CODEX_DAEMON_MAX_RESTARTS` | Restart cap on subprocess crashes |
| `CODEX_APPROVAL_TIMEOUT` | Seconds before an approval auto-denies |

The daemon is persistent: once started, it keeps running across turns so
session state is preserved.
