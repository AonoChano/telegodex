---
title: Quickstart
category: guide
last_updated: 2026-06-30
relevance: high
summary: Install, configure, and start Telegodex
related: [USAGE.md, PRODUCT_EXPERIENCE.md, CUSTOM_PROVIDERS.md, STARTUP.md]
---

# Quickstart

## Install

```bash
git clone https://github.com/CYcha/Telegodex.git
cd Telegodex
pip install -r requirements.txt
cp .env.example .env
cp provider.toml.example provider.toml
```

Edit `.env` and set `TELEGRAM_BOT_TOKEN` plus the API keys referenced by `provider.toml`:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
DEEPSEEK_API_KEY=
```

## Start

Check config without starting the polling loop:

```bash
python run.py --check-config
```

Then start the bot:

```bash
python run.py
```

Send `/start` to the bot in Telegram.

## Add A Custom Provider

Add the provider block to `provider.toml` and list it under `[global].available_providers`:

```toml
[global]
default_provider = "ollama"
available_providers = ["ollama"]

[providers.ollama]
transport = "openai_compatible"
api_key_literal = "ollama"
base_url = "http://localhost:11434/v1"
default_model = "llama3.2"
models = ["llama3.2"]
```

Run `python run.py --check-config`, restart the bot, and the provider appears in the settings flow.

## Read Next

- [Usage](USAGE.md)
- [Product experience](PRODUCT_EXPERIENCE.md)
- [Architecture](ARCHITECTURE.md)
- [Custom providers](CUSTOM_PROVIDERS.md)
- [Model catalog](MODELS.md)
- [Rich messages](RICH_MESSAGES.md)
- [Startup and polling](STARTUP.md)
