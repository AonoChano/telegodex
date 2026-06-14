# Startup And Polling

Run Telegodex with:

```bash
python run.py
```

Check configuration without starting polling:

```bash
python run.py --check-config
```

## Single Polling Instance

Telegram allows only one active `getUpdates` polling consumer per bot token. If two processes use the same token, Telegram returns:

```text
Conflict: terminated by other getUpdates request; make sure that only one bot instance is running
```

Telegodex creates a local lock file under `logs/telegodex_<bot_id>.lock` before starting polling. This prevents duplicate local processes from the same workspace.

The lock cannot stop another copy running in a different folder, on another machine, in a container, or on a hosting service. If the conflict still appears, stop the other bot process that uses the same `TELEGRAM_BOT_TOKEN`.

## Startup Banner

`run.py` prints a closed box banner with Telegram blue/white ANSI styling. The GitHub label uses an OSC 8 terminal hyperlink:

```text
github.com/AonoChano/telegodex
```

Terminals that support OSC 8 make the label clickable. Terminals that do not support it still show the plain text URL.
