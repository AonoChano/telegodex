"""冒烟：bot.utils.rich_messages 的重试与降级行为。"""
import asyncio
import json
import sys
import time
from unittest.mock import MagicMock

import _bootstrap  # noqa: F401
import aiohttp

from bot.utils import rich_messages
from bot.utils.rich_messages import (
    RETRY_DELAYS,
    RETRY_MAX_ATTEMPTS,
    RETRYABLE_EXCEPTIONS,
    _post_bot_method,
    close_shared_session,
)


class FakeResponse:
    """根据传入的 payload 决定 json() 是返回 dict 还是抛异常。"""

    def __init__(self, payload, status=None):
        self._payload = payload
        self.status = status

    async def json(self):
        if isinstance(self._payload, BaseException):
            raise self._payload
        return self._payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class FakeSession:
    """最小可配置的 aiohttp session 替身。复用为 _shared_session。

    queue: 每次调用 session.post 弹出一个元素：
        - dict  : 视为成功响应（payload）
        - Exception 实例 : 视为抛出该异常
    """

    def __init__(self, queue):
        self.queue = queue
        self.calls = 0
        self.closed = False

    def post(self, *a, **kw):
        self.calls += 1
        item = self.queue.pop(0)
        if isinstance(item, tuple):
            payload, status = item
            return FakeResponse(payload, status=status)
        return FakeResponse(item)

    async def close(self):
        self.closed = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


def assert_eq(name, got, want):
    if got != want:
        print(f"FAIL {name}: got {got!r}, want {want!r}")
        sys.exit(1)
    print(f"OK   {name}")


async def with_fake_session(fake, fn):
    """把 fake 注入成 rich_messages 的 _shared_session，调用 fn，最后还原。

    关键：每次注入前 await close_shared_session() 清掉上次残留。
    """
    await close_shared_session()
    rich_messages._shared_session = fake
    try:
        return await fn()
    finally:
        await close_shared_session()
        rich_messages._shared_session = None


async def main():
    # 1) 单次成功：不重试
    fake = FakeSession([{"ok": True}])
    async def case1():
        ok, desc, _ = await _post_bot_method("TOKEN", "test", {})
        return ok, fake.calls, desc
    ok, calls, desc = await with_fake_session(fake, case1)
    assert_eq("immediate-success", (ok, calls, desc), (True, 1, ""))

    # 2) 3 次网络抖动后恢复：第 4 次成功
    errs = [
        aiohttp.ClientConnectorError(MagicMock(), OSError("conn refused")),
        aiohttp.ServerDisconnectedError(),
        aiohttp.ClientPayloadError("payload error"),
        {"ok": True},
    ]
    fake = FakeSession(errs)
    t0 = time.monotonic()
    async def case2():
        ok, desc, _ = await _post_bot_method("TOKEN", "test", {})
        return ok, desc
    ok, desc = await with_fake_session(fake, case2)
    elapsed = time.monotonic() - t0
    expected_delay = sum(RETRY_DELAYS[:3])  # 1 + 2 + 2
    assert_eq("recover-after-3", (ok, fake.calls, desc), (True, 4, ""))
    assert_eq("recover-elapsed", int(elapsed), expected_delay)

    # 3) 全部网络失败
    errs = [
        aiohttp.ClientConnectorError(MagicMock(), OSError("conn refused"))
    ] * (RETRY_MAX_ATTEMPTS + 1)
    fake = FakeSession(errs)
    t0 = time.monotonic()
    async def case3():
        ok, desc, _ = await _post_bot_method("TOKEN", "test", {})
        return ok, desc
    ok, desc = await with_fake_session(fake, case3)
    elapsed = time.monotonic() - t0
    total_delay = sum(RETRY_DELAYS)
    assert_eq("all-fail", (ok, fake.calls), (False, RETRY_MAX_ATTEMPTS + 1))
    assert_eq("all-fail-elapsed", int(elapsed), total_delay)
    assert "NetworkError" in desc, f"description should be NetworkError, got {desc!r}"
    assert "ClientConnectorError" in desc

    # 4) 业务错误 4xx：不重试
    fake = FakeSession([{"ok": False, "description": "Bad Request: chat not found"}])
    async def case4():
        ok, desc, _ = await _post_bot_method("TOKEN", "test", {})
        return ok, fake.calls, desc
    ok, calls, desc = await with_fake_session(fake, case4)
    assert_eq("business-error", (ok, calls, desc),
              (False, 1, "Bad Request: chat not found"))

    # 5) 非可重试异常（ValueError）：不重试
    fake = FakeSession([ValueError("not a network error")])
    async def case5():
        ok, desc, _ = await _post_bot_method("TOKEN", "test", {})
        return ok, fake.calls
    ok, calls = await with_fake_session(fake, case5)
    assert_eq("non-retryable", (ok, calls), (False, 1))

    # 6) JSONDecodeError：不再可重试（请求可能已成功，重试会重复消息）
    fake = FakeSession([json.JSONDecodeError("empty body", "", 0)])
    async def case6():
        ok, desc, _ = await _post_bot_method("TOKEN", "test", {})
        return ok, fake.calls, desc
    ok, calls, desc = await with_fake_session(fake, case6)
    assert_eq("json-decode-no-retry", (ok, calls), (False, 1))
    assert "JSONDecodeError" in desc, f"description should mention JSONDecodeError, got {desc!r}"

    # 6b) 非幂等消息方法 JSONDecodeError：视为可能已送达，避免 fallback 重复发送
    fake = FakeSession([json.JSONDecodeError("empty body", "", 0)])
    async def case6b():
        ok, desc, _ = await _post_bot_method("TOKEN", "sendRichMessage", {})
        return ok, fake.calls, desc
    ok, calls, desc = await with_fake_session(fake, case6b)
    assert_eq("json-decode-rich-message-ambiguous-ok", (ok, calls), (True, 1))
    assert "JSONDecodeError" in desc

    # 6c) 2xx JSONDecodeError：Bot API 已返回成功状态但 body 损坏，也不触发重发
    fake = FakeSession([(json.JSONDecodeError("empty body", "", 0), 200)])
    async def case6c():
        ok, desc, _ = await _post_bot_method("TOKEN", "test", {})
        return ok, fake.calls, desc
    ok, calls, desc = await with_fake_session(fake, case6c)
    assert_eq("json-decode-2xx-ok", (ok, calls), (True, 1))
    assert "JSONDecodeError" in desc

    # 6d) 草稿方法 JSONDecodeError：同一 draft_id 替换语义下也不需要 fallback 复制
    fake = FakeSession([json.JSONDecodeError("empty body", "", 0)])
    async def case6d():
        ok, desc, _ = await _post_bot_method("TOKEN", "sendRichMessageDraft", {})
        return ok, fake.calls, desc
    ok, calls, desc = await with_fake_session(fake, case6d)
    assert_eq("json-decode-draft-ambiguous-ok", (ok, calls), (True, 1))
    assert "JSONDecodeError" in desc

    # 7) 退避序列
    assert_eq("backoff-seq", RETRY_DELAYS, [1, 2, 2, 3, 5, 8, 13, 20, 20, 20])

    # 8) 可重试异常集
    assert aiohttp.ClientError in RETRYABLE_EXCEPTIONS
    assert asyncio.TimeoutError in RETRYABLE_EXCEPTIONS
    assert ConnectionError in RETRYABLE_EXCEPTIONS
    assert json.JSONDecodeError not in RETRYABLE_EXCEPTIONS
    assert ValueError not in RETRYABLE_EXCEPTIONS
    print("OK   retryable-set")

    # 9) 关闭共享 session 正确清理全局状态
    await close_shared_session()
    rich_messages._shared_session = FakeSession([{"ok": True}])
    fake_in_use = rich_messages._shared_session
    await close_shared_session()
    assert_eq("close-shared-state", (rich_messages._shared_session, fake_in_use.closed), (None, True))

    # 10) 非幂等方法网络异常不重试（sendMessage 不会重复调用）
    errs = [
        aiohttp.ClientConnectorError(MagicMock(), OSError("conn refused")),
        {"ok": True},
    ]
    fake = FakeSession(errs)
    t0 = time.monotonic()
    async def case10():
        ok, desc, _ = await _post_bot_method("TOKEN", "sendMessage", {})
        return ok
    ok = await with_fake_session(fake, case10)
    elapsed = time.monotonic() - t0
    assert_eq("non-idempotent-no-retry", (ok, fake.calls), (False, 1))
    assert_eq("non-idempotent-no-delay", int(elapsed), 0)

    # 11) 幂等方法（sendRichMessageDraft）仍享受重试
    errs = [
        aiohttp.ClientConnectorError(MagicMock(), OSError("conn refused")),
        {"ok": True},
    ]
    fake = FakeSession(errs)
    t0 = time.monotonic()
    async def case11():
        ok, desc, _ = await _post_bot_method("TOKEN", "sendRichMessageDraft", {})
        return ok
    ok = await with_fake_session(fake, case11)
    elapsed = time.monotonic() - t0
    assert_eq("idempotent-draft-retry", (ok, fake.calls), (True, 2))
    assert_eq("idempotent-draft-delay", int(elapsed), RETRY_DELAYS[0])

    print("ALL RETRY SMOKE OK")


if __name__ == "__main__":
    asyncio.run(main())
