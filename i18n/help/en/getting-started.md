---
title: "🚀 Getting Started"
order: 2
---

# Getting Started

Telegodex is operated through Telegram commands and the menu buttons at the
bottom of the chat. This chapter lists every entry point.

---

## Commands

| Command | Action |
|---|---|
| `/start` | Initialize the bot and show status |
| `/new` | Start a new conversation |
| `/clear` | Clear the current conversation |
| `/settings` | Open the settings menu |
| `/help` | Open this help manual |
| `/language` | Change the UI language |
| `/model` | Switch model or provider |
| `/history` | View conversation history |
| `/codex` | Drive Codex CLI as a subprocess (see 🛠️ Codex Bridge) |
| `/shell` | Propose or run a shell command through Codex |
| `/screenshot` | Capture the current terminal window |

Commands are case-insensitive and can be typed anywhere in the chat.

---

## Menu Buttons

Below the input field you will find four persistent buttons:

- **💬 New chat** — same as `/new`, starts a fresh conversation
- **📝 History** — same as `/history`, browses past messages
- **⚙️ Settings** — same as `/settings`, opens the settings menu
- **ℹ️ Help** — same as `/help`, opens this manual

Tap a button instead of typing the command when you prefer.

---

## First Message

To start chatting, type any text and send it. Telegodex routes the message to
the currently selected provider and streams the reply back. If no provider is
configured, the bot will tell you to open `/settings` first.

Use `/new` whenever you want to switch topic without old context bleeding in.
