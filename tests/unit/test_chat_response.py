from unittest.mock import AsyncMock

import pytest

from ai import MessageRole
from ai.base import AIResponse, Message
from bot.handlers.chat_response import generate_chat_provider_response
from bot.handlers.chat_runtime import ChatRuntimeSelection


class FakeRoute:
    def send_kwargs(self):
        return {}


class FakeProvider:
    def __init__(self, *, stream_error: Exception | None = None):
        self.stream_error = stream_error
        self.chat_calls = 0

    async def chat_stream(self, **kwargs):
        if self.stream_error is not None:
            raise self.stream_error
        yield "streamed"

    async def chat(self, **kwargs):
        self.chat_calls += 1
        return AIResponse(content="fallback response", model="fallback-model", usage={"total_tokens": 7})


def _runtime(provider: FakeProvider, *, streaming: bool = True) -> ChatRuntimeSelection:
    return ChatRuntimeSelection(
        provider_name="fake",
        provider=provider,
        model_name="fake-model",
        temperature=0.2,
        streaming=streaming,
        max_output_tokens=123,
    )


@pytest.mark.asyncio
async def test_generate_chat_provider_response_falls_back_after_stream_error():
    provider = FakeProvider(stream_error=RuntimeError("temporary stream failure"))
    message = type("MessageStub", (), {"answer": AsyncMock()})()

    result = await generate_chat_provider_response(
        message=message,
        route=FakeRoute(),
        messages_with_system=[Message(role=MessageRole.USER, content="hello")],
        runtime=_runtime(provider),
        stream=None,
        locale="zh-cn",
    )

    assert result is not None
    assert result.text == "fallback response"
    assert result.model == "fallback-model"
    assert result.tokens == 7
    assert result.usage is not None
    assert result.usage.total_tokens == 7
    assert result.usage.estimated is False
    assert provider.chat_calls == 1
    message.answer.assert_not_awaited()


@pytest.mark.asyncio
async def test_generate_chat_provider_response_stops_on_terminal_stream_error():
    err = RuntimeError("insufficient balance")
    provider = FakeProvider(stream_error=err)
    message = type("MessageStub", (), {"answer": AsyncMock()})()

    result = await generate_chat_provider_response(
        message=message,
        route=FakeRoute(),
        messages_with_system=[Message(role=MessageRole.USER, content="hello")],
        runtime=_runtime(provider),
        stream=None,
        locale="zh-cn",
    )

    assert result is None
    assert provider.chat_calls == 0
    message.answer.assert_awaited_once()
    assert "余额或额度不足" in message.answer.await_args.args[0]
