# Contributing

Telegodex is a Telegram Workbench project for developer-operated AI workflows. Contributions should preserve that direction: Telegram-native rich output, provider-neutral AI chat, and safe local agent control.

## Repository Workflow

External contributions are submitted through Pull Requests. Repository maintainers may commit and push directly to `master` after running the relevant local checks. CI runs for both Pull Requests and pushes to `master`; a failed post-push maintainer build should be repaired promptly with a follow-up commit.

Maintainers may still use a branch and Pull Request when a change is high risk or would benefit from review before integration.

## Before Integrating Changes

Run:

```bash
python -m compileall main.py run.py ai bot storage security
python -m pytest
python run.py --check-config
```

For `--check-config`, copy `provider.toml.example` to `provider.toml` and provide placeholder or real environment variables as needed.

## Development Rules

- Do not commit `.env`, `provider.toml`, databases, logs, or local reference dumps.
- Keep user-facing Telegram text behind i18n keys in `i18n/locales/en.json` and `i18n/locales/zh-cn.json`.
- Preserve Telegram thread/topic routing fields when sending replies.
- Keep terminal execution and approval logic out of generic chat handlers.
- Prefer focused changes with tests over broad refactors.

## Public Documentation

README.md is the public positioning source. Keep docs accurate when behavior changes, but avoid linking to local agent guidance or ignored reference folders.
