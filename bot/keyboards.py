from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from core.orchestrator.chat_tools import permission_mode_label


def get_main_menu() -> ReplyKeyboardMarkup:
    """主菜单键盘"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💬 新对话"), KeyboardButton(text="📝 历史记录")],
            [KeyboardButton(text="⚙️ 设置"), KeyboardButton(text="ℹ️ 帮助")],
        ],
        resize_keyboard=True,
    )
    return keyboard


def get_provider_selector(available_providers: list[str], current_provider: str) -> InlineKeyboardMarkup:
    """AI 服务商选择器"""
    buttons = []

    provider_labels = {
        "openai": "🟢 OpenAI (GPT)",
        "anthropic": "🔵 Anthropic (Claude)",
        "google": "🔴 Google (Gemini)",
    }

    for provider in available_providers:
        label = provider_labels.get(provider, provider)
        if provider == current_provider:
            label = f"✅ {label}"

        buttons.append([InlineKeyboardButton(text=label, callback_data=f"provider:{provider}")])

    buttons.append([InlineKeyboardButton(text="« 返回", callback_data="settings:back")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_model_selector(provider: str, models: list[str], current_model: str | None) -> InlineKeyboardMarkup:
    """模型选择器"""
    buttons = []

    for model in models:
        label = model
        if model == current_model:
            label = f"✅ {label}"

        buttons.append([InlineKeyboardButton(text=label, callback_data=f"model:{provider}:{model}")])

    buttons.append([InlineKeyboardButton(text="« 返回", callback_data="settings:provider")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_settings_menu(permission_mode: str | None = None) -> InlineKeyboardMarkup:
    """设置菜单"""
    permission_label = permission_mode_label(permission_mode)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🤖 切换 AI 服务商", callback_data="settings:provider")],
            [InlineKeyboardButton(text="🎯 选择模型", callback_data="settings:model")],
            [InlineKeyboardButton(text="🌡️ 调整温度参数", callback_data="settings:temperature")],
            [InlineKeyboardButton(text=f"权限:{permission_label}", callback_data="settings:permission")],
            [InlineKeyboardButton(text="📊 查看使用统计", callback_data="settings:stats")],
            [InlineKeyboardButton(text="« 关闭", callback_data="settings:close")],
        ]
    )
    return keyboard


def get_conversation_list_keyboard(conversations: list) -> InlineKeyboardMarkup:
    """对话列表键盘"""
    buttons = []

    for conv in conversations:
        # 截取标题（最多 30 字符）
        title = conv.title[:30] + "..." if len(conv.title) > 30 else conv.title
        status = "🟢" if conv.is_active else "⚪"

        buttons.append([InlineKeyboardButton(text=f"{status} {title}", callback_data=f"conv:load:{conv.id}")])

    buttons.append([InlineKeyboardButton(text="🗑️ 清空历史", callback_data="conv:clear_all")])
    buttons.append([InlineKeyboardButton(text="« 返回", callback_data="conv:back")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_confirmation_keyboard(action: str) -> InlineKeyboardMarkup:
    """确认操作键盘"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ 确认", callback_data=f"confirm:{action}"),
                InlineKeyboardButton(text="❌ 取消", callback_data=f"cancel:{action}"),
            ]
        ]
    )
    return keyboard


def get_help_keyboard() -> InlineKeyboardMarkup:
    """帮助菜单键盘"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📚 使用教程", callback_data="help:tutorial")],
            [InlineKeyboardButton(text="🔧 命令列表", callback_data="help:commands")],
            [InlineKeyboardButton(text="💡 Markdown 语法", callback_data="help:markdown")],
            [InlineKeyboardButton(text="👨‍💻 联系开发者", url="https://t.me/your_channel")],
            [InlineKeyboardButton(text="« 关闭", callback_data="help:close")],
        ]
    )
    return keyboard
