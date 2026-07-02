"""Provider error classification for normal chat handlers."""

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


def format_provider_error(exc: Exception, provider_name: str) -> str:
    """Build a user-facing provider error without exposing raw SDK payloads."""
    status_code = provider_error_status_code(exc)
    message = provider_error_message(exc).lower()

    if status_code == 402 or "insufficient balance" in message or "余额" in message:
        hint = "当前 AI 服务商返回余额或额度不足。请充值、更换服务商，或稍后再试。"
    elif status_code == 429 or "rate limit" in message or "quota" in message or "限额" in message:
        hint = "当前 AI 服务商触发了频率或额度限制。请稍后再试，或切换到其他服务商。"
    elif status_code in {401, 403} or "unauthorized" in message or "forbidden" in message:
        hint = "当前 AI 服务商拒绝了请求。请检查 API Key、账号权限、余额或中转站额度。"
    else:
        hint = "AI 服务商请求失败。请稍后重试，或切换到其他服务商。"

    status_line = f"\nHTTP 状态码: {status_code}" if status_code is not None else ""
    return f"❌ AI 服务商请求失败\n\n{hint}\n\n服务商: {provider_name}{status_line}"
