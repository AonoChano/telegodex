"""冒烟：bot.utils.rich_messages 的重试与降级行为。"""
import _bootstrap  # noqa: F401
import asyncio
import json
import sys
import time
from contextlib import asynccontextmanager
from unittest.mock import patch, MagicMock

import aiohttp

from bot.utils import rich_messages
from bot.utils.rich_messages import (
    _post_bot_method,
    close_shared_session,
    RETRY_DELAYS,
    RETRY_MAX_ATTEMPTS,
    RETRYABLE_EXCEPTIONS,
)


class FakeResponse:
    """根据传入的 payload 决定 json() 是返回 dict 还是抛异常。"""

    def __init__(self, payload):
        self._payload = payload

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
        ok, desc = await _post_bot_method("TOKEN", "test", {})
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
        return await _post_bot_method("TOKEN", "test", {})
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
        return await _post_bot_method("TOKEN", "test", {})
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
        ok, desc = await _post_bot_method("TOKEN", "test", {})
        return ok, fake.calls, desc
    ok, calls, desc = await with_fake_session(fake, case4)
    assert_eq("business-error", (ok, calls, desc),
              (False, 1, "Bad Request: chat not found"))

    # 5) 非可重试异常（ValueError）：不重试
    fake = FakeSession([ValueError("not a network error")])
    async def case5():
        ok, desc = await _post_bot_method("TOKEN", "test", {})
        return ok, fake.calls
    ok, calls = await with_fake_session(fake, case5)
    assert_eq("non-retryable", (ok, calls), (False, 1))

    # 6) JSONDecodeError：可重试
    errs = [json.JSONDecodeError("empty body", "", 0), {"ok": True}]
    fake = FakeSession(errs)
    async def case6():
        ok, desc = await _post_bot_method("TOKEN", "test", {})
        return ok, fake.calls
    ok, calls = await with_fake_session(fake, case6)
    assert_eq("json-decode-retry", (ok, calls), (True, 2))

    # 7) 退避序列
    assert_eq("backoff-seq", RETRY_DELAYS, [1, 2, 2, 3, 5, 8, 13, 20, 20, 20])

    # 8) 可重试异常集
    assert aiohttp.ClientError in RETRYABLE_EXCEPTIONS
    assert asyncio.TimeoutError in RETRYABLE_EXCEPTIONS
    assert ConnectionError in RETRYABLE_EXCEPTIONS
    assert json.JSONDecodeError in RETRYABLE_EXCEPTIONS
    assert ValueError not in RETRYABLE_EXCEPTIONS
    print("OK   retryable-set")

    # 9) 关闭共享 session 正确清理全局状态
    await close_shared_session()
    rich_messages._shared_session = FakeSession([{"ok": True}])
    fake_in_use = rich_messages._shared_session
    await close_shared_session()
    assert_eq("close-shared-state", (rich_messages._shared_session, fake_in_use.closed), (None, True))

    print("ALL RETRY SMOKE OK")


if __name__ == "__main__":
    asyncio.run(main())
