# Telegodex - AI Agent Harness Configuration

## 🎯 Project True Purpose

**Telegodex** is not just a Telegram bot — it's a **Telegram-to-Codex remote access bridge** that enables real-time code operations via Telegram. The current phase establishes the foundational framework for multi-AI provider integration.

**Current Phase**: Multi-AI provider abstraction layer with plugin architecture  
**Future Phase**: Remote Codex integration for Telegram-based code operations

---

## 🏗️ Architecture Overview

```
Telegodex/
├── ai/              # AI Provider abstractions (BaseAIProvider + implementations)
├── bot/             # Telegram bot handlers (aiogram 3.x)
├── storage/         # SQLAlchemy async ORM (User, Conversation, Message)
├── security/        # Rate limiting, input validation, admin auth
├── extensions/      # Codex/Claude Code integration (future)
├── docs/            # All documentation (see DOCUMENT_INDEX below)
└── .claude/         # Harness metadata (tasks, rules, workflows)
```

**Key Pattern**: Plugin architecture with `BaseAIProvider` abstract base class
- All providers implement: `chat()`, `chat_stream()`, `get_available_models()`, `validate_api_key()`
- Supports: OpenAI, Anthropic, Google, DeepSeek, Qwen, Moonshot, GLM, ERNIE + unlimited custom providers

---

## 🔒 SECURITY RULES (CRITICAL)

### ⛔ NEVER READ THESE FILES

**Absolute ban** — AI assistants must NEVER read or access:

1. **`.env`** — Contains actual API keys and secrets
2. **`custom_providers.json`** — Contains user's real provider configurations and API keys
3. **`telegodex.db`** — SQLite database with user data
4. **`*.log`** — Log files may contain sensitive runtime data
5. **Any file in `logs/` directory** (if exists)
6. **`config.py` runtime instances** — Only read the source code, never execute to inspect values

### ✅ Safe to Read

- **`.env.example`** — Template without real keys
- **`custom_providers.example.json`** — Example configuration
- **`custom_providers.schema.json`** — JSON schema for validation
- All **`.py` source files** — Code review is safe
- All **documentation in `docs/`** — Safe to read

### 🛡️ Security Guidelines

- When suggesting configuration changes, always reference `.env.example`
- Never log, echo, or store actual API key values
- Use sanitization for all user inputs (see `security/input_validation.py`)
- Respect admin authentication (see `config.py` `admin_ids` property)

**Reference**: `RULES.md` for complete security boundaries

---

## 📚 Documentation Reading Protocol

### Two-Step Approach (Speed-Read → Precision)

To avoid context overflow, follow this protocol:

#### Step 1: Speed-Read (YAML Metadata Only)

All documents in `docs/` have YAML frontmatter:

```yaml
---
title: Document Title
category: guide | reference | architecture | changelog
last_updated: 2026-06-14
relevance: high | medium | low
summary: One-line description of content
related: [other-doc-name.md]
---
```

**When starting a task**:
1. Scan YAML metadata of related docs
2. Identify which docs are relevant to the current task
3. Only proceed to Step 2 for relevant documents

#### Step 2: Precision Read (Full Content)

Only read full content of documents that are:
- Directly related to the current task
- Marked as `relevance: high` for the task domain
- Referenced by the user's question

**Example**:
- User asks about adding a new AI provider → Read `docs/CUSTOM_PROVIDERS.md` + `docs/ARCHITECTURE.md`
- User asks about Telegram commands → Read `docs/USAGE.md` + `bot/handlers/`
- User asks about deployment → Read `docs/QUICKSTART.md` only

---

## 📑 Document Index

### Core Documentation

| File | Category | Purpose |
|------|----------|---------|
| `README.md` | overview | Project introduction, quick start |
| `docs/QUICKSTART.md` | guide | Fast reference card for common tasks |
| `docs/USAGE.md` | guide | Complete usage guide |
| `docs/ARCHITECTURE.md` | architecture | System design and patterns |

### Technical References

| File | Category | Purpose |
|------|----------|---------|
| `docs/MODELS.md` | reference | 30+ supported AI models (2026 latest) |
| `docs/CUSTOM_PROVIDERS.md` | reference | Custom provider configuration guide (8000+ words) |
| `docs/ANTHROPIC_COMPATIBILITY.md` | reference | Anthropic API compatibility for DeepSeek |

### Project History

| File | Category | Purpose | Read When |
|------|----------|---------|-----------|
| `docs/CHANGELOG.md` | changelog | v1.1.0 updates | Understanding recent changes |
| `docs/COMPLETION_REPORT.md` | changelog | Full project delivery summary | Onboarding new AI assistants |
| `docs/PROJECT_SUMMARY.md` | changelog | High-level overview | Quick context |
| `docs/FEATURES.md` | changelog | Complete feature checklist | Feature verification |

### Original Requirements

| File | Category | Purpose | Read When |
|------|----------|---------|-----------|
| `docs/需求.md` | archive | Original user requirements (Chinese) | Understanding project genesis |

**⚠️ Archive Status**: `docs/COMPLETION_REPORT.md`, `docs/需求.md` are historical — avoid reading unless specifically asked.

---

## 🔧 Development Workflow

### When Modifying Code

1. **Read before editing**: Always read the file you're about to modify
2. **Check related files**: Use Grep to find imports/references
3. **Verify patterns**: Match existing code style (async-first, type hints, docstrings)
4. **Update docs**: If changing public API, update relevant docs in `docs/`
5. **Test**: Run the bot locally if possible, or explain what should be tested

### When Adding New Features

1. **Check architecture**: Read `docs/ARCHITECTURE.md` first
2. **Follow patterns**: Inherit from base classes (`BaseAIProvider`, etc.)
3. **Update model list**: If adding AI provider, update `docs/MODELS.md`
4. **Document**: Add configuration examples to `docs/CUSTOM_PROVIDERS.md` if applicable
5. **Update changelog**: Add entry to `docs/CHANGELOG.md`

### When Answering Questions

1. **Speed-read**: Check YAML frontmatter of related docs
2. **Precision-read**: Only load full content if necessary
3. **Cite sources**: Reference specific files and line numbers (e.g., `config.py:51-68`)
4. **Avoid assumptions**: If unsure, read the actual code

---

## 📋 Task Management

Tasks are managed in `.claude/tasks/` using YAML+Markdown format.

### Task File Format

**Active Task**: `.claude/tasks/task-001-implement-streaming.md`

```yaml
---
id: task-001
title: Implement streaming response for Telegram
status: in_progress
priority: high
created: 2026-06-14
assigned: claude-opus-4.8
related_files:
  - bot/handlers/messages.py
  - ai/base.py
tags: [feature, telegram, streaming]
---

## Description

Add streaming response support to Telegram handlers...

## Acceptance Criteria

- [ ] Modify `chat_stream()` in BaseAIProvider
- [ ] Update message handlers to use streaming
- [ ] Test with OpenAI and DeepSeek providers

## Progress Notes

- 2026-06-14: Started implementation, reading aiogram docs
```

**Completed Task**: `.claude/tasks/[Closed] task-001-implement-streaming.md`

When a task is completed:
1. Rename file to add `[Closed]` prefix
2. Update `status: completed`
3. Add completion date and notes
4. AI assistants should **skip reading** files with `[Closed]` or `[Completed]` prefix unless explicitly asked

### Task Lifecycle

```
Created → In Progress → [Testing] → [Closed] Completed
                     ↓
                 [Blocked] → [Abandoned]
```

**Prefix Convention**:
- No prefix: Active task (read during planning)
- `[Closed]`: Completed successfully (skip unless referenced)
- `[Abandoned]`: Cancelled or obsolete (skip always)

---

## 🔄 Adaptive Harness Management

**Reference**: `HARNESS.md` for runtime adaptation rules

### Document Updates

When documentation becomes stale:
1. Update the YAML `last_updated` field
2. If content changes significantly, update `summary` field
3. If doc is no longer needed, move to `docs/archive/` and update this index

### Rule Evolution

When security or development rules need changes:
1. Update `RULES.md` first
2. Update this `CLAUDE.md` to reference new rules
3. Communicate changes to user for approval

### Task Pruning

Periodically (or when `.claude/tasks/` has >20 files):
1. Archive all `[Closed]` tasks older than 30 days to `.claude/tasks/archive/`
2. Delete `[Abandoned]` tasks older than 7 days
3. Keep only active and recent completed tasks visible

---

## 🚀 Quick Reference

### Most Common Operations

**Add a new AI provider**:
1. Read `docs/ARCHITECTURE.md` (BaseAIProvider interface)
2. Create provider class in `ai/` or `ai/china_providers.py`
3. Register in `ai/router.py` `BUILTIN_PROVIDERS`
4. Add models to `docs/MODELS.md`
5. Update `docs/CHANGELOG.md`

**Modify configuration system**:
1. Read `config.py` (Pydantic Settings)
2. Update `.env.example` (never `.env`)
3. Update `docs/USAGE.md` with new config
4. Test with example values

**Fix a bug**:
1. Read the problematic file
2. Use Grep to find related code
3. Fix and verify (run bot if possible)
4. Update `docs/CHANGELOG.md` if user-facing

**Answer configuration question**:
1. Read `.env.example` (safe)
2. Reference `docs/QUICKSTART.md` or `docs/USAGE.md`
3. Never suggest reading actual `.env`

---

## 📖 Additional Resources

- **Harness Engineering Concept**: [AI Agent Best Practices 2026](https://medium.com/@tort_mario/ai-agent-best-practices-production-ready-harness-engineering-2026-guide-c1236d713fac)
- **DeepSeek Anthropic API**: [Official Docs](https://api-docs.deepseek.com/zh-cn/guides/anthropic_api)
- **Telegram Bot API 2026**: [Official Docs](https://core.telegram.org/bots/api)

---

**Last Updated**: 2026-06-14  
**Harness Version**: 1.0  
**For**: Claude Code, Claude Opus 4.8, and future AI assistants working on Telegodex
