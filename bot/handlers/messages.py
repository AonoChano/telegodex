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
from bot.utils.latex import normalize_latex
from prompts import get_prompt_manager
from config import settings

router = Router()

# 流式 draft 触发间隔：积攒 N 字符再推送一次，避免触发限流
DRAFT_FLUSH_CHARS = 24
# 流式 draft 触发最长时间：超过 N 秒强制推送一次（兜底）
DRAFT_FLUSH_INTERVAL = 1.0
# 单次草稿内容上限：sendMessageDraft 文本最大 4096 字符
DRAFT_MAX_CHARS = 4000


async def _try_draft(
    bot_token: str,
    chat_id: int | str,
    text: str,
    draft_id: int,
    message_thread_id: int | None,
    *,
    use_rich: bool,
) -> bool:
    """尝试推送一次草稿。失败时 rich → 纯文本回退；都失败则返回 False。"""
    if not text:
        return False
    if use_rich:
        ok = await send_rich_message_draft(
            bot_token=bot_token,
            chat_id=chat_id,
            markdown_text=text,
            draft_id=draft_id,
            message_thread_id=message_thread_id,
        )
        if ok:
            return True
        # Rich 草稿被拒（多为版本/权限），降级为纯文本草稿
        ok = await send_message_draft(
            bot_token=bot_token,
            chat_id=chat_id,
            text=text,
            draft_id=draft_id,
            message_thread_id=message_thread_id,
        )
        return ok
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
        reply_markup=get_main_menu()
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """处理 /help 命令"""
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

    await message.answer(help_text, parse_mode="MarkdownV2")


@router.message(Command("new"))
async def cmd_new(message: Message, context_manager: ContextManager):
    """开始新对话"""
    user_id = message.from_user.id
    thread_id = message.message_thread_id

    # 创建新对话（按 topic 隔离）
    conversation = await context_manager.create_new_conversation(
        user_id, thread_id=thread_id
    )

    await message.answer(
        "✅ 已开始新对话\\!",
        parse_mode="MarkdownV2"
    )


@router.message(Command("clear"))
async def cmd_clear(message: Message, context_manager: ContextManager):
    """清空当前对话"""
    user_id = message.from_user.id
    thread_id = message.message_thread_id

    conversation = await context_manager.get_or_create_conversation(
        user_id, thread_id=thread_id
    )

    await context_manager.clear_conversation(conversation.id)

    await message.answer(
        "🗑️ 当前对话历史已清空\\!",
        parse_mode="MarkdownV2"
    )


@router.message(F.text)
async def handle_message(message: Message, context_manager: ContextManager, ai_router: AIRouter):
    """处理普通文本消息"""
    user_id = message.from_user.id
    user_text = message.text
    thread_id = message.message_thread_id  # topic 模式下是 topic id；普通私聊为 None

    # 输入验证和清理
    from security import sanitize_input
    user_text = sanitize_input(user_text, max_length=4000)

    if not user_text:
        await message.answer("⚠️ 消息内容为空或过长")
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
        await message.answer("功能开发中...")
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
        await message.answer("❌ 没有可用的 AI 服务商，请检查配置")
        return

    try:
        # 发送 "正在输入..." 状态
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

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

        # ---- 1) 优先尝试流式 ----
        try:
            buffer = ""
            last_flush = time.monotonic()
            if use_draft:
                # 推送占位草稿（让用户立即看到"思考中"）
                await _try_draft(
                    bot_token=bot_token,
                    chat_id=message.chat.id,
                    text="💭 …",
                    draft_id=draft_id,
                    message_thread_id=thread_id,
                    use_rich=False,
                )

            async for chunk in provider.chat_stream(
                messages=messages_with_system,
                model=model_name,
                temperature=temperature,
                max_tokens=settings.max_tokens,
            ):
                if not chunk:
                    continue
                # 流式阶段立即归一化，避免草稿里出现裸 \command
                chunk = normalize_latex(chunk)
                stream_used = True
                response_text += chunk
                buffer += chunk
                now = time.monotonic()
                # 草稿会带动画；为避免触发限流，按字符数 + 时间双触发
                if (
                    len(buffer) >= DRAFT_FLUSH_CHARS
                    or (now - last_flush) >= DRAFT_FLUSH_INTERVAL
                ):
                    if use_draft and response_text:
                        await _try_draft(
                            bot_token=bot_token,
                            chat_id=message.chat.id,
                            text=response_text[-DRAFT_MAX_CHARS:],
                            draft_id=draft_id,
                            message_thread_id=thread_id,
                            use_rich=True,
                        )
                    buffer = ""
                    last_flush = now

            # 流结束后推送一次最终草稿
            if stream_used and use_draft and response_text:
                await _try_draft(
                    bot_token=bot_token,
                    chat_id=message.chat.id,
                    text=response_text[-DRAFT_MAX_CHARS:],
                    draft_id=draft_id,
                    message_thread_id=thread_id,
                    use_rich=True,
                )
        except Exception as stream_err:
            logger.warning(
                f"流式 chat_stream 失败，回退非流式: {stream_err}"
            )
            stream_used = False
            response_text = ""

        # ---- 2) 流式失败 / 没拿到内容则回退非流式 ----
        if not stream_used:
            response = await provider.chat(
                messages=messages_with_system,
                model=model_name,
                temperature=temperature,
                max_tokens=settings.max_tokens,
            )
            response_text = normalize_latex(response.content)
            response_model = response.model
            response_tokens = (
                response.usage.get("total_tokens") if response.usage else None
            )
            # 非流式时也尝试一次草稿，让用户在持久化前先看到完整预览
            if use_draft and response_text:
                await _try_draft(
                    bot_token=bot_token,
                    chat_id=message.chat.id,
                    text=response_text[-DRAFT_MAX_CHARS:],
                    draft_id=draft_id,
                    message_thread_id=thread_id,
                    use_rich=True,
                )

        if not response_text.strip():
            await message.answer(
                "⚠️ AI 返回了空内容",
                message_thread_id=thread_id,
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
                chat_id=message.chat.id,
                markdown_text=response_text,
                message_thread_id=thread_id,
            )

            if success:
                logger.info("Rich Message sent successfully")
            else:
                logger.warning("Rich Messages unavailable, falling back to MarkdownV2")
                formatted_content = format_markdown_v2(response_text)
                await message.answer(
                    formatted_content,
                    parse_mode="MarkdownV2",
                    message_thread_id=thread_id,
                )

        except Exception as format_error:
            # 如果格式化失败，回退到纯文本
            logger.warning(f"格式化失败，使用纯文本: {format_error}")
            await message.answer(response_text, message_thread_id=thread_id)

    except Exception as e:
        logger.error(f"AI 调用失败: {e}")
        await message.answer(
            f"❌ 处理失败: {str(e)}",
            message_thread_id=thread_id,
        )
