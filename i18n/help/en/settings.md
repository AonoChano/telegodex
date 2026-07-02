---
title: "⚙️ Settings"
order: 7
---

# Settings

The settings menu is the control panel for everything Telegodex does. Open it
with `/settings` or the **⚙️ Settings** button.

---

## Menu Items

| Item | What it does |
|---|---|
| 🤖 Switch AI provider | Choose between OpenAI, Anthropic, Google, custom |
| 🎯 Select model | Pick a model from the active provider |
| 🌡️ Adjust temperature | Set creativity from 0.2 to 1.3 |
| Permission | Cycle through permission modes |
| 🌐 Language | Change the bot UI language |
| 📊 View usage statistics | Inspect message counters (when available) |
| « Close | Shut the settings panel |

Each item opens its own submenu. Use **« Back** to return.

---

## Switching Provider

Tap **🤖 Switch AI provider** to see the list of configured providers. The
active one is marked with ✅. Tapping another provider switches immediately
and confirms with a callback toast.

---

## Selecting a Model

Inside **🎯 Select model**, you see every model the active provider exposes.
Pick the one that fits the task — bigger context for long threads, smaller
models for speed.

---

## Adjusting Temperature

The temperature slider shows the current value. Lower values keep replies
focused and repeatable; higher values make them more varied. Tap to step
through presets or enter a value directly.

---

## Language

**🌐 Language** opens the locale selector. Help pages, button labels, and
bot replies all switch to the chosen language. English is the fallback when a
translation key is missing.

---

## Closing Settings

Tap **« Close** to dismiss the panel. Your changes are saved automatically —
there is no separate "save" button.
