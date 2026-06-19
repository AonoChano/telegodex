---
title: Changelog
category: changelog
last_updated: 2026-06-19
relevance: medium
summary: Human-maintained release notes for Telegodex
related: [PRODUCT_EXPERIENCE.md, RICH_MESSAGES.md, STARTUP.md]
---

# Changelog

## Unreleased

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
