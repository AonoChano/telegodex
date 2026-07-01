# Startup And Polling

Run Telegodex with:

```bash
python run.py
```

Check configuration without starting polling:

```bash
python run.py --check-config
```

## Required: `provider.toml`

Telegodex reads all AI provider configuration from `provider.toml`. The bot will not start without it. If the file is missing, `--check-config` and the polling startup both abort with an error pointing at `provider.toml.example`:

```text
provider.toml is required; see provider.toml.example (expected at: .../provider.toml)
```

To set up:

```bash
cp provider.toml.example provider.toml
# then edit provider.toml and .env (add the *_API_KEY env vars referenced by api_key_env)
```

See `docs/CUSTOM_PROVIDERS.md` for the full configuration guide.

## `--check-config` Behavior

`--check-config` loads `provider.toml` and validates:

- The file exists and parses as valid TOML.
- `[global].available_providers` is non-empty (an empty list activates nothing — every provider must be explicitly listed).
- `[global].default_provider` is in `available_providers`.

It does NOT validate API keys — those are resolved lazily at request time, so a missing `*_API_KEY` env var will skip the provider with a warning at startup but will not fail `--check-config`.

On success, the check prints the list of parsed provider blocks (e.g. `openai, anthropic, gemini, ...`).

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

The banner version is read from `pyproject.toml`. If the project version changes, the startup banner should change with it.

## Polling Reconnect Status

When Telegram polling loses connectivity, Telegodex renders one in-place terminal status line instead of repeating full tracebacks.

- `retry in X.Xs` means aiogram is in backoff before the next `getUpdates` request.
- `retrying` or `retrying X.Xs` means the next `getUpdates` request has started and has not returned yet.

The polling loop uses `polling_timeout=10` and an aiogram HTTP session timeout of 8 seconds. Aiogram combines these into the request timeout for `getUpdates`, so a broken network should fail in roughly 18 seconds plus the configured backoff instead of appearing stuck for a long system-level timeout.

## Telegram Startup Checks

When the bot starts the real polling process, Telegodex performs Telegram-side startup checks before accepting updates:

- It calls `setMyCommands` to sync the Telegram command menu with the commands implemented by the codebase. Users should not need to edit the command menu manually in BotFather after every project change.
- It calls `getMe` and checks `has_topics_enabled`. If Telegram reports that private-chat Threaded Mode is not enabled, Telegodex logs a warning and sends a private message to configured admins.

The Threaded Mode warning is non-fatal. The bot still starts so ordinary chat, forum groups, and debugging remain possible.

This check is specifically for Telegram private AI chatbot topics. Forum supergroup topics are a separate Telegram feature and still require a forum group with Topics enabled plus suitable bot admin permissions.
