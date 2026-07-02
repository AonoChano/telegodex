---
title: "📝 Markdown & Rich Messages"
order: 7
---

# Markdown & Rich Messages

Telegodex renders replies using Telegram's native Rich Message API. That
means the AI's Markdown output — tables, code blocks, formulas — shows up
cleanly in chat, not as escaped source text.

This chapter itself is rendered through the same pipeline, so every example
below is a live preview of how the syntax will look in your chat.

---

## Syntax Reference

The table below shows each element side by side: the syntax on the left,
the rendered preview on the right.

| Element | Syntax | Preview |
|---|---|---|
| Heading | `# Title` | (renders as heading above) |
| Bold | `**bold**` | **bold** |
| Italic | `*italic*` | *italic* |
| Inline code | `` `code` `` | `code` |
| Link | `[text](url)` | [Telegodex](https://github.com/) |
| Block quote | `> quote` | > quote |
| LaTeX inline | `$a^2+b^2$` | $a^2+b^2$ |

---

## Code Blocks

Fenced code blocks preserve formatting and syntax labels. Live preview:

```python
def greet(name: str) -> str:
    return f"Hello, {name}!"
```

```powershell
Get-ChildItem -Path . -Filter *.py | Measure-Object
```

Use them when sharing code — inline backticks are for short identifiers only.

---

## Tables

Tables render as real Telegram tables with aligned columns. Always include
a header row followed by the `|---|` separator. Live preview:

| Name | Score | Rank |
|---|---|---|
| Alpha | 12 | 🥇 |
| Beta | 9 | 🥈 |
| Gamma | 5 | 🥉 |

The pipe characters and the separator row are required; without them the
lines render as plain text.

---

## LaTeX

Math formulas render as Telegram native formulas, not as plain text. Use
`$...$` for inline math and `$$...$$` for display math.

Inline preview: the famous identity $E = mc^2$ appears here as a real
formula, not as the literal characters E, =, m, c, 2.

Block preview:

$$\int_0^1 x^2 \, dx = \frac{1}{3}$$

Do not substitute Unicode characters (like ² or √) — let LaTeX handle it
so the rendering stays crisp at every font size.

---

## Lists

Both unordered and ordered lists render natively:

- Unordered item one
- Unordered item two
  - Nested sub-item
- Unordered item three

1. First step
2. Second step
3. Third step

Use lists for steps, options, or any sequence — they keep Telegram
formatting clean where commas would feel cramped.
