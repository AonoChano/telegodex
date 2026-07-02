# Telegodex Help Documentation

This folder contains the in-bot help content shown to Telegram users via the
`/help` command. Each chapter is a standalone Markdown file; Telegodex loads
them, splits them into pages, and renders them through Telegram's Rich Message
API (`InputRichMessage.markdown`).

> **Note:** This README is a contributor guide. It is **not** shown to end users.
> Only the per-chapter `.md` files under `en/`, `zh-cn/`, etc. are rendered
> inside Telegram.

---

## 1. Folder Layout

```
i18n/help/
├── README.md                    # This contributor guide
├── translation-status.json      # Auto-generated translation coverage report
├── log/                         # Runtime error logs (auto-generated, JSONL)
├── en/                          # Base language (English) — authoritative source
│   ├── overview.md
│   ├── getting-started.md
│   ├── providers.md
│   ├── codex.md
│   ├── conversations.md
│   ├── permissions.md
│   ├── markdown.md
│   ├── settings.md
│   └── faq.md
└── zh-cn/                       # Chinese translation
    ├── overview.md
    ├── getting-started.md
    ├── providers.md
    ├── codex.md
    ├── conversations.md
    ├── permissions.md
    ├── markdown.md
    ├── settings.md
    └── faq.md
```

Each locale gets its own subfolder named after the locale code
(`en`, `zh-cn`, `ja`, `fr`, …). The folder name MUST match the `_meta.locale`
value in the corresponding `i18n/locales/<locale>.json` file.

---

## 2. File Naming Rules

- **kebab-case only**: `getting-started.md`, not `GettingStarted.md` or
  `getting_started.md`.
- **Filename = chapter_id**: The filename (without `.md`) is used as the
  `chapter_id` in callback data (e.g. `help:open:providers`). Never rename a
  file without updating the bot's callback routing.
- **One chapter per file**: Do not merge multiple chapters into a single file.
- **Locale folders only**: Do not place `.md` chapter files directly under
  `i18n/help/` — they must live inside a locale subfolder.

---

## 3. Frontmatter (Required)

Every chapter file MUST start with a YAML frontmatter block. Both fields are
required — files missing either field will be rejected by the loader.

```markdown
---
title: "📋 Overview"
order: 1
---

# Chapter Title

Content...
```

### Fields

| Field   | Type    | Required | Description                                                                 |
|---------|---------|----------|-----------------------------------------------------------------------------|
| `title` | string  | yes      | Emoji + chapter name. Shown on the TOC button and page header.              |
| `order` | integer | yes      | Positive integer. Sorts chapters in the table of contents (1, 2, 3, …).    |

### Rules

- The opening `---` must be the **first line** of the file (no leading blanks).
- The closing `---` must be on its **own line**.
- `title` is a quoted string so emojis and special characters parse correctly.
- `order` values must be unique within a locale folder. Gaps are allowed
  (e.g. `1, 2, 5, 8`) but discouraged — keep them sequential.
- The same `order` and `title` (translated) MUST be used across all locale
  folders for the same chapter, so the TOC structure stays consistent.

---

## 4. Page Breaks

A **page break** is a line containing exactly `---` (three hyphens), surrounded
by blank lines. It splits the chapter into multiple pages, each rendered as a
separate Telegram message.

```markdown
---
title: "🚀 Getting Started"
order: 2
---

# Getting Started

First page content here.

---

## Commands

Second page content here.
```

### Critical: Page break vs. table separator

| Syntax      | Meaning          | Where it appears                         |
|-------------|------------------|------------------------------------------|
| `---`       | Page break       | On its own line, surrounded by blanks    |
| `\|---\|`   | Table separator  | Inside a Markdown table, under the header|

**Do not confuse them.** `---` on its own line always means "new page". A
table separator always has pipe characters on both sides (`|---|`).

### Page count

Each chapter file MUST contain **at least 2 pages** (i.e. at least one page
break) so the pagination UI is exercised. There is no hard upper limit, but
keep total pages reasonable (3–6 per chapter is typical).

---

## 5. Content Guidelines

### Length per page

- **10–15 lines per page** is the target. Each page should fit on one mobile
  screen without scrolling.
- One screen of Telegram ≈ roughly 12 short lines on a phone. Err on the
  shorter side.
- If a page exceeds ~20 lines, split it with another `---`.

### Rich Markdown features

Content is sent straight to Telegram's Rich Message API. Supported features:

- Headings: `#`, `##`, `###`
- **Bold**: `**text**`
- *Italic*: `*text*`
- Inline code: `` `code` ``
- Code blocks: <code>```lang ... ```</code>
- Tables: `| col1 | col2 |` with `|---|` separator
- Links: `[text](url)`
- Block quotes: `> quote`
- Lists: `- item` or `1. item`
- LaTeX: `$formula$` for inline, `$$formula$$` for block

Avoid raw HTML — it is not rendered. Stick to Markdown.

### Tone

- **Manual-style**, not bullet-soup. Each page should read like a short manual
  section, with at least one full sentence explaining the concept.
- Be concrete: real command names, real values, real examples.
- Stay vendor-neutral unless describing a specific provider.
- Keep emojis sparse — one per heading at most.

### What NOT to include

- No internal implementation details (file paths, class names, callback codes).
- No links to AgentIDE files (`CLAUDE.md`, `RULES.md`, `.trae/`, …).
- No secrets, API keys, or token examples other than `sk-...` placeholders.
- No version numbers that go stale — describe features, not "new in 0.4.2".

---

## 6. Adding a New Chapter

1. Pick a `chapter_id` in kebab-case (e.g. `keyboard-shortcuts`).
2. Decide the `order` value — use the next available integer across all
   existing chapters (check `en/` first).
3. Create `i18n/help/en/<chapter_id>.md` with frontmatter + at least 2 pages.
4. Copy the file to every other locale folder (`zh-cn/`, …) and translate the
   `title` and body. Keep `order` identical.
5. Run the loader check (see §9) to verify the new chapter is discovered.
6. Commit all locale variants in the same change so translations stay in sync.

The TOC will pick up the new chapter automatically — no code changes needed.

---

## 7. Adding a New Language

1. Create `i18n/help/<locale>/` (e.g. `i18n/help/ja/`).
2. Copy **all** files from `i18n/help/en/` into the new folder.
3. Translate the `title` field and the body content. Keep `order` values
   identical to the English originals.
4. Ensure the corresponding `i18n/locales/<locale>.json` exists with a proper
   `_meta` block — the help folder name must match that locale code.
5. Run the loader check (see §9). The new language appears in the language
   selector and help TOC automatically.

**English is the base language.** Always edit `en/` first when changing
content structure, then propagate to other locales. Never edit a translation
without also updating the English master if the meaning changes.

---

## 8. The `log/` Folder

The `i18n/help/log/` folder is **auto-generated at runtime**. Whenever the help
loader encounters a malformed chapter file (missing frontmatter, duplicate
order, broken page break, etc.), it appends a JSONL record to a dated log file
under `log/`, for example `log/2026-07-03.jsonl`.

Each line is a JSON object with fields like:

```json
{"ts": "2026-07-03T14:22:01Z", "level": "error", "file": "en/faq.md", "reason": "missing frontmatter"}
```

### Maintenance reminders

- **Check `log/` regularly** during development — silent loader failures mean
  broken help pages for users.
- **Clean up old logs**: the folder is not pruned automatically. Delete or
  archive `log/*.jsonl` files older than your retention window.
- **Do not commit log files** to git — they are runtime artifacts. The folder
  is gitignored by default.
- If you see repeated errors for the same file, fix the source `.md` file
  rather than deleting the log.

---

## 9. `translation-status.json`

This file is **auto-generated** by the loader whenever it scans the help
folder. It reports translation coverage across locales:

```json
{
  "generated_at": "2026-07-03T14:22:01Z",
  "base_locale": "en",
  "locales": {
    "en": {"chapters": 9, "missing": 0, "outdated": 0},
    "zh-cn": {"chapters": 9, "missing": 0, "outdated": 0}
  }
}
```

- `missing` — chapters present in `en/` but absent in this locale.
- `outdated` — chapters whose `order` differs from the English original
  (signals a structural drift that needs manual sync).

**Do not edit this file by hand.** It is regenerated on every scan. Treat it
as a build artifact, not a source of truth. If it shows missing chapters,
create the corresponding `.md` files in the affected locale folder.

---

## 10. Verification

After editing any chapter file, run:

```powershell
python -m compileall i18n
python run.py --check-config
```

For a focused check that all chapters parse and all locales are in sync, the
loader exposes a verification hook — consult the loader module in
`i18n/loader.py` for the current entry point. A clean run produces no entries
in `log/` for the current date.

If a chapter renders incorrectly in Telegram, first check the corresponding
`log/*.jsonl` for parse errors, then verify the frontmatter and page-break
syntax against §3 and §4 of this guide.
