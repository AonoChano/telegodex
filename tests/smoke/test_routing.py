"""Smoke tests for Telegram native AI routing helpers."""

import _bootstrap  # noqa: F401
import sys

from aiogram.types import Message

from bot.utils.routing import TelegramRoute


def assert_eq(name, got, want):
    if got != want:
        print(f"FAIL {name}: got {got!r}, want {want!r}")
        sys.exit(1)
    print(f"OK   {name}")


threaded = Message.model_validate(
    {
        "message_id": 1,
        "date": 0,
        "chat": {"id": 123, "type": "private"},
        "message_thread_id": 987,
        "business_connection_id": "biz-1",
    }
)
route = TelegramRoute.from_message(threaded)
assert_eq("thread-chat", route.chat_id, 123)
assert_eq("thread-storage", route.storage_thread_id, 987)
assert_eq(
    "thread-send-kwargs",
    route.send_kwargs(),
    {"business_connection_id": "biz-1", "message_thread_id": 987},
)
assert_eq("thread-draft", route.draft_thread_id(), 987)


direct = Message.model_validate(
    {
        "message_id": 2,
        "date": 0,
        "chat": {"id": -100123, "type": "private"},
        "direct_messages_topic": {"topic_id": 555},
    }
)
route = TelegramRoute.from_message(direct)
assert_eq("direct-topic", route.direct_messages_topic_id, 555)
assert_eq("direct-storage", route.storage_thread_id, -555)
assert_eq(
    "direct-send-kwargs",
    route.send_kwargs(),
    {"direct_messages_topic_id": 555},
)
assert_eq("direct-draft", route.draft_thread_id(), None)


plain = Message.model_validate(
    {
        "message_id": 3,
        "date": 0,
        "chat": {"id": 123, "type": "private"},
    }
)
route = TelegramRoute.from_message(plain)
assert_eq("plain-storage", route.storage_thread_id, None)
assert_eq("plain-send-kwargs", route.send_kwargs(), {})

print("ALL ROUTING SMOKE OK")
