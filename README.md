<div align="center">

<img src="docs/assets/logo.svg" alt="Telegodex Logo" width="900">

# Telegodex

**A Telegram Workbench Project. Control Your Codex on Telegram.**  
Multi-AI provider support, TOML provider registry, Codex bridge foundation, and rich Telegram-native output.

<p>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-22c55e.svg" alt="License"></a>
  <a href="#tech-stack"><img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python 3.11+"></a>
  <a href="https://docs.aiogram.dev/"><img src="https://img.shields.io/badge/aiogram-3.x-26A5E4?logo=telegram&logoColor=white" alt="aiogram 3.x"></a>
  <a href="#tech-stack"><img src="https://img.shields.io/badge/SQLAlchemy-2.x-D71F00?logo=sqlalchemy&logoColor=white" alt="SQLAlchemy 2.x"></a>
  <a href="#roadmap"><img src="https://img.shields.io/badge/status-active%20development-f59e0b.svg" alt="Active development"></a>
</p>

<underline>English</underline> · [简体中文](docs/i18n/README.zh-CN.md) · [日本語](docs/i18n/README.ja.md)

</div>

---

## What this project is

Telegodex is a Telegram-based workbench for AI-assisted workflows.

It is designed for three things:

- **Remote control for Codex / CLI agents.** Bring terminal-grade AI workflows into Telegram so you can operate them from your phone.
- **Multi-provider AI access.** Switch between OpenAI, Anthropic, Google, DeepSeek, Qwen, Kimi, GLM, and ERNIE with one interface.
- **TOML provider registry.** Add, disable, or switch OpenAI-compatible endpoints through `provider.toml` without touching core code.

This is not just a chat bot.  
It is a control surface for AI work.

---

## What it can do

- **Control your Codex workflow from Telegram.** Send prompts, receive streamed output, review actions, and keep the interaction on mobile.
- **Render AI output in a Telegram-native way.** Code blocks, tables, lists, quotes, expandable sections, formulas, and structured summaries.
- **Keep one interface across providers.** Same handler, same UX, different backends.
- **Support local and self-hosted endpoints.** Ollama, vLLM, LiteLLM, Azure, LM Studio, and other OpenAI-compatible services.
- **Gate local tool use from normal chat.** Chat can stay text-only, ask for inline confirmation, or run allowed shell tools with full access.
- **Keep session state per user.** History, preferences, model selection, temperature, and rate limits.
- **Stay operationally safe.** Sanitized input, allow-list admin gate, and no API keys in logs.

---

## Current focus

The project is being shaped from a generic AI bot into a real Telegram workbench.

### Stage 1
- Multi-provider chat foundation
- TOML provider registry
- Telegram-native rendering
- Storage, preferences, and security

### Stage 2
- Codex CLI bridge foundation
- Session sync and output streaming
- Inline approval prompts
- Tool-call visibility and local shell gating

### Stage 3
- Claude Code bridge
- Agent-style workflows inside Telegram
- Better task orchestration and long-running jobs
- Dashboard and deployment tooling

---

## Quick start

```bash
git clone https://github.com/CYcha/Telegodex.git
cd Telegodex
pip install -r requirements.txt
cp .env.example .env
cp provider.toml.example provider.toml
```

Set `TELEGRAM_BOT_TOKEN` and the provider keys referenced by `provider.toml` in `.env`.
Then choose active providers in `[global].available_providers` and run:

```bash
python run.py --check-config
python run.py
```

Send `/start` to your bot.

Full walkthrough: [docs/QUICKSTART.md](docs/QUICKSTART.md)

---

## Add a custom provider

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

Add the block to `provider.toml`, run `python run.py --check-config`, restart, and the provider becomes available.

Reference: [docs/CUSTOM_PROVIDERS.md](docs/CUSTOM_PROVIDERS.md)

---

## Layout

```text
ai/          BaseAIProvider + provider implementations
bot/         aiogram handlers, keyboards, rich rendering
storage/     SQLAlchemy async ORM (User, Conversation, Message)
security/    rate limit, admin gate, input validation
extensions/  Codex and Claude Code bridges
```

Provider contract:

- `chat()`
- `chat_stream()`
- `get_available_models()`
- `validate_api_key()`

The router selects the provider.  
The handlers stay unchanged.

---

## Supported providers

| Region | Provider | Default models |
|---|---|---|
| International | OpenAI, Anthropic, Google | configured in `provider.toml` |
| China | DeepSeek, Qwen, Kimi, GLM, ERNIE | configured in `provider.toml` |

Any OpenAI-compatible endpoint can be added through `provider.toml`.

Full catalog: [docs/MODELS.md](docs/MODELS.md)

---

## Tech stack

Python 3.11+ · aiogram 3.x · SQLAlchemy 2.x async · Pydantic Settings · Alembic · Redis (optional)

---

## Documentation

- [Quickstart](docs/QUICKSTART.md)
- [Usage](docs/USAGE.md)
- [Product experience](docs/PRODUCT_EXPERIENCE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Custom providers](docs/CUSTOM_PROVIDERS.md)
- [Model catalog](docs/MODELS.md)
- [Rich messages](docs/RICH_MESSAGES.md)

---

## Roadmap

- [x] Multi-provider abstraction
- [x] Rich Telegram rendering
- [x] Context windowing and user preferences
- [x] Codex bridge foundation
- [ ] Full Codex workbench UX
- [ ] Claude Code bridge
- [ ] Agent/task execution layer
- [ ] Web admin dashboard
- [ ] Voice and image input
- [ ] Docker compose & Helm chart

---

## Contributing

PRs welcome. Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) before opening changes.

---

## Security

Report vulnerabilities privately to the maintainer.

Enforced by the codebase:

- no API keys in logs
- sanitized input at every boundary
- `ADMIN_USER_IDS` allow-list
- per-user rate limits

---

## License

MIT. See [LICENSE](LICENSE).
