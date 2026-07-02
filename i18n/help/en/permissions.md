---
title: "🔒 Permission Modes"
order: 6
---

# Permission Modes

Permission modes control how much autonomy the AI has when it wants to run
commands or call external tools. They apply to the Codex bridge and to any
tool-using provider.

---

## The Three Modes

| Mode | Behavior |
|---|---|
| Chat only | AI never runs commands or uses tools |
| User confirm | AI proposes commands; you approve each one |
| Full access | AI runs commands directly, no prompt |

The default is **Chat only**, which is the safest. Raise it only when you
trust the task and the provider.

---

## Chat Only

In this mode the AI is a pure conversational partner. It can answer questions,
write code in messages, and explain things, but it cannot execute anything on
your behalf. Use this for everyday chat, research, and drafting.

---

## User Confirm

The AI may propose to run a command (for example, listing files or applying a
diff). Telegodex shows you the exact command and waits. You tap **✅ Confirm**
to let it run, or **❌ Cancel** to refuse. Nothing executes without your
explicit approval.

This is the recommended mode for agentic work where you want oversight.

---

## Full Access

The AI executes commands immediately without asking. This is fastest but also
riskiest — a misunderstood instruction can still run unchallenged.

Reserve full access for sandboxed environments or trusted automation. Never
enable it on a server with sensitive data unless you accept that risk.

---

## Switching Modes

Open `/settings` → tap the **Permission** row. The current mode is shown on
the button label. Cycle to the next mode by tapping it. The change applies
immediately to the next turn.
