---
title: Changelog
category: changelog
last_updated: 2026-06-26
relevance: medium
summary: Human-maintained release notes for Telegodex
related: [PRODUCT_EXPERIENCE.md, RICH_MESSAGES.md, STARTUP.md]
---

# Changelog

## Unreleased

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
