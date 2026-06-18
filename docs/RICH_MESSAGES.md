# Telegram Rich Messages

Telegodex sends assistant replies through Telegram Bot API `sendRichMessage`.
Streaming previews use `sendRichMessageDraft` when Telegram accepts them.

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

This uses `InputRichMessage.markdown`, so Telegram handles headings, lists,
task lists, tables, block quotes, footnotes, inline math, block math, code
blocks, spoilers, links, and nested formatting.

`sendRichMessage` payloads must keep Telegram routing fields from the incoming
message:

- `message_thread_id` for private threaded AI chats and forum topics
- `direct_messages_topic_id` for channel direct messages chats
- `business_connection_id` when Telegram sends the message through a business connection

Dropping those fields can make a response appear in the wrong Telegram surface.
When replying through aiogram's `Message.answer()` or `Message.reply()`, use
`TelegramRoute.send_kwargs()`; it intentionally omits `message_thread_id`
because aiogram already carries the topic for those helper methods. Draft APIs
and direct bot sends must pass the thread id explicitly.

## Streaming Drafts

`sendRichMessageDraft` streams a temporary rich preview while the model generates
text. Telegram expires the preview after about 30 seconds, so the handler must
still send the complete response with `sendRichMessage`.

Draft APIs accept `chat_id`, `message_thread_id`, `draft_id`, and content. They
do not accept every field that final send methods accept. Keep final-message
routing separate from draft routing.

## Quotes And Collapsible Blocks

Rich Markdown keeps the normal block quote form:

```markdown
> Quoted text
>
> Continued quoted text
```

Use block quotes only for quoted material or callouts. Do not use them as
generic indentation.

For long citations, logs, source dumps, or optional details, use Rich Markdown's
HTML-compatible details block:

```html
<details><summary>Full log</summary>

Hidden rich Markdown content.

</details>
```

Add the `open` attribute when the block should be expanded by default:

```html
<details open><summary>Summary</summary>
Expanded by default.
</details>
```

Use `||spoiler||` for short single-line reveals. The MarkdownV2 fallback path
still knows how to convert legacy `<blockquote expandable>...</blockquote>`
markup into Telegram's MarkdownV2 expandable quote syntax. Do not prefer that
markup for new Rich Message output unless Telegram documents it for Rich
Markdown.

## Monospace And Code

Inline backticks create inline fixed-width code:

```markdown
Use `python run.py --check-config`.
```

Fenced code blocks create pre-formatted fixed-width blocks and should include a
language tag when known:

````markdown
```python
print("Hello")
```
````

## Math

Use Telegram Rich Markdown math delimiters:

````markdown
Inline: $x^2 + y^2$

Block:
$$\int_0^1 x^2 dx = \frac{1}{3}$$

```math
\int_0^1 x^2 dx = \frac{1}{3}
```
````

The handler normalizes common model output from `\(...\)` to `$...$` and from
`\[...\]` to `$$...$$`. It does not replace LaTeX commands with Unicode on the
Rich Message path because Telegram treats formula source as raw LaTeX.

## Fallback

If `sendRichMessage` fails, the bot falls back to the existing MarkdownV2
formatter and sends the response with `parse_mode="MarkdownV2"`.

## Prompt Contract

The system prompt should advertise Rich Markdown features only when replies are
sent through `InputRichMessage.markdown`. Do not reintroduce local
Markdown-to-block conversion for tables or math unless it preserves all
surrounding prose and inline content.
