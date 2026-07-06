## Summary

<!-- What changed and why? -->

## Verification

- [ ] `python -m compileall main.py run.py ai bot storage security`
- [ ] `python -m pytest`
- [ ] `python run.py --check-config`

## Safety

- [ ] No secrets, tokens, local databases, logs, or local provider configs are committed.
- [ ] Telegram replies preserve thread/topic routing where applicable.
- [ ] User-facing text uses i18n keys when new text is introduced.