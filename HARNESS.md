# Telegodex Harness Management

## 🎯 Purpose

This document defines how the **Telegodex Harness** adapts over time — managing documents, rules, and tasks as the project evolves. The harness is the infrastructure layer that makes AI assistance reliable, safe, and efficient.

**Harness = Everything except the model**  
Tools, memory, guardrails, verification, orchestration, permissions, context management.

---

## 📚 Document Management

### Document Lifecycle

```
Created → Active → [Stale] → Archived → [Deleted]
           ↓
       Updated (reset to Active)
```

### When Documents Become Stale

A document is **stale** when:
- Last update >90 days AND code has significantly changed
- References deprecated features or removed code
- Contains outdated version numbers or API endpoints

**Action**: Add `[Stale]` prefix to filename, update YAML `relevance: low`

### Document Categories

#### 1. Living Documents (Frequent Updates)

**Update on every relevant change**:
- `CHANGELOG.md` — Every feature/fix
- `MODELS.md` — When adding/removing AI models
- `FEATURES.md` — When completing features
- `CLAUDE.md` — When harness structure changes
- `RULES.md` — When security/dev rules change

**YAML Settings**:
```yaml
relevance: high
last_updated: <always current>
```

#### 2. Reference Documents (Periodic Updates)

**Update when content area changes**:
- `ARCHITECTURE.md` — When design patterns change
- `CUSTOM_PROVIDERS.md` — When config system changes
- `USAGE.md` — When user-facing behavior changes
- `ANTHROPIC_COMPATIBILITY.md` — When compatibility expands

**YAML Settings**:
```yaml
relevance: high | medium
last_updated: <date of last content change>
```

#### 3. Historical Documents (Rarely Updated)

**Archive after project phase completes**:
- `COMPLETION_REPORT.md` — Phase 1 delivery (2026-06-14)
- `PROJECT_SUMMARY.md` — Initial project overview
- `需求.md` — Original requirements

**YAML Settings**:
```yaml
relevance: low
last_updated: <creation date>
status: archived
```

### Progressive Disclosure Protocol

#### YAML Frontmatter Standard

**Every document** in `docs/` must start with:

```yaml
---
title: Human-Readable Title
category: guide | reference | architecture | changelog | archive
last_updated: YYYY-MM-DD
relevance: high | medium | low
summary: One-sentence description (max 100 chars)
related: [other-doc.md, another-doc.md]
status: active | archived | stale  # optional
---
```

#### Two-Step Reading Protocol

**Step 1: Metadata Scan** (Always do this first)

```python
# Pseudocode for AI assistant behavior
def handle_task(task_description):
    # 1. Identify relevant document categories
    categories = identify_categories(task_description)
    
    # 2. Scan YAML metadata only
    docs = scan_yaml_metadata(categories)
    
    # 3. Filter by relevance
    relevant = [d for d in docs if d.relevance in ['high', 'medium']]
    
    # 4. Only proceed to Step 2 for these docs
    for doc in relevant:
        read_full_content(doc)
```

**Step 2: Precision Read** (Only if relevant)

Only read full content when:
- Task explicitly requires this document
- YAML `relevance: high` for the task domain
- Referenced by another relevant document
- User explicitly asks for it

**Example Scenarios**:

| Task | Metadata Scan | Precision Read |
|------|---------------|----------------|
| "Add Gemini 2.0 support" | All `docs/*.md` | `ARCHITECTURE.md`, `MODELS.md`, `CUSTOM_PROVIDERS.md` |
| "How do I configure Telegram?" | Guide category | `USAGE.md`, `QUICKSTART.md` only |
| "What was the original requirement?" | Archive category | `需求.md` only (if needed) |
| "Fix Markdown rendering bug" | Guide + code | `USAGE.md` + `bot/handlers/messages.py` |

### Document Update Workflow

#### When Code Changes

1. **Identify affected docs**:
   ```bash
   # Modified files
   git diff --name-only
   
   # Check related docs
   grep -r "filename.py" docs/
   ```

2. **Update content** in relevant docs

3. **Update YAML metadata**:
   ```yaml
   last_updated: 2026-06-14  # Today's date
   ```

4. **Commit together**:
   ```bash
   git add filename.py docs/AFFECTED_DOC.md
   git commit -m "feat(feature): add X feature and update docs"
   ```

#### When Creating New Docs

1. **Create with YAML frontmatter** (mandatory)
2. **Add to `CLAUDE.md` Document Index**
3. **Link from related docs** using `related: [new-doc.md]`
4. **Commit**:
   ```bash
   git add docs/new-doc.md CLAUDE.md
   git commit -m "docs: add new-doc guide for X"
   ```

### Archival Process

**When to archive**:
- Document describes completed, historical phase
- Content is no longer relevant to active development
- Replaced by newer, more comprehensive docs

**How to archive**:

1. **Move to archive directory**:
   ```powershell
   Move-Item docs/old-doc.md docs/archive/
   ```

2. **Update YAML**:
   ```yaml
   status: archived
   relevance: low
   ```

3. **Update `CLAUDE.md` index**: Mark as archived

4. **Commit**:
   ```bash
   git commit -m "docs: archive old-doc (replaced by new-doc)"
   ```

---

## 📋 Task Management

### Task File Format (YAML + Markdown)

**Location**: `.claude/tasks/`

**Active Task**: `task-001-streaming-support.md`

```yaml
---
id: task-001
title: Add streaming response support
status: planned | in_progress | blocked | testing | completed | abandoned
priority: critical | high | medium | low
created: 2026-06-14
updated: 2026-06-14
assigned: claude-opus-4.8
estimated_effort: 2h | 1d | 3d | 1w
related_files:
  - bot/handlers/messages.py
  - ai/base.py
  - ai/openai_provider.py
tags: [feature, streaming, telegram]
blocks: []  # task IDs this blocks
blocked_by: []  # task IDs blocking this
---

## Description

Implement streaming response to show typing indicator and progressive message updates in Telegram.

## Context

Current implementation waits for full AI response before sending to user. Streaming would improve UX for long responses.

## Acceptance Criteria

- [ ] Add `chat_stream()` support to all providers
- [ ] Update message handler to use streaming
- [ ] Show typing indicator during streaming
- [ ] Handle stream interruption gracefully
- [ ] Update tests

## Technical Notes

- aiogram 3.x supports `bot.send_chat_action("typing")`
- OpenAI AsyncOpenAI already has streaming support
- Need to batch small chunks to avoid Telegram rate limits

## Progress Log

### 2026-06-14 15:30
- Started reading aiogram docs for streaming
- Identified `edit_message_text()` for progressive updates

### 2026-06-14 16:00
- Implemented basic streaming in OpenAI provider
- Testing with GPT-4o
```

**Completed Task**: `[Closed] task-001-streaming-support.md`

After completion:
1. Rename: `[Closed] task-001-streaming-support.md`
2. Update YAML: `status: completed`, `updated: <completion-date>`
3. Add final notes to Progress Log

**Abandoned Task**: `[Abandoned] task-002-voice-input.md`

If cancelled:
1. Rename: `[Abandoned] task-002-voice-input.md`
2. Update YAML: `status: abandoned`
3. Add reason to Progress Log

### Task Lifecycle

```
📝 planned (just created)
    ↓
🏗️ in_progress (actively working)
    ↓
🚧 blocked (waiting on dependency) → 🏗️ in_progress (unblocked)
    ↓
🧪 testing (implementation done, verifying)
    ↓
✅ completed → [Closed] prefix
    ↓
📦 archived (after 30 days) → moved to .claude/tasks/archive/

Alternative:
🏗️ in_progress → ❌ abandoned → [Abandoned] prefix → deleted after 7 days
```

### Task Reading Protocol for AI

**DO**:
- Read tasks with status: `planned`, `in_progress`, `blocked`, `testing`
- Read `[Closed]` tasks **only if** referenced by current task or user asks
- Scan YAML metadata of all tasks before starting new work (avoid duplicates)

**DON'T**:
- Read full content of `[Closed]` tasks during routine work
- Read `[Abandoned]` tasks (irrelevant)
- Create duplicate tasks (check existing first)

### Task Creation Workflow

**When user requests a feature/fix**:

1. **Check existing tasks**:
   ```powershell
   Get-ChildItem .claude/tasks/*.md | Select-String "title:"
   ```

2. **Create task file**:
   ```powershell
   New-Item .claude/tasks/task-003-add-gemini.md
   ```

3. **Fill YAML + Description** (use template above)

4. **Link related tasks**: If this blocks/is blocked by others, update `blocks`/`blocked_by`

5. **Commit**:
   ```bash
   git add .claude/tasks/task-003-add-gemini.md
   git commit -m "task: add Gemini provider integration task"
   ```

### Task Completion Workflow

**When task is finished**:

1. **Verify acceptance criteria**: All checkboxes ticked

2. **Update task file**:
   - Set `status: completed`
   - Update `updated: <today>`
   - Add final progress note

3. **Rename file**:
   ```powershell
   Rename-Item task-003-add-gemini.md "[Closed] task-003-add-gemini.md"
   ```

4. **Unblock dependent tasks**: Check if any tasks had `blocked_by: [task-003]`, remove the blocker

5. **Commit**:
   ```bash
   git add .claude/tasks/
   git commit -m "task: complete Gemini provider integration (task-003)"
   ```

### Task Archival

**Monthly cleanup** (or when `.claude/tasks/` has >20 files):

1. **Archive old completed tasks**:
   ```powershell
   # Move [Closed] tasks older than 30 days
   Get-ChildItem .claude/tasks/[Closed]*.md | 
       Where-Object LastWriteTime -lt (Get-Date).AddDays(-30) |
       Move-Item -Destination .claude/tasks/archive/
   ```

2. **Delete abandoned tasks**:
   ```powershell
   # Delete [Abandoned] tasks older than 7 days
   Get-ChildItem .claude/tasks/[Abandoned]*.md | 
       Where-Object LastWriteTime -lt (Get-Date).AddDays(-7) |
       Remove-Item
   ```

3. **Commit cleanup**:
   ```bash
   git commit -m "chore(tasks): archive completed tasks and prune abandoned"
   ```

---

## 🔧 Rules Management

### Rule Categories

1. **Security Rules** (`RULES.md` → Security Boundaries)
   - Which files AI must never read
   - Credential handling policies
   - Input validation requirements

2. **Development Standards** (`RULES.md` → Development Standards)
   - Code quality (types, async, errors, docs)
   - Architectural patterns
   - Testing requirements

3. **Git Workflow** (`RULES.md` → Git Workflow)
   - Commit message format
   - Branch strategy
   - Pre-push checklist

### When Rules Need Updates

**Triggers**:
- New security vulnerability discovered
- New file types with sensitive data (e.g., `.secrets.yaml`)
- New development patterns adopted (e.g., adding pytest)
- User feedback on AI behavior

**Update Process**:

1. **Propose change** in conversation:
   ```
   User: "AI shouldn't read .cache/ directory, it has tokens"
   AI: "Agreed. I'll add .cache/ to the forbidden files list in RULES.md"
   ```

2. **Update `RULES.md`**:
   ```markdown
   #### 🚫 Runtime Data
   - **`.cache/`** — Cached authentication tokens
   ```

3. **Update `CLAUDE.md`** if it references affected rules

4. **Commit**:
   ```bash
   git commit -m "docs(rules): add .cache/ to forbidden files list"
   ```

5. **Test**: Have AI assistant read RULES.md and confirm understanding

### Rule Evolution Log

Keep a changelog at bottom of `RULES.md`:

```markdown
## 📜 Rule Change History

### 2026-06-14 - v1.0 (Initial)
- Established security boundaries
- Defined development standards
- Set git workflow

### 2026-06-15 - v1.1
- Added `.cache/` to forbidden files
- Updated commit message examples
```

---

## 🔄 Adaptive Behavior

### Context Management

**Problem**: AI context windows are finite (200K tokens for Opus 4.8)

**Strategy**:
1. **Lazy loading**: Only read files when needed
2. **Metadata-first**: Scan YAML before reading full content
3. **Incremental**: Read in small chunks, not bulk
4. **Pruning**: Close old tasks to reduce noise

### Feedback Loop

**When AI makes mistakes**:

1. **User provides feedback**: "Don't suggest reading .env"
2. **AI updates internal understanding**
3. **AI proposes rule change**: "Should I add this to RULES.md?"
4. **User approves**
5. **AI updates harness documents**

**Example**:

```
User: "You just tried to read .env again. That's forbidden."

AI: "You're right, my apologies. I see in RULES.md that .env is forbidden.
     Should I add a more prominent warning at the top of CLAUDE.md to prevent
     this mistake in the future?"

User: "Yes, do it."

AI: *Updates CLAUDE.md with banner warning*
    *Commits: "docs(claude): add prominent .env warning banner"*
```

### Harness Health Checks

**Monthly review** (or when requested):

1. **Document freshness**:
   - Any docs with `last_updated` >90 days?
   - Any `[Stale]` docs that need updating or archiving?

2. **Task backlog**:
   - Any `blocked` tasks for >14 days? (investigate blocker)
   - Any `in_progress` tasks for >7 days with no updates? (check status)

3. **Rule compliance**:
   - Check recent git history for `.env` commits (shouldn't exist)
   - Review logs for forbidden file access attempts

4. **Structure cleanup**:
   - Archive old `[Closed]` tasks
   - Delete `[Abandoned]` tasks
   - Verify `.gitignore` is up to date

---

## 🚀 Harness Upgrade Path

### Future Enhancements

**Phase 2: Codex Integration** (planned)

When remote Codex access is implemented:
1. Create `.claude/codex/` directory
2. Add `docs/CODEX_INTEGRATION.md`
3. Update `RULES.md` with Codex-specific security rules
4. Add Codex tasks to `.claude/tasks/`

**Phase 3: Multi-User Support** (future)

When supporting multiple Telegram users:
1. Add per-user context management
2. Update security rules for user data isolation
3. Create `docs/USER_MANAGEMENT.md`

**Phase 4: Plugin Ecosystem** (future)

When allowing third-party plugins:
1. Create `docs/PLUGIN_DEVELOPMENT.md`
2. Add plugin security sandboxing rules
3. Create `.claude/plugins/` directory

### Harness Versioning

Track harness structure changes:

```markdown
# Harness Version History

## v1.0 (2026-06-14) - Initial Structure
- Created CLAUDE.md, RULES.md, HARNESS.md
- Established task management system
- Defined document lifecycle
- Set up progressive disclosure

## v1.1 (TBD) - Codex Integration
- Add Codex-specific rules
- Create remote operation tasks
- Update security boundaries
```

---

## 📖 Quick Reference

### For AI Assistants

**Starting a new task?**
1. Read `CLAUDE.md` → Quick Reference
2. Scan `.claude/tasks/*.md` metadata (avoid duplicates)
3. Read relevant docs (metadata-first approach)
4. Check `RULES.md` security boundaries
5. Create task file if multi-step work

**Modifying code?**
1. Read target file first
2. Follow `RULES.md` → Development Standards
3. Update related docs in `docs/`
4. Run tests (when available)
5. Commit with conventional format

**Answering questions?**
1. Scan doc metadata in `docs/`
2. Read relevant docs only (precision read)
3. Never read `.env` or other forbidden files
4. Cite sources with file:line references

### For Human Developers

**Adding a document?**
- Include YAML frontmatter
- Add to `CLAUDE.md` index
- Link from related docs

**Changing rules?**
- Update `RULES.md`
- Announce to AI assistants
- Commit with `docs(rules):` prefix

**Managing tasks?**
- Use YAML+MD format
- Rename with `[Closed]` when done
- Archive old tasks monthly

---

**Last Updated**: 2026-06-14  
**Harness Version**: 1.0  
**Status**: Active - AI assistants must follow adaptive protocols
