# Security Policy

## Supported Versions

Telegodex is in active `0.x` development. Security fixes target the latest commit on the default branch unless a release branch is explicitly maintained.

## Reporting a Vulnerability

Please do not open public issues for vulnerabilities involving bot tokens, API keys, local file access, command execution, approval bypass, or private chat data.

Report privately by contacting the repository owner through GitHub. Include:

- affected commit or version
- reproduction steps
- expected impact
- any relevant logs with secrets redacted

## Secret Handling

Never commit real values for:

- `TELEGRAM_BOT_TOKEN`
- provider API keys
- `.env`
- `provider.toml`
- databases and logs

Use `.env.example` and `provider.toml.example` for public examples.