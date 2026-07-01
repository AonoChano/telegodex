---
title: Changelog
category: changelog
last_updated: 2026-07-01
relevance: medium
summary: Human-maintained release notes for Telegodex
related: [PRODUCT_EXPERIENCE.md, RICH_MESSAGES.md, STARTUP.md]
---

# Changelog

## Unreleased

- Fixed aiogram polling reconnect status so backoff shows `retry in X.Xs`, active HTTP attempts show `retrying` / `retrying X.Xs`, and the polling request timeout is explicitly bounded by `polling_timeout=10` plus an 8-second HTTP session timeout.
- Redesigned aiogram polling retry display into a state-machine-driven single-line status: dim italic color-blocked layout (Reconnecting · attempt/limit · retry countdown · elapsed · error), category-aware retry limits (network ∞, auth 5, server/client/unknown 10), golden-ratio backoff (max 30 s), success → green log, failure → red log + sys.exit for auth, and worker-generation guard against stale-thread races.
- Removed deprecated vendor-specific AI provider modules now superseded by the TOML transport registry, and added a chat/thread conversation index for existing and new databases.
- Updated public README, Quickstart, Usage, Architecture, and localized README docs to describe the `provider.toml` registry instead of the removed JSON custom-provider flow.
- Fixed provider TOML runtime behavior so `.env` API keys are hydrated without overriding shell variables, missing default providers fail closed, provider `headers`/`query` reach SDK clients, and `[global]` request defaults are honored by normal chat.
- Migrated provider configuration from JSON-based `custom_providers.json` to TOML-based `provider.toml`. The new system uses a transport registry pattern (`openai`/`anthropic`/`openai_compatible`) and moves all provider selection out of `.env` into the `[global]` section of `provider.toml`. See `docs/CUSTOM_PROVIDERS.md` for migration guide.
- Fixed Telegram shell execution on Windows to run through PowerShell, so generated commands such as `Start-Process notepad` work as intended, and polished shell results into Rich Message summaries with folded stdout/stderr blocks.
- Improved the normal-chat Telegodex tool prompt so browser/app launch requests such as opening Bilibili or Notepad are treated as shell tool intents instead of generic AI refusals, and ambiguous “run shell” requests no longer invent demo commands.
- Added normal-chat tool permission modes in Settings: `仅对话`, `用户确认`, and `⚠️ 完全访问`. Normal AI chat now knows it is Telegodex, can request shell tools through a structured Telegodex tool intent, blocks tools in chat-only mode, asks for inline confirmation in confirm mode, and feeds shell results back into the model in full-access mode.
- Improved `/screenshot` capture reliability by ignoring invalid window bounds, retrying full-screen capture after empty terminal-window images, using pyautogui regions correctly, and showing a non-misleading failure message when capture returns an empty image.
- Added AI-assisted `/shell <natural language>` command proposals with Run/Revise/Cancel buttons, raw `/shell !<command>` and `/shell -- <command>` escape hatches, and dangerous-command confirmation before execution.
- Fixed Codex permissions approval requests so Telegram shows inline buttons and returns granted permission scopes to the app-server.
- Clarified the startup preflight logs while preserving the decorative startup banner.
- Fixed Codex approval prompt cleanup so handled inline approval messages no longer remain as unrendered command blocks, and command-running status edits now escape command text before HTML rendering.
- Fixed Codex approval prompts so command/file approval requests are registered before Telegram UI rendering, object-shaped `availableDecisions` are supported, and inline buttons appear in the active Codex topic.
- Fixed Codex Telegram finalization for long tool output: collapsed tool details are now previewed/summarized within Rich Message limits, and plain-message fallback is shortened before send.
- Fixed Codex streaming rendering so tool activity stays in default-collapsed Rich Message details blocks, legacy previews edit the same rich message, and edit failures no longer create repeated transcript messages.
- Fixed Codex runtime error display so late daemon stderr refreshes the live status message, raw provider/runtime details are shown in a dedicated block, and repeated generic `Unknown error` lines are removed.
- Improved ordinary AI chat provider failures: balance/quota/auth errors now show a readable user message and do not retry the same failed request in non-streaming mode.
- Fixed duplicate active conversation rows so they are archived instead of crashing message handling with `MultipleResultsFound`.
- Scoped conversation lookup by Telegram chat to avoid cross-chat/topic context collisions.
- Fixed `/start` provider listing so configured non-built-in providers such as DeepSeek are shown.
- Routed the legacy `⚙️ 设置` reply-keyboard button to the settings menu instead of the placeholder reply.
- Fixed `/codex@botname` parsing so a bare command mention shows usage instead of trying to read a directory named after the bot.
- Updated Codex in-progress status messages when retry/error, reasoning, command execution, failure, or interruption events are visible.
- Added Telegram startup checks that sync the bot command menu and warn admins when private-chat Threaded Mode is not enabled.
- Added a readable public version-control policy in `docs/VERSION-CONTROL.md`.
- Fixed Codex approval callbacks so inline buttons use short Telegram-safe tokens and resolve through the active Orchestrator approval handler.
- Added `docs/PRODUCT_EXPERIENCE.md` as the product-experience baseline for Telegram Workbench behavior.
- Documented strict Codex topic ownership: active Codex-bound topics route to Codex, recoverable historical Codex topics ask create-or-cancel, and ordinary non-Codex topics remain normal AI chat.
- Updated the roadmap to mark the Codex bridge foundation complete while keeping full Codex Workbench UX open.
- Documented that the startup banner version is read from `pyproject.toml`.
- Reframed the public documentation around the Telegram Workbench goal.
- Replaced stale generated reports and old requirement dumps with current docs.
- Kept `README.md` as the public source of truth for project positioning.

## 2026-06-14

- Added Telegram Rich Messages output through `InputRichMessage.markdown`.
- Added documentation for Rich Markdown behavior and startup polling conflicts.
- Added a local polling lock to avoid duplicate `getUpdates` consumers in one checkout.

## Notes For Maintainers

Do not use this file as a model catalog. Provider model names belong in provider code and must be checked against official provider docs before public claims change.
