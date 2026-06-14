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

import itertools
import threading
from typing import Any, Dict

import aiohttp
from loguru import logger

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
    """共用底层：调一次 Telegram Bot API 并返回 (ok, description)。"""
    url = f"https://api.telegram.org/bot{bot_token}/{method}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                result = await resp.json()
    except aiohttp.ClientError as e:
        logger.error(f"{method} request failed: {type(e).__name__}: {e!r}")
        return False, str(e) or type(e).__name__
    except Exception as e:
        # 用 type+repr 记录，避免 str(e) 为空时丢失关键信息
        logger.error(f"{method} raised {type(e).__name__}: {e!r}")
        return False, f"{type(e).__name__}: {e}"

    if result.get("ok"):
        return True, ""
    return False, result.get("description", "Unknown error")


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
