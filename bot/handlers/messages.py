import time

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from loguru import logger
from sqlalchemy import select

from ai import AIRouter, MessageRole
from ai import Message as AIMessage
from bot.keyboards import get_main_menu, get_settings_menu
from bot.telegram_draft import DraftStream
from bot.utils.latex import normalize_rich_markdown_latex
from bot.utils.markdown import format_markdown_v2
from bot.utils.rich_messages import send_rich_message
from bot.utils.routing import TelegramRoute
from config import settings
from core.session import SessionData, SessionKey, session_manager
from prompts import get_prompt_manager
from storage import ContextManager
from storage.models import Conversation

router = Router()

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
TERMINAL_PROVIDER_STATUS_CODES = {401, 402, 403, 429}
TERMINAL_PROVIDER_ERROR_MARKERS = (
    "insufficient balance",
    "payment required",
    "quota",
    "rate limit",
    "rolling spend limit",
    "unauthorized",
    "invalid api key",
    "forbidden",
    "余额",
    "额度",
    "限额",
    "使用人数较多",
)


async def _push_draft(stream: DraftStream | None, text: str) -> None:
    """Wrapper around DraftStream.push with empty-text guard."""
    if stream is None or not text:
        return
    await stream.push(text)


def escape_markdown(text: str) -> str:
    """转义 Telegram MarkdownV2 特殊字符（用于 Bot 自身消息）"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def _provider_error_status_code(exc: Exception) -> int | None:
    """Extract an HTTP-like status code from provider SDK exceptions."""
    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int):
        return status_code
    response = getattr(exc, "response", None)
    response_status = getattr(response, "status_code", None)
    if isinstance(response_status, int):
        return response_status
    return None


def _provider_error_message(exc: Exception) -> str:
    """Extract a concise provider error message without requiring provider SDK imports."""
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])
        if body.get("message"):
            return str(body["message"])
    return str(exc)


def _is_terminal_provider_error(exc: Exception) -> bool:
    """Return whether retrying the same provider request immediately is wasteful."""
    status_code = _provider_error_status_code(exc)
    if status_code in TERMINAL_PROVIDER_STATUS_CODES:
        return True
    message = _provider_error_message(exc).lower()
    return any(marker in message for marker in TERMINAL_PROVIDER_ERROR_MARKERS)


def _format_provider_error(exc: Exception, provider_name: str) -> str:
    """Build a user-facing provider error without exposing raw SDK payloads."""
    status_code = _provider_error_status_code(exc)
    message = _provider_error_message(exc).lower()

    if status_code == 402 or "insufficient balance" in message or "余额" in message:
        hint = "当前 AI 服务商返回余额或额度不足。请充值、更换服务商，或稍后再试。"
    elif status_code == 429 or "rate limit" in message or "quota" in message or "限额" in message:
        hint = "当前 AI 服务商触发了频率或额度限制。请稍后再试，或切换到其他服务商。"
    elif status_code in {401, 403} or "unauthorized" in message or "forbidden" in message:
        hint = "当前 AI 服务商拒绝了请求。请检查 API Key、账号权限、余额或中转站额度。"
    else:
        hint = "AI 服务商请求失败。请稍后重试，或切换到其他服务商。"

    status_line = f"\nHTTP 状态码: {status_code}" if status_code is not None else ""
    return f"❌ AI 服务商请求失败\n\n{hint}\n\n服务商: {provider_name}{status_line}"


@router.message(Command("start"))
async def cmd_start(message: Message, context_manager: ContextManager, ai_router: AIRouter):
    """处理 /start 命令"""
    user = message.from_user
    route = TelegramRoute.from_message(message)

    # 创建或更新用户
    await context_manager.get_or_create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code,
    )

    user_name = escape_markdown(user.first_name or 'User')
    providers = []
    if ai_router.is_provider_available('openai'):
        providers.append('• ✅ OpenAI \\(GPT\\)')
    if ai_router.is_provider_available('anthropic'):
        providers.append('• ✅ Anthropic \\(Claude\\)')
    if ai_router.is_provider_available('google'):
        providers.append('• ✅ Google \\(Gemini\\)')
    for provider_name in ai_router.list_available_providers():
        if provider_name.lower() not in {"openai", "anthropic", "google"}:
            providers.append(f"• ✅ {escape_markdown(provider_name)}")

    providers_text = '\n'.join(providers) if providers else '• ⚠️ 无可用服务商'

    welcome_text = f"""👋 欢迎使用 **Telegodex**\\!

你好，{user_name}\\!

我是一个多 AI 服务商的智能助手，支持：
{providers_text}

发送任何消息开始对话，或使用菜单按钮\\!

📌 快速命令：
/new \\- 开始新对话
/settings \\- 设置
/help \\- 帮助
"""

    await message.answer(
        welcome_text,
        parse_mode="MarkdownV2",
        reply_markup=get_main_menu(),
        **route.send_kwargs(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """处理 /help 命令"""
    route = TelegramRoute.from_message(message)
    help_text = """📖 **帮助文档**

**基本命令：**
/start \\- 启动机器人
/new \\- 开始新对话
/clear \\- 清空当前对话
/settings \\- 打开设置
/help \\- 显示帮助

**功能说明：**
• 直接发送消息即可与 AI 对话
• 支持多轮对话，自动保存上下文
• 可在设置中切换不同的 AI 服务商
• 支持完整的 Markdown 格式

**Markdown 示例：**
\\*斜体\\* \\- *斜体*
\\*\\*粗体\\*\\* \\- **粗体**
\\[链接\\]\\(url\\) \\- [链接](https://example.com)
\\`代码\\` \\- `代码`
"""

    await message.answer(help_text, parse_mode="MarkdownV2", **route.send_kwargs())


@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    """Open the settings menu."""
    route = TelegramRoute.from_message(message)
    await message.answer(
        "Settings",
        reply_markup=get_settings_menu(),
        **route.send_kwargs(),
    )


@router.message(Command("new"))
async def cmd_new(message: Message, context_manager: ContextManager):
    """开始新对话"""
    user_id = message.from_user.id
    route = TelegramRoute.from_message(message)
    thread_id = route.storage_thread_id

    # 创建新对话（按 topic 隔离）
    await context_manager.create_new_conversation(
        user_id, thread_id=thread_id, chat_id=route.chat_id
    )

    await message.answer(
        "✅ 已开始新对话\\!",
        parse_mode="MarkdownV2",
        **route.send_kwargs(),
    )


@router.message(Command("clear"))
async def cmd_clear(message: Message, context_manager: ContextManager):
    """清空当前对话"""
    user_id = message.from_user.id
    route = TelegramRoute.from_message(message)
    thread_id = route.storage_thread_id

    conversation = await context_manager.get_or_create_conversation(
        user_id, thread_id=thread_id, chat_id=route.chat_id
    )

    await context_manager.clear_conversation(conversation.id)

    await message.answer(
        "🗑️ 当前对话历史已清空\\!",
        parse_mode="MarkdownV2",
        **route.send_kwargs(),
    )


async def _load_session_data(
    conversation: Conversation,
    session_key: SessionKey,
) -> SessionData:
    """Load ``SessionData`` from *conversation* or memory."""
    data = session_manager.get_session_data(session_key)
    if data is None:
        data = SessionData.from_dict(conversation.provider_sessions)
        session_manager.set_session_data(session_key, data)
    return data


async def _save_session_data(
    conversation: Conversation,
    session_key: SessionKey,
) -> None:
    """Persist ``SessionData`` back to *conversation*."""
    data = session_manager.get_session_data(session_key)
    if data is not None:
        conversation.provider_sessions = data.to_dict()


async def _resolve_provider_conversation(
    context_manager: ContextManager,
    session_key: SessionKey,
    session_data: SessionData,
    user_id: int,
    thread_id: int | None,
    provider_name: str,
) -> Conversation:
    """Return the conversation for *provider_name*, creating one if needed.

    Uses the provider bucket ``session_id`` when available so that switching
    providers never loses context.
    """
    bucket = session_data.get_or_create_bucket(provider_name)

    if bucket.session_id:
        stmt = select(Conversation).where(Conversation.id == int(bucket.session_id))
        result = await context_manager.session.execute(stmt)
        conv = result.scalar_one_or_none()
        if conv is not None:
            if not conv.is_active:
                conv.is_active = True
            return conv

    # No bucket or stale session_id: create a fresh conversation.
    conv = await context_manager.create_new_conversation(
        user_id, thread_id=thread_id, chat_id=session_key.chat_id
    )
    bucket.session_id = str(conv.id)
    return conv


@router.message(Command("model"))
async def cmd_model(
    message: Message,
    context_manager: ContextManager,
    ai_router: AIRouter,
) -> None:
    """Switch AI provider without losing other provider context."""
    user_id = message.from_user.id
    route = TelegramRoute.from_message(message)
    thread_id = route.storage_thread_id
    session_key = SessionKey.from_telegram_message(route.chat_id, route.message_thread_id)

    prompt = message.text or ""
    if prompt.startswith("/model"):
        prompt = prompt[len("/model"):].strip()

    if not prompt:
        available = ai_router.list_available_providers()
        lines = ["**Usage:** `/model <provider>`", "", "**Available providers:**"]
        for name in available:
            lines.append(f"- `{name}`")
        await message.answer(
            "\n".join(lines),
            parse_mode="Markdown",
            **route.send_kwargs(),
        )
        return

    provider_name = prompt.lower()
    if not ai_router.is_provider_available(provider_name):
        await message.answer(
            f"❌ Unknown provider: `{provider_name}`",
            parse_mode="Markdown",
            **route.send_kwargs(),
        )
        return

    user = await context_manager.get_or_create_user(user_id)
    conversation = await context_manager.get_or_create_conversation(
        user_id, thread_id=thread_id, chat_id=route.chat_id
    )

    session_data = await _load_session_data(conversation, session_key)

    # Save current provider bucket before switching.
    if user.preferred_provider:
        old_bucket = session_data.get_or_create_bucket(user.preferred_provider)
        old_bucket.session_id = str(conversation.id)

    # Switch active provider.
    user.preferred_provider = provider_name
    session_manager.set_active_provider(session_key, provider_name)

    # Resolve or create the provider-specific conversation.
    provider_conv = await _resolve_provider_conversation(
        context_manager, session_key, session_data, user_id, thread_id, provider_name
    )

    await _save_session_data(provider_conv, session_key)
    await context_manager.session.commit()

    await message.answer(
        f"✅ Switched to `{provider_name}`\\.\n"
        f"_Messages in this thread are now isolated per provider\\._",
        parse_mode="MarkdownV2",
        **route.send_kwargs(),
    )


@router.message(F.text)
async def handle_message(message: Message, context_manager: ContextManager, ai_router: AIRouter):
    """处理普通文本消息"""
    user_id = message.from_user.id
    user_text = message.text
    route = TelegramRoute.from_message(message)
    thread_id = route.storage_thread_id

    # 输入验证和清理
    from security import sanitize_input
    user_text = sanitize_input(user_text, max_length=4000)

    if not user_text:
        await message.answer("⚠️ 消息内容为空或过长", **route.send_kwargs())
        return

    # 菜单按钮处理
    if user_text in ["💬 新对话", "📝 历史记录", "⚙️ 设置", "ℹ️ 帮助"]:
        if user_text == "💬 新对话":
            await cmd_new(message, context_manager)
            return
        if user_text == "⚙️ 设置":
            await cmd_settings(message)
            return
        if user_text == "ℹ️ 帮助":
            await cmd_help(message)
            return
        # TODO: 实现历史记录
        await message.answer("功能开发中...", **route.send_kwargs())
        return

    # 获取用户和对话（按 topic + provider 隔离）
    user = await context_manager.get_or_create_user(user_id)
    session_key = SessionKey.from_telegram_message(route.chat_id, route.message_thread_id)

    # Bootstrap session data from the current active conversation.
    base_conv = await context_manager.get_or_create_conversation(
        user_id, thread_id=thread_id, chat_id=route.chat_id
    )
    session_data = await _load_session_data(base_conv, session_key)

    provider_name = user.preferred_provider or "openai"
    provider = ai_router.get_provider(provider_name)
    if not provider:
        provider = ai_router.get_default_provider()

    if not provider:
        await message.answer(
            "❌ 没有可用的 AI 服务商，请检查配置",
            **route.send_kwargs(),
        )
        return

    # Resolve the provider-isolated conversation.
    conversation = await _resolve_provider_conversation(
        context_manager, session_key, session_data, user_id, thread_id, provider_name
    )

    # Ensure the base conversation also carries the latest session data.
    await _save_session_data(conversation, session_key)

    # 添加用户消息到历史
    await context_manager.add_message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=user_text
    )

    # 获取对话历史
    history = await context_manager.get_conversation_history(conversation.id)

    try:
        # 发送 "正在输入..." 状态
        await message.bot.send_chat_action(
            chat_id=route.chat_id,
            action="typing",
            message_thread_id=route.message_thread_id,
            business_connection_id=route.business_connection_id,
        )

        # 获取系统提示词（按 provider 分层组合）
        prompt_manager = get_prompt_manager()
        system_prompt = prompt_manager.get_system_prompt(
            provider=user.preferred_provider
        )

        # 构建包含系统提示词的消息历史
        messages_with_system = [
            AIMessage(role=MessageRole.SYSTEM, content=system_prompt)
        ] + history

        bot_token = settings.telegram_bot_token
        if hasattr(bot_token, 'get_secret_value'):
            bot_token = bot_token.get_secret_value()

        # 仅私有 chat 支持 draft API；其它场景（群组/频道）跳过预览
        use_draft = message.chat.type == "private"
        stream = DraftStream(
            bot_token=bot_token,
            chat_id=route.chat_id,
            message_thread_id=route.draft_thread_id(),
            direct_messages_topic_id=route.direct_messages_topic_id,
            business_connection_id=route.business_connection_id,
            use_rich=True,
            max_draft_calls=DRAFT_MAX_CALLS_PER_ID,
        ) if use_draft else None
        model_name = user.preferred_model
        temperature = float(user.temperature or 0.7)

        response_text = ""
        response_model = model_name
        response_tokens = None
        stream_used = False

        # ---- 1) 优先尝试流式 ----
        try:
            buffer = ""
            last_flush = time.monotonic()
            if stream is not None:
                # 推送占位草稿（让用户立即看到"思考中"）
                await stream.push("💭 …", force_plain=True)

            async for chunk in provider.chat_stream(
                messages=messages_with_system,
                model=model_name,
                temperature=temperature,
                max_tokens=settings.max_tokens,
            ):
                if not chunk:
                    continue
                stream_used = True
                response_text += chunk
                buffer += chunk
                now = time.monotonic()
                # 草稿会带动画；按字符数 + 时间双触发，但短回复不推草稿
                if (
                    len(buffer) >= DRAFT_FLUSH_CHARS
                    or (now - last_flush) >= DRAFT_FLUSH_INTERVAL
                ):
                    if len(response_text) >= DRAFT_MIN_RESPONSE_CHARS:
                        await _push_draft(
                            stream,
                            normalize_rich_markdown_latex(
                                response_text[-DRAFT_MAX_CHARS:]
                            ),
                        )
                    buffer = ""
                    last_flush = now

            # 流结束：若响应已经够长，推送一次最终草稿
            if (
                stream_used
                and stream is not None
                and response_text
                and len(response_text) >= DRAFT_MIN_RESPONSE_CHARS
            ):
                await _push_draft(
                    stream,
                    normalize_rich_markdown_latex(
                        response_text[-DRAFT_MAX_CHARS:]
                    ),
                )
        except Exception as stream_err:
            if _is_terminal_provider_error(stream_err):
                logger.warning(
                    f"流式 chat_stream 遇到终止性服务商错误，不再回退非流式: "
                    f"{type(stream_err).__name__}: {stream_err}"
                )
                await message.answer(
                    _format_provider_error(stream_err, provider_name),
                    **route.send_kwargs(),
                )
                return
            logger.warning(
                f"流式 chat_stream 失败，回退非流式: {type(stream_err).__name__}: {stream_err}"
            )
            stream_used = False
            response_text = ""

        # ---- 2) 流式失败 / 没拿到内容则回退非流式 ----
        if not stream_used:
            try:
                response = await provider.chat(
                    messages=messages_with_system,
                    model=model_name,
                    temperature=temperature,
                    max_tokens=settings.max_tokens,
                )
            except Exception as chat_err:
                logger.error(f"非流式 provider.chat 失败: {type(chat_err).__name__}: {chat_err}")
                await message.answer(
                    _format_provider_error(chat_err, provider_name),
                    **route.send_kwargs(),
                )
                return
            response_text = response.content
            response_model = response.model
            response_tokens = (
                response.usage.get("total_tokens") if response.usage else None
            )
            # 非流式时尝试一次草稿，让用户在持久化前先看到完整预览
            if (
                stream is not None
                and response_text
                and len(response_text) >= DRAFT_MIN_RESPONSE_CHARS
            ):
                await _push_draft(
                    stream,
                    normalize_rich_markdown_latex(
                        response_text[-DRAFT_MAX_CHARS:]
                    ),
                )

        response_text = normalize_rich_markdown_latex(response_text)

        if not response_text.strip():
            await message.answer(
                "⚠️ AI 返回了空内容",
                **route.send_kwargs(),
            )
            return

        # ---- 3) 保存 AI 响应 ----
        await context_manager.add_message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=response_text,
            provider=user.preferred_provider,
            model=response_model,
            tokens_used=response_tokens,
        )

        # Update provider bucket stats.
        session_manager.update_provider_stats(
            session_key,
            provider_name,
            message_count=1,
            tokens=response_tokens or 0,
        )
        await _save_session_data(conversation, session_key)
        await context_manager.session.commit()

        # ---- 4) 持久化收尾 ----
        sent = False
        try:
            if stream is not None:
                sent = await stream.finalize(response_text)
            else:
                sent = await send_rich_message(
                    bot_token=bot_token,
                    chat_id=route.chat_id,
                    markdown_text=response_text,
                    message_thread_id=route.message_thread_id,
                    direct_messages_topic_id=route.direct_messages_topic_id,
                    business_connection_id=route.business_connection_id,
                )

            if sent:
                logger.info("Rich Message sent successfully")
            else:
                logger.warning("Rich Messages unavailable, falling back to MarkdownV2")
                formatted_content = format_markdown_v2(response_text)
                try:
                    await message.answer(
                        formatted_content,
                        parse_mode="MarkdownV2",
                        **route.send_kwargs(),
                    )
                except Exception:
                    await message.answer(
                        response_text,
                        **route.send_kwargs(),
                    )

        except Exception as format_error:
            # 如果格式化失败，回退到纯文本
            logger.warning(f"格式化失败，使用纯文本: {format_error}")
            await message.answer(response_text, **route.send_kwargs())

    except Exception as e:
        logger.error(f"AI 调用失败: {e}")
        await message.answer(
            f"❌ 处理失败: {str(e)}",
            **route.send_kwargs(),
        )
