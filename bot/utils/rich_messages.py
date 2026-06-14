"""
Telegram Rich Messages API helpers.

Bot API 10.1 introduced InputRichMessage.markdown, so rich Markdown should be
sent to Telegram directly instead of being partially converted locally.
"""

from __future__ import annotations

from typing import Any, Dict

import aiohttp
from loguru import logger


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
