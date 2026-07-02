"""Provider error classification for normal chat handlers."""

from i18n import tr

TERMINAL_PROVIDER_STATUS_CODES = {401, 402, 403, 429}
TERMINAL_PROVIDER_ERROR_MARKERS = (
    "insufficient balance",
    "payment required",
    "quota",
    "rate limit",
    "rolling spend limit",
    "unauthorized",
    "invalid api key",
    "forbidden",
    "余额",
    "额度",
    "限额",
    "使用人数较多",
)


def provider_error_status_code(exc: Exception) -> int | None:
    """Extract an HTTP-like status code from provider SDK exceptions."""
    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int):
        return status_code
    response = getattr(exc, "response", None)
    response_status = getattr(response, "status_code", None)
    if isinstance(response_status, int):
        return response_status
    return None


def provider_error_message(exc: Exception) -> str:
    """Extract a concise provider error message without requiring provider SDK imports."""
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])
        if body.get("message"):
            return str(body["message"])
    return str(exc)


def is_terminal_provider_error(exc: Exception) -> bool:
    """Return whether retrying the same provider request immediately is wasteful."""
    status_code = provider_error_status_code(exc)
    if status_code in TERMINAL_PROVIDER_STATUS_CODES:
        return True
    message = provider_error_message(exc).lower()
    return any(marker in message for marker in TERMINAL_PROVIDER_ERROR_MARKERS)


def format_provider_error(exc: Exception, provider_name: str, locale: str | None = None) -> str:
    """Build a user-facing provider error without exposing raw SDK payloads."""
    status_code = provider_error_status_code(exc)
    message = provider_error_message(exc).lower()

    if status_code == 402 or "insufficient balance" in message or "余额" in message:
        hint = tr("bot.provider_errors.hint_insufficient_balance", locale)
    elif status_code == 429 or "rate limit" in message or "quota" in message or "限额" in message:
        hint = tr("bot.provider_errors.hint_rate_limit", locale)
    elif status_code in {401, 403} or "unauthorized" in message or "forbidden" in message:
        hint = tr("bot.provider_errors.hint_auth_failed", locale)
    else:
        hint = tr("bot.provider_errors.hint_generic", locale)

    status_line = tr("bot.provider_errors.status_line", locale, status_code=status_code) if status_code is not None else ""
    return tr("bot.provider_errors.main", locale, hint=hint, provider=provider_name, status_line=status_line)
