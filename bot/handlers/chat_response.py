"""Provider response generation for normal chat handlers."""

from __future__ import annotations

import time
from dataclasses import dataclass

from aiogram.types import Message
from loguru import logger

from ai import Message as AIMessage
from ai.token_usage import TokenUsage, estimate_chat_usage, token_usage_from_provider_usage
from bot.handlers.chat_runtime import ChatRuntimeSelection
from bot.handlers.chat_tool_requests import looks_like_chat_tool_request_prefix
from bot.handlers.provider_errors import format_provider_error, is_terminal_provider_error
from bot.telegram_draft import DraftStream
from bot.utils.latex import normalize_rich_markdown_latex
from bot.utils.routing import TelegramRoute

# 流式 draft 触发字符阈值：积攒 N 字符再推送一次。Telegram 官方文档没有公开
# draft 的更新频率上限，参考 telegramify-markdown 的 DraftStream 实践，64 字符
# 是一个在"动画流畅"和"不刷屏"之间的折中。
DRAFT_FLUSH_CHARS = 64
# 流式 draft 触发最长时间：超过 N 秒强制推送一次（兜底）
DRAFT_FLUSH_INTERVAL = 1.5
# 单次草稿内容上限：sendMessageDraft 文本最大 4096 字符
DRAFT_MAX_CHARS = 4000
# 同一次响应内对**同一 draft_id** 的最大推送次数。超过后停止草稿，攒到
# sendRichMessage 持久化时一次性发出。30 秒预览窗口 + 反滥用保护实测上
# 6 次左右开始出现 raised/拒绝。
DRAFT_MAX_CALLS_PER_ID = 6
# 响应总字符数低于此值时跳过草稿阶段，直接 sendRichMessage 持久化。短回复
# 频繁推草稿不划算（看起来在闪、实则在等）。
DRAFT_MIN_RESPONSE_CHARS = 80


@dataclass(frozen=True)
class ChatProviderResponse:
    text: str
    model: str | None
    tokens: int | None
    usage: TokenUsage | None = None


async def push_draft(stream: DraftStream | None, text: str) -> None:
    """Wrapper around DraftStream.push with empty-text guard."""
    if stream is None or not text:
        return
    await stream.push(text)


async def generate_chat_provider_response(
    *,
    message: Message,
    route: TelegramRoute,
    messages_with_system: list[AIMessage],
    runtime: ChatRuntimeSelection,
    stream: DraftStream | None,
    locale: str | None = None,
) -> ChatProviderResponse | None:
    """Generate one normal-chat provider response, including stream fallback."""
    provider_name = runtime.provider_name
    provider = runtime.provider
    model_name = runtime.model_name
    temperature = runtime.temperature
    max_output_tokens = runtime.max_output_tokens

    response_text = ""
    response_model = model_name
    usage: TokenUsage | None = None
    stream_used = False

    if runtime.streaming:
        try:
            buffer = ""
            last_flush = time.monotonic()
            if stream is not None:
                await stream.push("💭 …", force_plain=True)

            async for chunk in provider.chat_stream(
                messages=messages_with_system,
                model=model_name,
                temperature=temperature,
                max_tokens=max_output_tokens,
            ):
                if not chunk:
                    continue
                stream_used = True
                response_text += chunk
                buffer += chunk
                now = time.monotonic()
                if len(buffer) >= DRAFT_FLUSH_CHARS or (now - last_flush) >= DRAFT_FLUSH_INTERVAL:
                    if len(response_text) >= DRAFT_MIN_RESPONSE_CHARS and not looks_like_chat_tool_request_prefix(
                        response_text
                    ):
                        await push_draft(
                            stream,
                            normalize_rich_markdown_latex(response_text[-DRAFT_MAX_CHARS:]),
                        )
                    buffer = ""
                    last_flush = now

            if stream_used:
                usage = estimate_chat_usage(messages_with_system, response_text, model=response_model)
            if (
                stream_used
                and stream is not None
                and response_text
                and len(response_text) >= DRAFT_MIN_RESPONSE_CHARS
                and not looks_like_chat_tool_request_prefix(response_text)
            ):
                await push_draft(
                    stream,
                    normalize_rich_markdown_latex(response_text[-DRAFT_MAX_CHARS:]),
                )
        except Exception as stream_err:
            if is_terminal_provider_error(stream_err):
                logger.warning(
                    f"流式 chat_stream 遇到终止性服务商错误，不再回退非流式: {type(stream_err).__name__}: {stream_err}"
                )
                await message.answer(
                    format_provider_error(stream_err, provider_name, locale),
                    **route.send_kwargs(),
                )
                return None
            logger.warning(f"流式 chat_stream 失败，回退非流式: {type(stream_err).__name__}: {stream_err}")
            stream_used = False
            response_text = ""
            usage = None

    if not stream_used:
        try:
            response = await provider.chat(
                messages=messages_with_system,
                model=model_name,
                temperature=temperature,
                max_tokens=max_output_tokens,
            )
        except Exception as chat_err:
            logger.error(f"非流式 provider.chat 失败: {type(chat_err).__name__}: {chat_err}")
            await message.answer(
                format_provider_error(chat_err, provider_name, locale),
                **route.send_kwargs(),
            )
            return None
        response_text = response.content
        response_model = response.model
        usage = token_usage_from_provider_usage(response.usage) or estimate_chat_usage(
            messages_with_system,
            response_text,
            model=response_model,
        )
        if (
            stream is not None
            and response_text
            and len(response_text) >= DRAFT_MIN_RESPONSE_CHARS
            and not looks_like_chat_tool_request_prefix(response_text)
        ):
            await push_draft(
                stream,
                normalize_rich_markdown_latex(response_text[-DRAFT_MAX_CHARS:]),
            )

    return ChatProviderResponse(
        text=normalize_rich_markdown_latex(response_text),
        model=response_model,
        tokens=usage.total_tokens if usage else None,
        usage=usage,
    )
