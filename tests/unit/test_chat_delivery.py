from unittest.mock import AsyncMock

import pytest

from bot.handlers import chat_delivery


class FakeRoute:
    chat_id = 100
    message_thread_id = 200
    direct_messages_topic_id = None
    business_connection_id = None

    def send_kwargs(self):
        return {"message_thread_id": self.message_thread_id}


@pytest.mark.asyncio
async def test_deliver_chat_response_uses_rich_message(monkeypatch):
    message = type("MessageStub", (), {"answer": AsyncMock()})()
    send_rich = AsyncMock(return_value=True)
    monkeypatch.setattr(chat_delivery, "send_rich_message", send_rich)

    await chat_delivery.deliver_chat_response(
        message=message,
        route=FakeRoute(),
        bot_token="TOKEN",
        stream=None,
        response_text="hello",
    )

    send_rich.assert_awaited_once()
    message.answer.assert_not_awaited()


@pytest.mark.asyncio
async def test_deliver_chat_response_falls_back_to_markdown(monkeypatch):
    message = type("MessageStub", (), {"answer": AsyncMock()})()
    monkeypatch.setattr(chat_delivery, "send_rich_message", AsyncMock(return_value=False))

    await chat_delivery.deliver_chat_response(
        message=message,
        route=FakeRoute(),
        bot_token="TOKEN",
        stream=None,
        response_text="hello",
    )

    message.answer.assert_awaited_once()
    assert message.answer.await_args.kwargs["parse_mode"] == "MarkdownV2"


@pytest.mark.asyncio
async def test_deliver_chat_response_falls_back_to_plain_text_on_failure(monkeypatch):
    message = type("MessageStub", (), {"answer": AsyncMock()})()
    send_rich = AsyncMock(side_effect=RuntimeError("boom"))
    monkeypatch.setattr(chat_delivery, "send_rich_message", send_rich)

    await chat_delivery.deliver_chat_response(
        message=message,
        route=FakeRoute(),
        bot_token="TOKEN",
        stream=None,
        response_text="hello",
    )

    message.answer.assert_awaited_once_with("hello", message_thread_id=200)
