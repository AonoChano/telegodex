"""
Telegram Rich Messages API helpers.

Bot API 10.1 introduced InputRichMessage.markdown, so rich Markdown should be
sent to Telegram directly instead of being partially converted locally.

The module also exposes ephemeral draft helpers (``sendRichMessageDraft`` /
``sendMessageDraft``) used to stream partial content while the AI is still
generating. Both endpoints are private-chat / forum-topic only and require a
non-zero ``draft_id``; the draft is a temporary 30-second preview that must
be finalized with ``sendRichMessage`` / ``sendMessage``.
"""

from __future__ import annotations

import asyncio
import itertools
import json
import threading
from typing import Any, Dict

import aiohttp
from loguru import logger

# 自定义 loguru 级别：用于"重试中"状态。
# - 优先级 35（介于 WARNING=30 和 ERROR=40 之间），保证默认 logger 收得到
#   但仍比 ERROR 温和
# - 灰色 + ↻ 图标：首次失败时跳红 ERROR，重试中显示灰 ↻，不刷屏
logger.level("RETRY", no=35, color="<light-black>", icon="↻")

# 网络抖动的退避策略。10 次重试，总等待 ~96 秒。
# 序列：[1, 2, 2, 3, 5, 8, 13, 20, 20, 20] —— 前段快响（典型瞬时抖动），
# 后段封顶 20s（已经丢包的连接继续等没有意义）。
RETRY_DELAYS: list[float] = [1, 2, 2, 3, 5, 8, 13, 20, 20, 20]
RETRY_MAX_ATTEMPTS: int = len(RETRY_DELAYS)

# 可重试的异常。aiohttp.ClientError 覆盖了连接失败 / 读超时 / 服务器 5xx
# 等大多数"网络层面"问题；asyncio.TimeoutError 单独再列一次以兼容 3.10；
# json.JSONDecodeError 处理"网关返回了空 body / 半截 HTML"这种
# 代理层异常；ConnectionError 兜底原生 socket 错误。
RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    aiohttp.ClientError,
    asyncio.TimeoutError,
    ConnectionError,
    json.JSONDecodeError,
)

# 共享的 aiohttp ClientSession。每个 _post_bot_method 调用都 new 一次 session
# 是常见反模式：流式响应里推 20+ 次草稿 = 20+ 个 session 内部创建/销毁 Proactor
# pipe transport，bot 关闭时残留 transport 在 __del__ 里尝试通过已关闭的事件
# 循环清理 -> 'Event loop is closed' 异常。
# 共享 session 还顺带把 TCP 连接、TLS 握手、连接池都复用掉，省掉每次冷启动
# 30-50ms 的开销。
_shared_session: aiohttp.ClientSession | None = None
_shared_session_lock = threading.Lock()


def _get_shared_session() -> aiohttp.ClientSession:
    """懒加载共享 session。线程安全（即使 event loop 关闭后被调用也不会崩）。"""
    global _shared_session
    if _shared_session is None or _shared_session.closed:
        with _shared_session_lock:
            if _shared_session is None or _shared_session.closed:
                _shared_session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=15),
                )
    return _shared_session


async def close_shared_session() -> None:
    """在 bot shutdown 时显式关闭共享 session。

    必须在事件循环还活着时调用（main.py 的 finally 链）。调用后再访问会
    触发懒加载重建，行为正确。
    """
    global _shared_session
    with _shared_session_lock:
        if _shared_session is not None and not _shared_session.closed:
            try:
                await _shared_session.close()
            except Exception as e:
                logger.warning(
                    f"close_shared_session raised {type(e).__name__}: {e!r}"
                )
        _shared_session = None

# 进程内单调递增的 draft_id 序列。Telegram 只要求"非零 + 同 id 视为同草稿"
# 所以单计数器足够，溢出时折叠到 1。
_draft_lock = threading.Lock()
_draft_counter = itertools.count(1)


def build_rich_markdown_payload(
    chat_id: int | str,
    markdown_text: str,
    *,
    is_rtl: bool | None = None,
    skip_entity_detection: bool | None = None,
    message_thread_id: int | None = None,
) -> Dict[str, Any]:
    """Build a sendRichMessage payload using InputRichMessage.markdown."""
    rich_message: Dict[str, Any] = {"markdown": markdown_text}

    if is_rtl is not None:
        rich_message["is_rtl"] = is_rtl
    if skip_entity_detection is not None:
        rich_message["skip_entity_detection"] = skip_entity_detection

    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "rich_message": rich_message,
    }
    if message_thread_id is not None:
        payload["message_thread_id"] = message_thread_id
    return payload


async def send_rich_message(
    bot_token: str,
    chat_id: int | str,
    markdown_text: str,
    *,
    is_rtl: bool | None = None,
    skip_entity_detection: bool | None = None,
    message_thread_id: int | None = None,
) -> bool:
    """
    Send Markdown through Telegram's Rich Messages API.

    Returns True on success. Callers should fall back to MarkdownV2/plain text
    when Telegram rejects the rich message.
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendRichMessage"
    payload = build_rich_markdown_payload(
        chat_id,
        markdown_text,
        is_rtl=is_rtl,
        skip_entity_detection=skip_entity_detection,
        message_thread_id=message_thread_id,
    )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                result = await resp.json()

        if result.get("ok"):
            logger.info(f"Rich Message sent successfully: chat_id={chat_id}")
            return True

        error_desc = result.get("description", "Unknown error")
        logger.warning(f"Rich Message send failed: {error_desc}")
        return False

    except aiohttp.ClientError as e:
        logger.error(f"Rich Message API request failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Rich Message send raised an exception: {e}")
        return False


# ---------------------------------------------------------------------------
# Draft helpers (sendRichMessageDraft / sendMessageDraft)
# ---------------------------------------------------------------------------


def new_draft_id() -> int:
    """
    生成非零的 draft_id。

    Telegram 要求 draft_id 必须非零，且同一 draft_id 重复调用会被动画替换。
    进程内单调计数器即可保证唯一性；溢出时折叠到 1（同一个 bot 进程产生
    2^31 次草稿才会触发，实际不可能）。
    """
    with _draft_lock:
        val = next(_draft_counter)
    return val if 0 < val <= 0x7FFFFFFF else (val & 0x7FFFFFFF) or 1


async def _post_bot_method(
    bot_token: str, method: str, payload: Dict[str, Any]
) -> tuple[bool, str]:
    """
    共用底层：调一次 Telegram Bot API 并返回 ``(ok, description)``。

    网络层异常走 :data:`RETRY_DELAYS` 退避序列。日志策略：

    - **第一次失败** → 红 ERROR，标 type(e)
    - **重试 1..N** → 灰 ↻ RETRY，单行 ``[NN/10] in Ns — reason``
    - **中途恢复** → 绿 SUCCESS，标已重试次数
    - **10 次都失败** → 红 ERROR，标"permanently failed"

    非网络异常（4xx 业务错误 / JSON 结构错误）不重试。
    """
    url = f"https://api.telegram.org/bot{bot_token}/{method}"
    last_exc: BaseException | None = None
    first_failure_logged = False

    for attempt in range(RETRY_MAX_ATTEMPTS + 1):
        if attempt > 0:
            delay = RETRY_DELAYS[attempt - 1]
            reason = (
                f"{type(last_exc).__name__}: {last_exc}"
                if last_exc is not None
                else "unknown"
            )
            logger.log(
                "RETRY",
                f"{method} retry [{attempt:02d}/{RETRY_MAX_ATTEMPTS:02d}] "
                f"in {delay:>2}s — {reason}",
            )
            await asyncio.sleep(delay)

        try:
            session = _get_shared_session()
            async with session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                result = await resp.json()
        except RETRYABLE_EXCEPTIONS as e:
            last_exc = e
            if not first_failure_logged:
                # 首次失败：跳红，让运维立刻看到
                logger.error(
                    f"{method} network error: {type(e).__name__}: {e!r} "
                    f"(will backoff up to {RETRY_MAX_ATTEMPTS} times)"
                )
                first_failure_logged = True
            continue
        except Exception as e:
            # 非可重试异常：原样上报，不消耗重试预算
            logger.error(f"{method} raised {type(e).__name__}: {e!r}")
            return False, f"{type(e).__name__}: {e}"

        if result.get("ok"):
            if first_failure_logged:
                logger.success(
                    f"{method} recovered after {attempt} "
                    f"{'retry' if attempt == 1 else 'retries'}"
                )
            return True, ""
        # 业务层错误（4xx）不重试
        return False, result.get("description", "Unknown error")

    # 走到这里说明 RETRY_MAX_ATTEMPTS+1 次全部因网络异常失败
    logger.error(
        f"{method} permanently failed after {RETRY_MAX_ATTEMPTS} retries: "
        f"{type(last_exc).__name__ if last_exc else 'Unknown'}: {last_exc!r}"
    )
    return False, f"NetworkError: {type(last_exc).__name__ if last_exc else 'Unknown'}: {last_exc}"


async def send_rich_message_draft(
    bot_token: str,
    chat_id: int | str,
    markdown_text: str,
    draft_id: int,
    *,
    message_thread_id: int | None = None,
    is_rtl: bool | None = None,
    skip_entity_detection: bool | None = None,
) -> bool:
    """
    调用 ``sendRichMessageDraft`` 发送流式预览。

    仅 private chat + forum topic 场景可用；草稿是 30 秒临时预览，必须用
    ``sendRichMessage`` 持久化收尾。
    """
    if draft_id == 0:
        raise ValueError("draft_id must be non-zero")

    rich_message: Dict[str, Any] = {"markdown": markdown_text}
    if is_rtl is not None:
        rich_message["is_rtl"] = is_rtl
    if skip_entity_detection is not None:
        rich_message["skip_entity_detection"] = skip_entity_detection

    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "draft_id": draft_id,
        "rich_message": rich_message,
    }
    if message_thread_id is not None:
        payload["message_thread_id"] = message_thread_id

    ok, desc = await _post_bot_method(bot_token, "sendRichMessageDraft", payload)
    if ok:
        logger.debug(
            f"Rich draft ok: chat_id={chat_id} thread={message_thread_id} "
            f"draft_id={draft_id} bytes={len(markdown_text)}"
        )
    else:
        logger.warning(f"Rich draft failed: {desc}")
    return ok


async def send_message_draft(
    bot_token: str,
    chat_id: int | str,
    text: str,
    draft_id: int,
    *,
    message_thread_id: int | None = None,
) -> bool:
    """
    回退路径：调 ``sendMessageDraft`` 发送纯文本草稿（无 Rich 解析能力）。
    """
    if draft_id == 0:
        raise ValueError("draft_id must be non-zero")

    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "draft_id": draft_id,
        "text": text,
    }
    if message_thread_id is not None:
        payload["message_thread_id"] = message_thread_id

    ok, desc = await _post_bot_method(bot_token, "sendMessageDraft", payload)
    if not ok:
        logger.warning(f"Plain draft failed: {desc}")
    return ok


def has_rich_features(markdown_text: str) -> bool:
    """
    Rich Markdown is now the primary response transport.

    Keep this compatibility helper for older imports; any non-empty AI response
    can be sent through InputRichMessage.markdown.
    """
    return bool(markdown_text.strip())


class MarkdownToRichMessage:
    """
    Backwards-compatible wrapper for old local conversion call sites.

    New code should send Markdown directly with send_rich_message().
    """

    @staticmethod
    def convert(markdown_text: str) -> Dict[str, Any]:
        return {"markdown": markdown_text}


class RichMessageBuilder:
    """Compatibility shim for old imports."""

    @staticmethod
    def create_markdown(markdown_text: str) -> Dict[str, Any]:
        return {"markdown": markdown_text}
