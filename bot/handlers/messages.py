import time

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from loguru import logger

from ai import AIRouter, Message as AIMessage, MessageRole
from storage import ContextManager
from bot.keyboards import get_main_menu
from bot.utils.markdown import format_markdown_v2
from bot.utils.rich_messages import (
    send_rich_message,
    send_rich_message_draft,
    send_message_draft,
    new_draft_id,
)
from bot.utils.latex import normalize_rich_markdown_latex
from bot.utils.routing import TelegramRoute
from prompts import get_prompt_manager
from config import settings

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


async def _try_draft(
    bot_token: str,
    chat_id: int | str,
    text: str,
    draft_id: int,
    message_thread_id: int | None,
    *,
    use_rich: bool,
    allow_rich: bool = True,
) -> bool:
    """
    尝试推送一次草稿。

    - ``use_rich=True`` 且 ``allow_rich=True``：先发 Rich 草稿，失败再降级到
      纯文本草稿。
    - ``use_rich=True`` 但 ``allow_rich=False``：本次响应内 Rich 已经失败过，
      直接发纯文本草稿，避免反复换 draft_id 触发的反滥用保护。
    - ``use_rich=False``：只发纯文本草稿。
    """
    if not text:
        return False
    if use_rich and allow_rich:
        ok = await send_rich_message_draft(
            bot_token=bot_token,
            chat_id=chat_id,
            markdown_text=text,
            draft_id=draft_id,
            message_thread_id=message_thread_id,
        )
        if ok:
            return True
        # Rich 草稿被拒：降级为纯文本草稿
        return await send_message_draft(
            bot_token=bot_token,
            chat_id=chat_id,
            text=text,
            draft_id=draft_id,
            message_thread_id=message_thread_id,
        )
    return await send_message_draft(
        bot_token=bot_token,
        chat_id=chat_id,
        text=text,
        draft_id=draft_id,
        message_thread_id=message_thread_id,
    )


async def _stream_with_draft(
    *,
    bot_token: str,
    chat_id: int | str,
    message_thread_id: int | None,
    full_text: str,
    draft_id: int,
    use_rich_draft: bool,
) -> bool:
    """一次性回灌历史流：用于 provider 不支持 chat_stream 的回退路径。"""
    return await _try_draft(
        bot_token=bot_token,
        chat_id=chat_id,
        text=full_text,
        draft_id=draft_id,
        message_thread_id=message_thread_id,
        use_rich=use_rich_draft,
    )


def escape_markdown(text: str) -> str:
    """转义 Telegram MarkdownV2 特殊字符（用于 Bot 自身消息）"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


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


@router.message(Command("new"))
async def cmd_new(message: Message, context_manager: ContextManager):
    """开始新对话"""
    user_id = message.from_user.id
    route = TelegramRoute.from_message(message)
    thread_id = route.storage_thread_id

    # 创建新对话（按 topic 隔离）
    conversation = await context_manager.create_new_conversation(
        user_id, thread_id=thread_id
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
        user_id, thread_id=thread_id
    )

    await context_manager.clear_conversation(conversation.id)

    await message.answer(
        "🗑️ 当前对话历史已清空\\!",
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
        elif user_text == "ℹ️ 帮助":
            await cmd_help(message)
            return
        # TODO: 实现历史记录和设置
        await message.answer("功能开发中...", **route.send_kwargs())
        return

    # 获取用户和对话（按 topic 隔离）
    user = await context_manager.get_or_create_user(user_id)
    conversation = await context_manager.get_or_create_conversation(
        user_id, thread_id=thread_id
    )

    # 添加用户消息到历史
    await context_manager.add_message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=user_text
    )

    # 获取对话历史
    history = await context_manager.get_conversation_history(conversation.id)

    # 选择 AI Provider
    provider = ai_router.get_provider(user.preferred_provider)
    if not provider:
        provider = ai_router.get_default_provider()

    if not provider:
        await message.answer(
            "❌ 没有可用的 AI 服务商，请检查配置",
            **route.send_kwargs(),
        )
        return

    try:
        # 发送 "正在输入..." 状态
        await message.bot.send_chat_action(
            chat_id=route.chat_id,
            action="typing",
            message_thread_id=route.message_thread_id,
            business_connection_id=route.business_connection_id,
        )

        # 获取系统提示词
        prompt_manager = get_prompt_manager()
        system_prompt = prompt_manager.get_system_prompt()

        # 构建包含系统提示词的消息历史
        messages_with_system = [
            AIMessage(role=MessageRole.SYSTEM, content=system_prompt)
        ] + history

        bot_token = settings.telegram_bot_token
        if hasattr(bot_token, 'get_secret_value'):
            bot_token = bot_token.get_secret_value()

        # 仅私有 chat 支持 draft API；其它场景（群组/频道）跳过预览
        use_draft = message.chat.type == "private"
        draft_id = new_draft_id() if use_draft else 0
        model_name = user.preferred_model
        temperature = float(user.temperature or 0.7)

        response_text = ""
        response_model = model_name
        response_tokens = None
        stream_used = False
        # 本次响应内的草稿状态机：
        # - rich_ok：是否在本次响应中成功推过 rich 草稿
        # - rich_disabled：rich 草稿连续失败后置 True，本轮内不再尝试 rich
        # - draft_call_count：累计已推次数（占位 + 内容），封顶 DRAFT_MAX_CALLS_PER_ID
        rich_ok = False
        rich_disabled = False
        draft_call_count = 0

        async def _push_draft(text: str, *, use_rich: bool) -> None:
            """包一层 _try_draft，负责更新 rich_disabled / draft_call_count。"""
            nonlocal rich_ok, rich_disabled, draft_call_count
            if not use_draft or not text or draft_call_count >= DRAFT_MAX_CALLS_PER_ID:
                return
            ok = await _try_draft(
                bot_token=bot_token,
                chat_id=route.chat_id,
                text=text,
                draft_id=draft_id,
                message_thread_id=route.draft_thread_id(),
                use_rich=use_rich,
                allow_rich=not rich_disabled,
            )
            draft_call_count += 1
            if use_rich and ok:
                rich_ok = True
            elif use_rich and not ok and not rich_disabled:
                # 第一次 rich 失败：降级为纯文本草稿，且本轮不再试 rich
                rich_disabled = True
                if not text:
                    return
                ok2 = await _try_draft(
                    bot_token=bot_token,
                    chat_id=route.chat_id,
                    text=text,
                    draft_id=draft_id,
                    message_thread_id=route.draft_thread_id(),
                    use_rich=False,
                )
                if not ok2:
                    # 连纯文本都失败（多半被服务器拒），整个草稿阶段直接放弃
                    logger.warning(
                        f"Plain draft also failed, abandoning draft for this response"
                    )

        # ---- 1) 优先尝试流式 ----
        try:
            buffer = ""
            last_flush = time.monotonic()
            if use_draft:
                # 推送占位草稿（让用户立即看到"思考中"）
                await _push_draft("💭 …", use_rich=False)

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
                            normalize_rich_markdown_latex(
                                response_text[-DRAFT_MAX_CHARS:]
                            ),
                            use_rich=True,
                        )
                    buffer = ""
                    last_flush = now

            # 流结束：若响应已经够长且本轮尚未达到调用上限，推送一次最终草稿
            if (
                stream_used
                and use_draft
                and response_text
                and len(response_text) >= DRAFT_MIN_RESPONSE_CHARS
                and draft_call_count < DRAFT_MAX_CALLS_PER_ID
            ):
                await _push_draft(
                    normalize_rich_markdown_latex(
                        response_text[-DRAFT_MAX_CHARS:]
                    ),
                    use_rich=True,
                )
        except Exception as stream_err:
            logger.warning(
                f"流式 chat_stream 失败，回退非流式: {type(stream_err).__name__}: {stream_err}"
            )
            stream_used = False
            response_text = ""
            draft_call_count = 0
            rich_disabled = False
            rich_ok = False

        # ---- 2) 流式失败 / 没拿到内容则回退非流式 ----
        if not stream_used:
            response = await provider.chat(
                messages=messages_with_system,
                model=model_name,
                temperature=temperature,
                max_tokens=settings.max_tokens,
            )
            response_text = response.content
            response_model = response.model
            response_tokens = (
                response.usage.get("total_tokens") if response.usage else None
            )
            # 非流式时尝试一次草稿，让用户在持久化前先看到完整预览
            if (
                use_draft
                and response_text
                and len(response_text) >= DRAFT_MIN_RESPONSE_CHARS
            ):
                await _push_draft(
                    normalize_rich_markdown_latex(
                        response_text[-DRAFT_MAX_CHARS:]
                    ),
                    use_rich=True,
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

        # ---- 4) 持久化收尾：sendRichMessage ----
        try:
            success = await send_rich_message(
                bot_token=bot_token,
                chat_id=route.chat_id,
                markdown_text=response_text,
                message_thread_id=route.message_thread_id,
                direct_messages_topic_id=route.direct_messages_topic_id,
                business_connection_id=route.business_connection_id,
            )

            if success:
                logger.info("Rich Message sent successfully")
            else:
                logger.warning("Rich Messages unavailable, falling back to MarkdownV2")
                formatted_content = format_markdown_v2(response_text)
                await message.answer(
                    formatted_content,
                    parse_mode="MarkdownV2",
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
