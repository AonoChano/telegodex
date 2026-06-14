---
title: Quickstart
category: guide
last_updated: 2026-06-15
relevance: high
summary: Install, configure, and start Telegodex
related: [USAGE.md, CUSTOM_PROVIDERS.md, STARTUP.md]
---

# Quickstart

## Install

```bash
git clone https://github.com/CYcha/Telegodex.git
cd Telegodex
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set `TELEGRAM_BOT_TOKEN` plus at least one provider key:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
DEEPSEEK_API_KEY=
```

## Start

```bash
python run.py
```

Check config without starting the polling loop:

```bash
python run.py --check-config
```

Send `/start` to the bot in Telegram.

## Add A Custom Provider

Create `custom_providers.json`:

```json
{
  "ollama": {
    "type": "openai_compatible",
    "api_key": "ollama",
    "base_url": "http://localhost:11434/v1",
    "models": ["llama3.2"],
    "default_model": "llama3.2"
  }
}
```

Restart the bot. The provider appears in the settings flow.

## Read Next

- [Usage](USAGE.md)
- [Architecture](ARCHITECTURE.md)
- [Custom providers](CUSTOM_PROVIDERS.md)
- [Model catalog](MODELS.md)
- [Rich messages](RICH_MESSAGES.md)
- [Startup and polling](STARTUP.md)
