---
title: "💬 Conversations"
order: 4
---

# Conversations

Telegodex keeps full conversation context so the AI remembers what was said
earlier in the same thread. You do not need to re-paste background every turn.

---

## Multi-Turn Context

Every reply you send is stored alongside the AI's response. On the next
message, Telegodex feeds the entire thread back to the provider so it can
answer with continuity — references to "it" or "the previous code" just work.

Context is per-thread: separate forum topics keep separate histories.

---

## Starting Fresh

Use `/new` to begin a new conversation. The previous thread is saved into
history but no longer sent to the AI. This is the right command when you
switch topics or want a clean slate.

`/clear` is more aggressive: it wipes the current conversation entirely
without saving a snapshot. Use it when you want to forget everything.

---

## Browsing History

`/history` opens a paginated view of past conversations. You can scroll
through older messages and reopen any thread.

| Button | Action |
|---|---|
| ⏮️ | Jump to first page |
| ⬅️ | Previous page |
| ➡️ | Next page |
| ⏭️ | Jump to last page |

The current page number is shown between the arrows.

---

## Thread Isolation

Inside forum topics, each topic acts as an independent conversation. A
message posted in topic A never leaks into topic B's context, even if both
use the same provider. This makes forums the natural place to organize
parallel discussions.
