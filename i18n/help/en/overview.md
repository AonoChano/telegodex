---
title: "📋 Overview"
order: 1
---

# Telegodex

Telegodex is a **Telegram Workbench** for AI chat and AI agents. It is not just
another chatbot — it is a control surface for talking to multiple AI providers
and, eventually, for driving CLI agents like Codex directly from Telegram.

The bot lives in your chat list, remembers context across turns, and renders
rich Markdown (tables, code blocks, LaTeX) the way Telegram natively intends.

---

## Core Capabilities

| Capability | Status |
|---|---|
| Multi-provider AI chat | ✅ Available |
| Rich Markdown output | ✅ Available |
| Conversation history | ✅ Available |
| Permission modes | ✅ Available |
| Codex / CLI agent bridge | 🚧 Planned |

You pick a provider, send a message, and Telegodex routes it through the
matching adapter, streams the reply back, and stores the turn so the next
message keeps full context.

---

## Multi-Provider Architecture

Telegodex ships with built-in adapters for the major model families, plus a
custom-provider system for anything OpenAI-compatible:

- **OpenAI** — GPT models
- **Anthropic** — Claude models
- **Google** — Gemini models
- **Custom providers** — defined via JSON config

Switch providers on the fly from Settings without leaving the chat. Each
provider keeps its own model list and temperature defaults.

---

## Quick Start

There is nothing to install on your phone. Once the bot is running on the
server side, just open the chat and send any message. Telegodex responds
immediately using the currently selected provider.

Use `/start` to initialize, `/settings` to pick a provider, and `/help` to
open this manual anytime.
