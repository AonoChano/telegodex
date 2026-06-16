"""Stream coalescer: merges high-frequency text deltas to avoid Telegram rate limits."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger


class StreamCoalescer:
    """合并高频文本增量，避免触发 Telegram 编辑频率限制（≤1 次/秒）。

    当满足以下任一条件时，触发 ``on_batch`` 回调发射当前累积的完整文本：

    * 自上次发射以来的增量长度达到 ``max_chars``
    * 增量长度达到 ``min_chars`` 且以句子结束符结尾（``sentence_break=True``）
    * 自上次 ``push`` 后超过 ``idle_ms`` 毫秒（idle timeout）
    * 显式调用 ``flush()`` 或 ``close()``

    同时，两次发射之间强制间隔至少 1 秒，以遵守 Telegram 速率限制。
    """

    _SENTENCE_ENDINGS = (". ", "! ", "? ", ".\n", "!\n", "?\n", "\n\n", "… ", "。")

    def __init__(
        self,
        *,
        min_chars: int = 32,
        max_chars: int = 400,
        idle_ms: int = 1000,
        sentence_break: bool = True,
        on_batch: Callable[[str], Awaitable[None]] | None = None,
    ) -> None:
        self.min_chars = min_chars
        self.max_chars = max_chars
        self.idle_ms = idle_ms
        self.sentence_break = sentence_break
        self.on_batch = on_batch

        self._accumulated = ""
        self._buffer = ""
        self._idle_task: asyncio.Task[None] | None = None
        self._last_flush_time = 0.0
        self._closed = False
        self._buffer_lock = asyncio.Lock()
        self._flush_lock = asyncio.Lock()

    async def push(self, delta: str) -> None:
        """推送文本增量。满足 flush 条件时触发 ``on_batch(accumulated_text)``。"""
        if self._closed:
            return

        should_flush = False
        async with self._buffer_lock:
            self._accumulated += delta
            self._buffer += delta
            buf_len = len(self._buffer)

            if buf_len >= self.max_chars:
                should_flush = True
            elif buf_len >= self.min_chars and self.sentence_break:
                if any(self._buffer.endswith(end) for end in self._SENTENCE_ENDINGS):
                    should_flush = True

        if self._idle_task is not None and not self._idle_task.done():
            self._idle_task.cancel()

        if should_flush:
            await self._flush()
        else:
            self._idle_task = asyncio.create_task(self._idle_wait())

    async def _idle_wait(self) -> None:
        try:
            await asyncio.sleep(self.idle_ms / 1000.0)
            await self._flush()
        except asyncio.CancelledError:
            pass

    async def _flush(self) -> None:
        async with self._flush_lock:
            batch = ""
            async with self._buffer_lock:
                if not self._buffer or self._closed:
                    return
                batch = self._accumulated
                self._buffer = ""

            # Rate limit: max 1 edit per second
            now = time.monotonic()
            target_time = self._last_flush_time + 1.0
            if now < target_time:
                await asyncio.sleep(target_time - now)

            self._last_flush_time = time.monotonic()

            if self.on_batch is not None:
                try:
                    await self.on_batch(batch)
                except Exception as exc:
                    logger.debug(f"StreamCoalescer on_batch failed: {exc}")

    async def flush(self) -> None:
        """强制刷新，发射当前累积的完整文本。"""
        if self._idle_task is not None and not self._idle_task.done():
            self._idle_task.cancel()
        await self._flush()

    async def close(self) -> None:
        """关闭 coalescer，flush 剩余内容并不再接受新增量。"""
        self._closed = True
        if self._idle_task is not None and not self._idle_task.done():
            self._idle_task.cancel()
        await self._flush()
