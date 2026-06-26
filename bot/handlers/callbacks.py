from typing import Any

from aiogram import Router
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy import select

from ai import AIRouter
from bot.keyboards import (
    get_confirmation_keyboard,
    get_model_selector,
    get_provider_selector,
    get_settings_menu,
)
from storage import ContextManager, User

router = Router()


@router.callback_query(lambda c: c.data and c.data.startswith("settings:"))
async def handle_settings_callback(callback: CallbackQuery, context_manager: ContextManager, ai_router: AIRouter):
    """处理设置菜单回调"""
    action = callback.data.split(":", 1)[1]

    if action == "provider":
        # 显示 AI 服务商选择器
        user = await context_manager.session.execute(
            select(User).where(User.id == callback.from_user.id)
        )
        user_obj = user.scalar_one()

        available_providers = ai_router.list_available_providers()
        keyboard = get_provider_selector(available_providers, user_obj.preferred_provider)

        await callback.message.edit_text(
            "🤖 选择 AI 服务商：",
            reply_markup=keyboard
        )

    elif action == "model":
        # 显示模型选择器
        user = await context_manager.session.execute(
            select(User).where(User.id == callback.from_user.id)
        )
        user_obj = user.scalar_one()

        provider = ai_router.get_provider(user_obj.preferred_provider)
        if provider:
            models = provider.get_available_models()
            keyboard = get_model_selector(
                user_obj.preferred_provider,
                models,
                user_obj.preferred_model
            )

            await callback.message.edit_text(
                f"🎯 选择模型 ({provider.provider_name})：",
                reply_markup=keyboard
            )

    elif action == "back":
        # 返回设置主菜单
        await callback.message.edit_text(
            "⚙️ 设置",
            reply_markup=get_settings_menu()
        )

    elif action == "close":
        # 关闭设置菜单
        await callback.message.delete()

    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("provider:"))
async def handle_provider_change(callback: CallbackQuery, context_manager: ContextManager):
    """处理服务商切换"""
    provider = callback.data.split(":", 1)[1]

    user = await context_manager.session.execute(
        select(User).where(User.id == callback.from_user.id)
    )
    user_obj = user.scalar_one()
    user_obj.preferred_provider = provider
    user_obj.preferred_model = None  # 重置模型选择

    await context_manager.session.commit()

    await callback.answer(f"✅ 已切换到 {provider}", show_alert=True)
    await callback.message.edit_text(
        "⚙️ 设置",
        reply_markup=get_settings_menu()
    )


@router.callback_query(lambda c: c.data and c.data.startswith("model:"))
async def handle_model_change(callback: CallbackQuery, context_manager: ContextManager):
    """处理模型切换"""
    parts = callback.data.split(":", 2)
    model = parts[2]

    user = await context_manager.session.execute(
        select(User).where(User.id == callback.from_user.id)
    )
    user_obj = user.scalar_one()
    user_obj.preferred_model = model

    await context_manager.session.commit()

    await callback.answer(f"✅ 已切换到 {model}", show_alert=True)
    await callback.message.edit_text(
        "⚙️ 设置",
        reply_markup=get_settings_menu()
    )


@router.callback_query(lambda c: c.data and c.data.startswith("conv:"))
async def handle_conversation_callback(callback: CallbackQuery, context_manager: ContextManager):
    """处理对话历史回调"""
    action = callback.data.split(":", 1)[1]

    if action == "load":
        # TODO: 加载特定对话
        await callback.answer("功能开发中...", show_alert=True)

    elif action == "clear_all":
        # 显示确认对话框
        await callback.message.edit_text(
            "⚠️ 确定要清空所有对话历史吗？此操作不可撤销！",
            reply_markup=get_confirmation_keyboard("clear_all_conversations")
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

        await callback.message.edit_text("✅ 所有对话历史已清空！")
        logger.info(f"用户 {user_id} 清空了所有对话历史")

    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("cancel:"))
async def handle_cancel(callback: CallbackQuery):
    """处理取消操作"""
    await callback.message.delete()
    await callback.answer("已取消")


# ---------------------------------------------------------------------------
# CodexBridge approval callbacks
# ---------------------------------------------------------------------------

@router.callback_query(lambda c: c.data and c.data.startswith("codex_approval:"))
async def handle_codex_approval(callback: CallbackQuery, orchestrator: Any):
    """Handle Codex approval inline button callbacks.

    Callback data format: ``codex_approval:{token}``. The token maps to
    ``(approval_id, decision)`` inside the shared ``ApprovalHandler``.
    """
    if callback.data is None:
        await callback.answer("Invalid callback data", show_alert=True)
        return

    parts = callback.data.split(":", 1)
    if len(parts) < 2:
        await callback.answer("Invalid callback data", show_alert=True)
        return

    token = parts[1]
    approval = orchestrator.approval_handler.resolve_callback_token(token)
    if approval is None:
        await callback.answer("Approval already timed out", show_alert=True)
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
                    f"Codex approval handled: {decision_label}",
                    reply_markup=None,
                )
            except Exception as edit_exc:
                logger.warning(f"Failed to compact approval message: {edit_exc}")
    else:
        await callback.answer("Approval already timed out", show_alert=True)
