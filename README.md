<div align="center">

<img src="docs/assets/logo.svg" alt="Telegodex Logo" width="900">
A Telegram bot framework for AI chats. Eight providers built in, more via JSON config.

<p>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-22c55e.svg" alt="License"></a>
  <a href="#tech-stack"><img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python 3.11+"></a>
  <a href="https://docs.aiogram.dev/"><img src="https://img.shields.io/badge/aiogram-3.x-26A5E4?logo=telegram&logoColor=white" alt="aiogram 3.x"></a>
  <a href="#tech-stack"><img src="https://img.shields.io/badge/SQLAlchemy-2.x-D71F00?logo=sqlalchemy&logoColor=white" alt="SQLAlchemy 2.x"></a>
  <a href="#roadmap"><img src="https://img.shields.io/badge/status-active%20development-f59e0b.svg" alt="Active development"></a>
</p>

<underline>English</underline>  · [简体中文](docs/i18n/README.zh-CN.md) · [日本語](docs/i18n/README.ja.md)

</div>

---

## What it does

A Telegram bot, with all the production stuff most demos skip.

- **Eight providers, one interface.** OpenAI, Anthropic, Google, DeepSeek, Qwen, Kimi, GLM, ERNIE. Switch by changing a config flag.
- **Custom providers via JSON.** Add any OpenAI-compatible endpoint (Ollama, vLLM, LiteLLM, Azure, LM Studio) to `custom_providers.json`. No code change.
- **A new provider in <50 lines.** Inherit `BaseAIProvider`, implement 4 methods, register in the router. A plugin, not a fork.
- **Telegram-native rendering.** MarkdownV2 with tables, task lists, footnotes, expandable blockquotes, LaTeX. Inline buttons, reply keyboards, model and temperature pickers.
- **Persistence and security built in.** Conversation history, per-user preferences, per-user rate limits, admin allow-list, sanitized input, no API keys in logs.

## Quick start

```bash
git clone https://github.com/CYcha/Telegodex.git
cd Telegodex
pip install -r requirements.txt
cp .env.example .env
```

Fill in `TELEGRAM_BOT_TOKEN` and at least one provider key in `.env`, then:

```bash
python run.py
```

Send `/start` to your bot.

Full walkthrough: [docs/QUICKSTART.md](docs/QUICKSTART.md).

## Add a custom provider

```json
{
  "ollama": {
    "type": "openai_compatible",
    "base_url": "http://localhost:11434/v1",
    "models": ["llama3.2"]
  }
}
```

Add the block to `custom_providers.json`, restart, done.

Reference: [docs/CUSTOM_PROVIDERS.md](docs/CUSTOM_PROVIDERS.md).

## Layout

```
ai/          BaseAIProvider + 8 implementations
bot/         aiogram handlers, keyboards, rich rendering
storage/     SQLAlchemy async ORM (User, Conversation, Message)
security/    rate limit, admin gate, input validation
extensions/  Codex and Claude Code bridges
```

Provider contract: `chat()`, `chat_stream()`, `get_available_models()`, `validate_api_key()`. Swap providers in the router; handlers stay the same.

## Supported providers

| Region | Provider | Default models |
|---|---|---|
| International | OpenAI, Anthropic, Google | `gpt-4o`, `claude-sonnet-4.6`, `gemini-2.0-flash` |
| China | DeepSeek, Qwen, Kimi, GLM, ERNIE | `deepseek-v4-pro`, `qwen-max`, `kimi-k2-7-code`, `glm-4-6`, `ernie-5.0` |

Plus any OpenAI-compatible endpoint through `custom_providers.json`. Full catalog: [docs/MODELS.md](docs/MODELS.md).

## Tech stack

Python 3.11+ · aiogram 3.x · SQLAlchemy 2.x async · Pydantic Settings · Alembic · Redis (optional)

## Documentation

- [Quickstart](docs/QUICKSTART.md)
- [Usage](docs/USAGE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Custom providers](docs/CUSTOM_PROVIDERS.md)
- [Model catalog](docs/MODELS.md)
- [Rich messages](docs/RICH_MESSAGES.md)

## Roadmap

- [x] Multi-provider abstraction (v1.0)
- [x] Rich Markdown, interactive keyboards, context windowing (v1.1)
- [ ] Codex bridge
- [ ] Claude Code bridge
- [ ] Web admin dashboard
- [ ] Voice and image input
- [ ] Docker compose & Helm chart

## Contributing

PRs welcome. Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [CLAUDE.md](CLAUDE.md) first.

## Security

Vulnerabilities: email the maintainer (see commit history). Don't open a public issue.

What the code enforces: no API keys in logs, sanitized input at every boundary, `ADMIN_USER_IDS` allow-list, per-user rate limits.

## License

MIT. See [LICENSE](LICENSE).

---

