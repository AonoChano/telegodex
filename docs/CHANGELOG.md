---
title: Changelog
category: changelog
last_updated: 2026-06-15
relevance: medium
summary: Human-maintained release notes for Telegodex
related: [RICH_MESSAGES.md, STARTUP.md]
---

# Changelog

## Unreleased

- Reframed the public documentation around the Telegram Workbench goal.
- Replaced stale generated reports and old requirement dumps with current docs.
- Kept `README.md` as the public source of truth for project positioning.

## 2026-06-14

- Added Telegram Rich Messages output through `InputRichMessage.markdown`.
- Added documentation for Rich Markdown behavior and startup polling conflicts.
- Added a local polling lock to avoid duplicate `getUpdates` consumers in one checkout.

## Notes For Maintainers

Do not use this file as a model catalog. Provider model names belong in provider code and must be checked against official provider docs before public claims change.
