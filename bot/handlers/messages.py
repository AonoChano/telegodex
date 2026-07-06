from inspect import isawaitable
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from loguru import logger
from sqlalchemy import select

from ai import AIRouter, MessageRole
from ai import Message as AIMessage
from ai.token_usage import combine_token_usages
from bot.handlers.chat_delivery import deliver_chat_response
from bot.handlers.chat_response import DRAFT_MAX_CALLS_PER_ID, generate_chat_provider_response
from bot.handlers.chat_runtime import select_chat_runtime
from bot.handlers.chat_sessions import load_session_data, resolve_provider_conversation, save_session_data
from bot.handlers.chat_tool_requests import (
    handle_chat_tool_request,
    has_chat_tool_request,
)
from bot.keyboards import get_language_selector, get_main_menu, get_settings_menu
from bot.telegram_draft import DraftStream
from bot.utils.rich_messages import send_rich_message
from bot.utils.routing import TelegramRoute
from config import settings
from core.orchestrator.chat_tools import build_telegodex_capability_prompt
from core.session import SessionKey, session_manager
from i18n import list_available_locales, resolve_locale, tr
from prompts import get_prompt_manager
from storage import ContextManager
from storage.models import User

router = Router()

def escape_markdown(text: str) -> str:
    """转义 Telegram MarkdownV2 特殊字符（用于 Bot 自身消息）"""
    special_chars = ["_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"]
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    return text


def _rich_inline_text(text: str) -> str:
    """Escape user/provider text for simple Rich Markdown inline contexts."""
    return text.replace("\\", "\\\\").replace("*", "\\*").replace("_", "\\_").replace("`", "\\`")


def _rich_table_cell(text: str) -> str:
    return _rich_inline_text(text).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _build_start_message(locale: str | None, user_name: str, provider_names: list[str]) -> str:
    provider_ready = tr("bot.commands.start.provider_ready", locale)
    if provider_names:
        rows = "\n".join(
            tr(
                "bot.commands.start.provider_row",
                locale,
                provider=_rich_table_cell(provider),
                status=provider_ready,
            )
            for provider in provider_names
        )
    else:
        rows = tr("bot.commands.start.no_providers", locale)

    providers_section = tr("bot.commands.start.providers_section", locale, rows=rows)
    commands_section = tr("bot.commands.start.commands_section", locale)
    return tr(
        "bot.commands.start.welcome",
        locale,
        name=_rich_inline_text(user_name),
        providers=providers_section,
        commands=commands_section,
    )


@router.message(Command("start"))
async def cmd_start(message: Message, context_manager: ContextManager, ai_router: AIRouter):
    """处理 /start 命令"""
    user = message.from_user
    route = TelegramRoute.from_message(message)

    # 创建或更新用户
    db_user = await context_manager.get_or_create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code,
    )
    locale = resolve_locale(db_user.ui_language, db_user.language_code)

    user_name = user.first_name or tr("bot.commands.start.default_name", locale)
    provider_names = ai_router.list_available_providers()
    welcome_text = _build_start_message(locale, user_name, provider_names)
    main_menu = get_main_menu(locale)

    bot_token = settings.telegram_bot_token
    if hasattr(bot_token, "get_secret_value"):
        bot_token = bot_token.get_secret_value()

    sent = await send_rich_message(
        bot_token=bot_token,
        chat_id=route.chat_id,
        markdown_text=welcome_text,
        message_thread_id=route.message_thread_id,
        direct_messages_topic_id=route.direct_messages_topic_id,
        business_connection_id=route.business_connection_id,
        reply_markup=main_menu,
    )
    if sent:
        return

    await message.answer(
        welcome_text,
        reply_markup=main_menu,
        **route.send_kwargs(),
    )


@router.message(Command("settings"))
async def cmd_settings(message: Message, context_manager: ContextManager | None = None) -> None:
    """Open the settings menu."""
    route = TelegramRoute.from_message(message)
    permission_mode = None
    locale = resolve_locale(None, message.from_user.language_code if message.from_user else None)
    if context_manager is not None and message.from_user is not None:
        try:
            result = await context_manager.session.execute(select(User).where(User.id == message.from_user.id))
            user = result.scalar_one_or_none()
            if isawaitable(user):
                user = await user
            permission_mode = getattr(user, "tool_permission_mode", None)
            locale = resolve_locale(user.ui_language, user.language_code)
        except Exception as exc:
            logger.debug(f"Failed to load settings permission mode: {exc}")
    await message.answer(
        tr("bot.commands.settings.title", locale),
        reply_markup=get_settings_menu(permission_mode, locale),
        **route.send_kwargs(),
    )


@router.message(Command("language"))
async def cmd_language(message: Message) -> None:
    """Open the language selector."""
    route = TelegramRoute.from_message(message)
    locale = resolve_locale(None, message.from_user.language_code if message.from_user else None)
    available = list_available_locales()
    keyboard = get_language_selector(available, locale, back_callback="settings:back", locale=locale)
    await message.answer(
        tr("bot.callbacks.language_title", locale),
        reply_markup=keyboard,
        **route.send_kwargs(),
    )


@router.message(Command("new"))
async def cmd_new(message: Message, context_manager: ContextManager):
    """开始新对话"""
    user_id = message.from_user.id
    route = TelegramRoute.from_message(message)
    thread_id = route.storage_thread_id

    # 创建新对话（按 topic 隔离）
    await context_manager.create_new_conversation(user_id, thread_id=thread_id, chat_id=route.chat_id)

    locale = resolve_locale(None, message.from_user.language_code if message.from_user else None)
    await message.answer(
        tr("bot.commands.new.success", locale),
        parse_mode="MarkdownV2",
        **route.send_kwargs(),
    )


@router.message(Command("clear"))
async def cmd_clear(message: Message, context_manager: ContextManager):
    """清空当前对话"""
    user_id = message.from_user.id
    route = TelegramRoute.from_message(message)
    thread_id = route.storage_thread_id

    conversation = await context_manager.get_or_create_conversation(user_id, thread_id=thread_id, chat_id=route.chat_id)

    await context_manager.clear_conversation(conversation.id)

    locale = resolve_locale(None, message.from_user.language_code if message.from_user else None)
    await message.answer(
        tr("bot.commands.clear.success", locale),
        parse_mode="MarkdownV2",
        **route.send_kwargs(),
    )



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
        prompt = prompt[len("/model") :].strip()

    user = await context_manager.get_or_create_user(user_id)
    locale = resolve_locale(user.ui_language, user.language_code)

    if not prompt:
        available = ai_router.list_available_providers()
        lines = [tr("bot.commands.model.usage", locale), ""]
        for name in available:
            lines.append(tr("bot.commands.model.available", locale, name=name))
        await message.answer(
            "\n".join(lines),
            parse_mode="Markdown",
            **route.send_kwargs(),
        )
        return

    provider_name = prompt.lower()
    if not ai_router.is_provider_available(provider_name):
        await message.answer(
            tr("bot.commands.model.unknown", locale, provider=provider_name),
            parse_mode="Markdown",
            **route.send_kwargs(),
        )
        return

    conversation = await context_manager.get_or_create_conversation(user_id, thread_id=thread_id, chat_id=route.chat_id)

    session_data = await load_session_data(conversation, session_key)

    # Save current provider bucket before switching.
    if user.preferred_provider:
        old_bucket = session_data.get_or_create_bucket(user.preferred_provider)
        old_bucket.session_id = str(conversation.id)

    # Switch active provider.
    user.preferred_provider = provider_name
    session_manager.set_active_provider(session_key, provider_name)

    # Resolve or create the provider-specific conversation.
    provider_conv = await resolve_provider_conversation(
        context_manager, session_key, session_data, user_id, thread_id, provider_name
    )

    await save_session_data(provider_conv, session_key)
    await context_manager.session.commit()

    await message.answer(
        tr("bot.commands.model.switched", locale, provider=provider_name),
        parse_mode="MarkdownV2",
        **route.send_kwargs(),
    )


@router.message(F.text)
async def handle_message(
    message: Message, context_manager: ContextManager, ai_router: AIRouter, orchestrator: Any | None = None
):
    """处理普通文本消息"""
    user_id = message.from_user.id
    user_text = message.text
    route = TelegramRoute.from_message(message)
    thread_id = route.storage_thread_id

    # 输入验证和清理
    from security import sanitize_input

    user_text = sanitize_input(user_text, max_length=4000)

    if not user_text:
        locale = resolve_locale(None, message.from_user.language_code if message.from_user else None)
        await message.answer(tr("bot.errors.empty_input", locale), **route.send_kwargs())
        return

    # 获取用户和对话（按 topic + provider 隔离）
    user = await context_manager.get_or_create_user(user_id)
    locale = resolve_locale(user.ui_language, user.language_code)

    # 菜单按钮处理 — match across ALL locales for robustness
    # (user's ReplyKeyboard may still show old-language text after language change)
    menu_keys = {
        "bot.menu.new_chat": "new_chat",
        "bot.menu.history": "history",
        "bot.menu.settings": "settings",
        "bot.menu.help": "help",
    }
    menu_options = {}
    for _locale_info in list_available_locales():
        for _key, _action in menu_keys.items():
            _text = tr(_key, _locale_info.locale)
            if _text != _key:
                menu_options[_text] = _action
    if user_text in menu_options:
        choice = menu_options[user_text]
        if choice == "new_chat":
            await cmd_new(message, context_manager)
            return
        if choice == "settings":
            await cmd_settings(message, context_manager)
            return
        if choice == "help":
            from bot.handlers.help import send_help_toc

            await send_help_toc(message, locale)
            return
        # TODO: 实现历史记录
        await message.answer(tr("bot.callbacks.wip", locale), **route.send_kwargs())
        return

    session_key = SessionKey.from_telegram_message(route.chat_id, route.message_thread_id)

    # Bootstrap session data from the current active conversation.
    base_conv = await context_manager.get_or_create_conversation(user_id, thread_id=thread_id, chat_id=route.chat_id)
    session_data = await load_session_data(base_conv, session_key)

    runtime = select_chat_runtime(user, ai_router)
    if runtime is None:
        await message.answer(
            tr("bot.errors.no_provider", locale),
            **route.send_kwargs(),
        )
        return
    provider_name = runtime.provider_name
    provider = runtime.provider

    # Resolve the provider-isolated conversation.
    conversation = await resolve_provider_conversation(
        context_manager, session_key, session_data, user_id, thread_id, provider_name
    )

    # Ensure the base conversation also carries the latest session data.
    await save_session_data(conversation, session_key)

    try:
        # 添加用户消息到历史
        await context_manager.add_message(conversation_id=conversation.id, role=MessageRole.USER, content=user_text)

        # 获取对话历史
        history = await context_manager.get_conversation_history(conversation.id)
    except Exception as e:
        logger.error(f"Failed to prepare chat context: {e}")
        await message.answer(
            tr("bot.errors.processing_failed", locale, error=str(e)),
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

        # 获取系统提示词（按 provider 分层组合）
        prompt_manager = get_prompt_manager()
        system_prompt = prompt_manager.get_system_prompt(
            provider=provider_name
        ) + build_telegodex_capability_prompt(getattr(user, "tool_permission_mode", None))

        # 构建包含系统提示词的消息历史
        messages_with_system = [AIMessage(role=MessageRole.SYSTEM, content=system_prompt)] + history

        bot_token = settings.telegram_bot_token
        if hasattr(bot_token, "get_secret_value"):
            bot_token = bot_token.get_secret_value()

        # 仅私有 chat 支持 draft API；其它场景（群组/频道）跳过预览
        use_draft = message.chat.type == "private"
        stream = (
            DraftStream(
                bot_token=bot_token,
                chat_id=route.chat_id,
                message_thread_id=route.draft_thread_id(),
                direct_messages_topic_id=route.direct_messages_topic_id,
                business_connection_id=route.business_connection_id,
                use_rich=True,
                max_draft_calls=DRAFT_MAX_CALLS_PER_ID,
            )
            if use_draft
            else None
        )
        model_name = runtime.model_name
        temperature = runtime.temperature
        max_output_tokens = runtime.max_output_tokens

        provider_response = await generate_chat_provider_response(
            message=message,
            route=route,
            messages_with_system=messages_with_system,
            runtime=runtime,
            stream=stream,
            locale=locale,
        )
        if provider_response is None:
            return
        response_text = provider_response.text
        response_model = provider_response.model
        response_usage = provider_response.usage

        tool_outcome = await handle_chat_tool_request(
            tool_response_text=response_text,
            message=message,
            route=route,
            context_manager=context_manager,
            conversation=conversation,
            messages_with_system=messages_with_system,
            provider=provider,
            orchestrator=orchestrator,
            session_key=session_key,
            permission_mode=getattr(user, "tool_permission_mode", None),
            model_name=model_name,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            locale=locale,
        )
        if has_chat_tool_request(response_text):
            if tool_outcome is None:
                return
            response_text = tool_outcome.text
            response_model = tool_outcome.model
            response_usage = combine_token_usages(response_usage, tool_outcome.usage)

        if not response_text.strip():
            await message.answer(
                tr("bot.errors.empty_response", locale),
                **route.send_kwargs(),
            )
            return

        # ---- 3) 保存 AI 响应 ----
        await context_manager.add_message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=response_text,
            provider=provider_name,
            model=response_model,
            tokens_used=response_usage.total_tokens if response_usage else None,
            prompt_tokens=response_usage.prompt_tokens if response_usage else None,
            completion_tokens=response_usage.completion_tokens if response_usage else None,
            token_count_estimated=response_usage.estimated if response_usage else None,
            tokenizer_name=response_usage.tokenizer_name if response_usage else None,
        )

        # Update provider bucket stats.
        session_manager.update_provider_stats(
            session_key,
            provider_name,
            message_count=1,
            tokens=response_usage.total_tokens if response_usage else 0,
        )
        await save_session_data(conversation, session_key)
        await context_manager.session.commit()

        await deliver_chat_response(
            message=message,
            route=route,
            bot_token=bot_token,
            stream=stream,
            response_text=response_text,
        )

    except Exception as e:
        logger.error(f"AI 调用失败: {e}")
        await message.answer(
            tr("bot.errors.processing_failed", locale, error=str(e)),
            **route.send_kwargs(),
        )
