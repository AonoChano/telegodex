---
id: task-001
title: Add streaming response support (EXAMPLE)
status: planned
priority: medium
created: 2026-06-14
updated: 2026-06-14
assigned: future-ai-assistant
estimated_effort: 1d
related_files:
  - bot/handlers/messages.py
  - ai/base.py
  - ai/openai_provider.py
tags: [feature, streaming, telegram, example]
blocks: []
blocked_by: []
---

## Description

**This is an EXAMPLE task file** demonstrating the YAML+MD format for task management.

Implement streaming response to show typing indicator and progressive message updates in Telegram, improving UX for long AI responses.

## Context

Current implementation waits for the full AI response before sending to the user. Streaming would:
- Show typing indicator during generation
- Display progressive updates (typing effect)
- Improve perceived responsiveness
- Better user experience for long responses

## Acceptance Criteria

- [ ] Extend `BaseAIProvider` with streaming support
- [ ] Implement `chat_stream()` in all provider classes
- [ ] Update message handlers to detect and use streaming
- [ ] Show typing indicator: `bot.send_chat_action("typing")`
- [ ] Batch small chunks to avoid Telegram rate limits (max 1 edit/sec)
- [ ] Handle stream interruption gracefully (timeout, errors)
- [ ] Update documentation in `docs/ARCHITECTURE.md`
- [ ] Test with OpenAI, Anthropic, and DeepSeek providers

## Technical Notes

### aiogram 3.x Streaming Pattern

```python
# Show typing indicator
await message.bot.send_chat_action(message.chat.id, "typing")

# Send initial message
sent = await message.answer("...")

# Progressive updates
buffer = ""
async for chunk in provider.chat_stream(messages):
    buffer += chunk
    if len(buffer) > 50:  # Batch threshold
        await sent.edit_text(buffer)
        buffer = ""
        await asyncio.sleep(1)  # Rate limit protection

# Final update
if buffer:
    await sent.edit_text(buffer)
```

### Provider Implementation

OpenAI AsyncOpenAI already has streaming:
```python
stream = await self.client.chat.completions.create(..., stream=True)
async for chunk in stream:
    if chunk.choices[0].delta.content:
        yield chunk.choices[0].delta.content
```

Anthropic also supports streaming via AsyncAnthropic.

### Edge Cases

1. **Markdown parsing errors during streaming**: Need to validate before each edit
2. **Telegram rate limits**: Max 30 messages/sec, 1 edit/sec per message
3. **Stream timeout**: Add timeout protection (default 60s)
4. **User sends new message**: Cancel current stream

## Progress Log

### 2026-06-14 16:00
- Created example task file
- Researched aiogram 3.x streaming patterns
- Identified rate limit constraints

## Related Issues

- None (this is an example task)

## References

- [aiogram docs - send_chat_action](https://docs.aiogram.dev/en/latest/)
- [OpenAI Streaming](https://platform.openai.com/docs/api-reference/streaming)
- [Anthropic Streaming](https://docs.anthropic.com/en/api/streaming)

---

**Note**: When this task is completed, rename file to `[Closed] task-001-example-streaming.md` and update `status: completed`.
