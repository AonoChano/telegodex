---
title: "📝 Markdown & Rich Messages"
order: 6
---

# Markdown & Rich Messages

Telegodex renders replies using Telegram's native Rich Message API. That
means the AI's Markdown output — tables, code blocks, formulas — shows up
cleanly in chat, not as escaped source text.

---

## Supported Syntax

| Element | Syntax |
|---|---|
| Heading | `#`, `##`, `###` |
| Bold | `**text**` |
| Italic | `*text*` |
| Inline code | `` `code` `` |
| Code block | <code>```lang ... ```</code> |
| Table | `\| col \| col \|` |
| Link | `[text](url)` |
| Block quote | `> quote` |
| LaTeX (inline) | `$a^2 + b^2$` |
| LaTeX (block) | `$$E = mc^2$$` |

---

## Code Blocks

Fenced code blocks keep their formatting and syntax labels:

```python
def greet(name: str) -> str:
    return f"Hello, {name}!"
```

Use them when sharing code — inline backticks are for short identifiers only.

---

## Tables

Tables render as real Telegram tables with columns aligned. Always include a
header row followed by the `|---|` separator:

```markdown
| Name | Score |
|---|---|
| Alpha | 12 |
| Beta  | 9  |
```

---

## LaTeX

Math formulas are rendered as Telegram native formulas, not as plain text.
Use `$...$` for inline math and `$$...$$` for display math. Do not substitute
Unicode characters (like ² or √) — let LaTeX handle it so the rendering stays
crisp at every font size.
