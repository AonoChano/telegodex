# Telegram Rich Messages

Telegodex sends assistant replies through Telegram Bot API `sendRichMessage`.

## Transport

Assistant output is passed directly as Rich Markdown:

```json
{
  "chat_id": 123456,
  "rich_message": {
    "markdown": "## Title\n\n| A | B |\n|---|---|\n| 1 | 2 |"
  }
}
```

This uses `InputRichMessage.markdown`, so Telegram handles parsing for headings, lists, task lists, tables, block quotes, footnotes, inline math, block math, code blocks, spoilers, links, and nested formatting.

## Quotes And Collapsible Blocks

Rich Markdown keeps the normal block quote form:

```markdown
> Quoted text
>
> Continued quoted text
```

Use block quotes only for actual quoted material or callouts. Do not use them as generic indentation.

For long citations, source dumps, or anything readers will want to scan past, use the Telegram-native **expandable block quote** (Bot API 7.3+):

```html
<blockquote expandable>
First three lines are visible by default; the rest unfolds when the
user taps the block. Use this for source citations, log dumps, optional
reference material, or long quoted passages.
</blockquote>
```

The body is rendered as a regular block quote when expanded. Cannot be nested inside another block quote, and cannot contain other block quotes. The MarkdownV2 fallback path converts `<blockquote expandable>…</blockquote>` to `**>…` + last line `||` (the MarkdownV2 form of an expandable block quote).

For collapsible content that should look like a foldable panel with a custom title (e.g. "Click for full log"), use Rich Markdown's HTML-compatible details block:

```html
<details><summary>Summary</summary>

Hidden rich Markdown content.

</details>
```

Add the `open` attribute when the block should be expanded by default:

```html
<details open><summary>Summary</summary>
Expanded by default.
</details>
```

Pick the right "hidden until tapped" affordance for the content. `<details>` and `<blockquote expandable>` are not interchangeable: `<blockquote expandable>` is for quoted material without a custom title; `<details>` is for non-quote content with a custom title. Use `||spoiler||` for short single-line reveals.

## Monospace And Code

Inline backticks create inline fixed-width code:

```markdown
Use `python run.py --check-config`.
```

Fenced code blocks create pre-formatted fixed-width blocks and should include a language tag when known:

````markdown
```python
print("Hello")
```
````

## Fallback

If `sendRichMessage` fails, the bot falls back to the existing MarkdownV2 formatter and sends the response with `parse_mode="MarkdownV2"`.

## Prompt Contract

The system prompt should advertise Rich Markdown features only when replies are sent through `InputRichMessage.markdown`. Do not reintroduce local Markdown-to-block conversion for tables or math unless it preserves all surrounding prose and inline content.
