from bot.handlers.provider_errors import (
    format_provider_error,
    is_terminal_provider_error,
    provider_error_message,
    provider_error_status_code,
)


class ProviderError(Exception):
    def __init__(self, message: str = "provider failed", *, status_code=None, body=None, response=None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body
        self.response = response


class Response:
    def __init__(self, status_code: int):
        self.status_code = status_code


def test_provider_error_status_code_prefers_exception_attribute():
    exc = ProviderError(status_code=429, response=Response(500))

    assert provider_error_status_code(exc) == 429
    assert is_terminal_provider_error(exc) is True


def test_provider_error_status_code_falls_back_to_response():
    exc = ProviderError(response=Response(403))

    assert provider_error_status_code(exc) == 403
    assert is_terminal_provider_error(exc) is True


def test_provider_error_message_reads_nested_body_error():
    exc = ProviderError(body={"error": {"message": "insufficient balance"}})

    assert provider_error_message(exc) == "insufficient balance"
    assert is_terminal_provider_error(exc) is True


def test_format_provider_error_includes_provider_and_status_hint():
    exc = ProviderError(status_code=402, body={"message": "insufficient balance"})

    text = format_provider_error(exc, "deepseek", "zh-cn")

    assert "余额或额度不足" in text
    assert "服务商: deepseek" in text
    assert "HTTP 状态码: 402" in text


def test_non_terminal_provider_error_uses_generic_hint():
    exc = ProviderError("temporary upstream failure")

    assert is_terminal_provider_error(exc) is False
    assert "稍后重试" in format_provider_error(exc, "zhipu", "zh-cn")
