---
title: "❓ FAQ & Tips"
order: 8
---

# FAQ & Tips

Common questions and a few practical habits that make Telegodex nicer to use.

---

## Q: How do I switch AI provider?

Open `/settings`, tap **🤖 Switch AI provider**, and pick one from the list.
The switch applies to the next message you send. Each forum topic remembers
its own provider, so switching in one topic does not affect others.

---

## Q: How do I start a new conversation?

Send `/new`. The current thread's context is dropped from the AI's view
(older messages are still reachable via `/history`). Use this whenever the
topic changes and you do not want old context confusing the model.

---

## Q: Why is the bot not responding?

Check, in order:

1. Is the bot running? Ask an admin or check the server.
2. Is a provider configured? Run `/start` to see the status table.
3. Did you hit a rate limit? Wait a minute and try again.
4. Is the message empty or too long? Telegram rejects both.

If none of these apply, the issue is likely upstream at the provider.

---

## Q: How do I change the UI language?

Send `/language` or open **⚙️ Settings → 🌐 Language**. Pick a locale from
the list. The bot interface and help pages switch immediately. English is
always available as a fallback.

---

## Q: What are permission modes?

Permission modes decide whether the AI may run commands on your behalf. The
default is **Chat only** (no execution). See the **🔒 Permission Modes**
chapter for the full breakdown.

---

## Tips

- Use `/new` for fresh context — it is faster than `/clear` and keeps history.
- Browse `/history` to recover a thread you accidentally left.
- Lower temperature for code and facts; raise it for brainstorming.
- In forums, each topic is isolated — organize parallel tasks that way.
- If a reply looks truncated, the stream may still be running; wait a moment.
