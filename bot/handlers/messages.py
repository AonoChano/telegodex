from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from loguru import logger

from ai import AIRouter, Message as AIMessage, MessageRole
from storage import ContextManager
from bot.keyboards import get_main_menu
from bot.utils.markdown import format_markdown_v2
from bot.utils.rich_messages import (
    MarkdownToRichMessage,
    send_rich_message,
    has_rich_features
)
from config import settings

router = Router()


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

    # 创建新对话
    conversation = await context_manager.create_new_conversation(user_id)

    await message.answer(
        "✅ 已开始新对话\\!",
        parse_mode="MarkdownV2"
    )


@router.message(Command("clear"))
async def cmd_clear(message: Message, context_manager: ContextManager):
    """清空当前对话"""
    user_id = message.from_user.id
    conversation = await context_manager.get_or_create_conversation(user_id)

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

    # 获取用户和对话
    user = await context_manager.get_or_create_user(user_id)
    conversation = await context_manager.get_or_create_conversation(user_id)

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

        # 调用 AI
        response = await provider.chat(
            messages=history,
            model=user.preferred_model,
            temperature=float(user.temperature or 0.7),
            max_tokens=settings.max_tokens,
        )

        # 保存 AI 响应
        await context_manager.add_message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=response.content,
            provider=user.preferred_provider,
            model=response.model,
            tokens_used=response.usage.get("total_tokens") if response.usage else None,
        )

        # 格式化并发送响应
        try:
            # 检测是否包含需要 Rich Messages 的特性（表格、数学公式等）
            if has_rich_features(response.content):
                logger.info("检测到 Rich 特性（表格/数学公式），尝试使用 Rich Messages API")

                # 转换为 Rich Message
                rich_message = MarkdownToRichMessage.convert(response.content)

                # 尝试发送 Rich Message
                bot_token = message.bot.token.get_secret_value()
                success = await send_rich_message(
                    bot_token=bot_token,
                    chat_id=message.chat.id,
                    rich_message=rich_message,
                    fallback_text=response.content
                )

                if success:
                    logger.info("✅ Rich Message 发送成功")
                else:
                    # Rich Messages 不可用，回退到 MarkdownV2
                    logger.warning("⚠️ Rich Messages 不可用，回退到 MarkdownV2")
                    formatted_content = format_markdown_v2(response.content)
                    await message.answer(formatted_content, parse_mode="MarkdownV2")
            else:
                # 普通 Markdown，使用 MarkdownV2
                formatted_content = format_markdown_v2(response.content)
                await message.answer(formatted_content, parse_mode="MarkdownV2")

        except Exception as format_error:
            # 如果格式化失败，回退到纯文本
            logger.warning(f"格式化失败，使用纯文本: {format_error}")
            await message.answer(response.content)

    except Exception as e:
        logger.error(f"AI 调用失败: {e}")
        await message.answer(f"❌ 处理失败: {str(e)}")

