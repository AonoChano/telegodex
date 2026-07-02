from typing import Any

from aiogram import Router
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy import select

from ai import AIRouter
from bot.keyboards import (
    get_confirmation_keyboard,
    get_language_selector,
    get_main_menu,
    get_model_selector,
    get_provider_selector,
    get_settings_menu,
    get_temperature_selector,
)
from core.orchestrator.chat_tools import next_permission_mode, permission_mode_label
from i18n import list_available_locales, resolve_locale, tr
from storage import ContextManager, User

router = Router()


@router.callback_query(lambda c: c.data and c.data.startswith("settings:"))
async def handle_settings_callback(callback: CallbackQuery, context_manager: ContextManager, ai_router: AIRouter):
    """处理设置菜单回调"""
    action = callback.data.split(":", 1)[1]

    user = await context_manager.session.execute(select(User).where(User.id == callback.from_user.id))
    user_obj = user.scalar_one()
    locale = resolve_locale(user_obj.ui_language, user_obj.language_code)

    if action == "provider":
        # 显示 AI 服务商选择器
        available_providers = ai_router.list_available_providers()
        keyboard = get_provider_selector(available_providers, user_obj.preferred_provider, locale)

        await callback.message.edit_text(tr("bot.settings.select_provider_title", locale), reply_markup=keyboard)

    elif action == "model":
        # 显示模型选择器
        provider = ai_router.get_provider(user_obj.preferred_provider)
        if provider:
            models = provider.get_available_models()
            keyboard = get_model_selector(user_obj.preferred_provider, models, user_obj.preferred_model, locale)

            await callback.message.edit_text(
                tr("bot.settings.select_model_title", locale, provider=provider.provider_name),
                reply_markup=keyboard,
            )

    elif action == "back":
        # 返回设置主菜单
        await callback.message.edit_text(
            tr("bot.settings.title", locale),
            reply_markup=get_settings_menu(user_obj.tool_permission_mode, locale),
        )

    elif action == "temperature":
        keyboard = get_temperature_selector(user_obj.temperature, locale)
        value = _format_temperature_label(user_obj.temperature)
        await callback.message.edit_text(
            tr("bot.settings.temperature_title", locale, value=value),
            reply_markup=keyboard,
        )

    elif action == "permission":
        user_obj.tool_permission_mode = next_permission_mode(user_obj.tool_permission_mode)
        await context_manager.session.commit()
        label = permission_mode_label(user_obj.tool_permission_mode, locale)
        await callback.message.edit_text(
            tr("bot.settings.title", locale),
            reply_markup=get_settings_menu(user_obj.tool_permission_mode, locale),
        )
        await callback.answer(tr("bot.settings.permission", locale, label=label), show_alert=False)
        return

    elif action == "language":
        available = list_available_locales()
        keyboard = get_language_selector(available, locale, back_callback="settings:back", locale=locale)
        await callback.message.edit_text(tr("bot.callbacks.language_title", locale), reply_markup=keyboard)

    elif action == "close":
        # 关闭设置菜单
        await callback.message.delete()

    await callback.answer()


def _format_temperature_label(value: str | float | int | None) -> str:
    if value is None:
        return "0.7"
    try:
        return f"{float(str(value).strip()):.1f}"
    except (TypeError, ValueError):
        return str(value)


@router.callback_query(lambda c: c.data and c.data.startswith("temperature:set:"))
async def handle_temperature_change(callback: CallbackQuery, context_manager: ContextManager):
    """Handle user temperature selection."""
    value = callback.data.split(":", 2)[2]

    user = await context_manager.session.execute(select(User).where(User.id == callback.from_user.id))
    user_obj = user.scalar_one()
    locale = resolve_locale(user_obj.ui_language, user_obj.language_code)

    try:
        float(value)
    except ValueError:
        await callback.answer(tr("bot.errors.invalid_callback", locale), show_alert=True)
        return

    user_obj.temperature = value
    await context_manager.session.commit()

    label = _format_temperature_label(value)
    keyboard = get_temperature_selector(value, locale)
    await callback.message.edit_text(
        tr("bot.settings.temperature_title", locale, value=label),
        reply_markup=keyboard,
    )
    await callback.answer(tr("bot.callbacks.temperature_changed", locale, value=label), show_alert=False)


@router.callback_query(lambda c: c.data and c.data.startswith("provider:"))
async def handle_provider_change(callback: CallbackQuery, context_manager: ContextManager):
    """处理服务商切换"""
    provider = callback.data.split(":", 1)[1]

    user = await context_manager.session.execute(select(User).where(User.id == callback.from_user.id))
    user_obj = user.scalar_one()
    locale = resolve_locale(user_obj.ui_language, user_obj.language_code)

    user_obj.preferred_provider = provider
    user_obj.preferred_model = None  # 重置模型选择

    await context_manager.session.commit()

    await callback.answer(tr("bot.callbacks.provider_switched", locale, provider=provider), show_alert=True)
    await callback.message.edit_text(
        tr("bot.settings.title", locale),
        reply_markup=get_settings_menu(user_obj.tool_permission_mode, locale),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("model:"))
async def handle_model_change(callback: CallbackQuery, context_manager: ContextManager):
    """处理模型切换"""
    parts = callback.data.split(":", 2)
    model = parts[2]

    user = await context_manager.session.execute(select(User).where(User.id == callback.from_user.id))
    user_obj = user.scalar_one()
    locale = resolve_locale(user_obj.ui_language, user_obj.language_code)

    user_obj.preferred_model = model

    await context_manager.session.commit()

    await callback.answer(tr("bot.callbacks.model_switched", locale, model=model), show_alert=True)
    await callback.message.edit_text(
        tr("bot.settings.title", locale),
        reply_markup=get_settings_menu(user_obj.tool_permission_mode, locale),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("conv:"))
async def handle_conversation_callback(callback: CallbackQuery, context_manager: ContextManager):
    """处理对话历史回调"""
    action = callback.data.split(":", 1)[1]
    locale = resolve_locale(None, callback.from_user.language_code if callback.from_user else None)

    if action == "load":
        # TODO: 加载特定对话
        await callback.answer(tr("bot.callbacks.wip", locale), show_alert=True)

    elif action == "clear_all":
        # 显示确认对话框
        await callback.message.edit_text(
            tr("bot.callbacks.confirm_clear", locale),
            reply_markup=get_confirmation_keyboard("clear_all_conversations", locale),
        )

    elif action == "back":
        await callback.message.delete()

    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("confirm:"))
async def handle_confirmation(callback: CallbackQuery, context_manager: ContextManager):
    """处理确认操作"""
    action = callback.data.split(":", 1)[1]

    if action == "clear_all_conversations":
        # 清空所有对话
        user_id = callback.from_user.id
        conversations = await context_manager.get_user_conversations(user_id, limit=999)

        for conv in conversations:
            await context_manager.clear_conversation(conv.id)

        locale = resolve_locale(None, callback.from_user.language_code if callback.from_user else None)
        await callback.message.edit_text(tr("bot.callbacks.history_cleared", locale))
        logger.info(f"用户 {user_id} 清空了所有对话历史")

    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("cancel:"))
async def handle_cancel(callback: CallbackQuery):
    """处理取消操作"""
    locale = resolve_locale(None, callback.from_user.language_code if callback.from_user else None)
    await callback.message.delete()
    await callback.answer(tr("bot.callbacks.canceled", locale))


# ---------------------------------------------------------------------------
# CodexBridge approval callbacks
# ---------------------------------------------------------------------------


@router.callback_query(lambda c: c.data and c.data.startswith("codex_approval:"))
async def handle_codex_approval(callback: CallbackQuery, orchestrator: Any):
    """Handle Codex approval inline button callbacks.

    Callback data format: ``codex_approval:{token}``. The token maps to
    ``(approval_id, decision)`` inside the shared ``ApprovalHandler``.
    """
    locale = resolve_locale(None, callback.from_user.language_code if callback.from_user else None)

    if callback.data is None:
        await callback.answer(tr("bot.errors.invalid_callback", locale), show_alert=True)
        return

    parts = callback.data.split(":", 1)
    if len(parts) < 2:
        await callback.answer(tr("bot.errors.invalid_callback", locale), show_alert=True)
        return

    token = parts[1]
    approval = orchestrator.approval_handler.resolve_callback_token(token)
    if approval is None:
        await callback.answer(tr("bot.errors.approval_timeout", locale), show_alert=True)
        return

    approval_id, decision = approval

    logger.info(f"Codex approval callback: id={approval_id} decision={decision}")

    resolved = await orchestrator.approval_handler.resolve(approval_id, decision)
    if resolved:
        decision_label = orchestrator.approval_handler.describe_decision(decision)
        try:
            await callback.answer(f"{decision_label}")
        except Exception as exc:
            logger.debug(f"Failed to answer approval callback: {exc}")
        try:
            # Approval prompts are temporary gates. The final Codex message will
            # include the executed or rejected tool activity, so remove this
            # prompt instead of leaving a duplicate command block in the topic.
            await callback.message.delete()
        except Exception as exc:
            logger.debug(f"Failed to delete approval message, compacting it: {exc}")
            try:
                await callback.message.edit_text(
                    tr("bot.callbacks.approval_handled", locale, decision=decision_label),
                    reply_markup=None,
                )
            except Exception as edit_exc:
                logger.warning(f"Failed to compact approval message: {edit_exc}")
    else:
        await callback.answer(tr("bot.errors.approval_timeout", locale), show_alert=True)


@router.callback_query(lambda c: c.data and c.data.startswith("lang:set:"))
async def handle_language_change(callback: CallbackQuery, context_manager: ContextManager):
    """Handle language selection."""
    locale_code = callback.data.split(":", 2)[2]

    user = await context_manager.session.execute(select(User).where(User.id == callback.from_user.id))
    user_obj = user.scalar_one()
    user_obj.ui_language = locale_code
    await context_manager.session.commit()

    # Use the newly selected locale for the response
    locale = locale_code
    # Find display_name for the confirmation toast
    display_name = locale_code
    for loc_info in list_available_locales():
        if loc_info.locale == locale_code:
            display_name = loc_info.display_name
            break
    await callback.answer(tr("bot.callbacks.language_changed", locale, language=display_name))
    await callback.message.edit_text(
        tr("bot.settings.title", locale),
        reply_markup=get_settings_menu(user_obj.tool_permission_mode, locale),
    )
    # Re-send the main menu ReplyKeyboard to update button text on the client
    await callback.message.answer(
        tr("bot.callbacks.language_changed", locale, language=display_name),
        reply_markup=get_main_menu(locale),
    )
