from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from core.orchestrator.chat_tools import permission_mode_label
from i18n import tr, LocaleInfo


def get_main_menu(locale: str | None = None) -> ReplyKeyboardMarkup:
    """主菜单键盘"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=tr("bot.menu.new_chat", locale)), KeyboardButton(text=tr("bot.menu.history", locale))],
            [KeyboardButton(text=tr("bot.menu.settings", locale)), KeyboardButton(text=tr("bot.menu.help", locale))],
        ],
        resize_keyboard=True,
    )
    return keyboard


def get_provider_selector(
    available_providers: list[str],
    current_provider: str,
    locale: str | None = None,
) -> InlineKeyboardMarkup:
    """AI 服务商选择器"""
    buttons = []

    provider_labels = {
        "openai": tr("bot.keyboards.provider_openai", locale),
        "anthropic": tr("bot.keyboards.provider_anthropic", locale),
        "google": tr("bot.keyboards.provider_google", locale),
    }

    for provider in available_providers:
        label = provider_labels.get(provider, provider)
        if provider == current_provider:
            label = tr("bot.keyboards.provider_active", locale, label=label)

        buttons.append([InlineKeyboardButton(text=label, callback_data=f"provider:{provider}")])

    buttons.append([InlineKeyboardButton(text=tr("bot.settings.back", locale), callback_data="settings:back")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_model_selector(
    provider: str,
    models: list[str],
    current_model: str | None,
    locale: str | None = None,
) -> InlineKeyboardMarkup:
    """模型选择器"""
    buttons = []

    for model in models:
        label = model
        if model == current_model:
            label = f"✅ {label}"

        buttons.append([InlineKeyboardButton(text=label, callback_data=f"model:{provider}:{model}")])

    buttons.append([InlineKeyboardButton(text=tr("bot.settings.back", locale), callback_data="settings:provider")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_settings_menu(permission_mode: str | None = None, locale: str | None = None) -> InlineKeyboardMarkup:
    """设置菜单"""
    permission_label = permission_mode_label(permission_mode, locale)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=tr("bot.settings.switch_provider", locale), callback_data="settings:provider")],
            [InlineKeyboardButton(text=tr("bot.settings.select_model", locale), callback_data="settings:model")],
            [InlineKeyboardButton(text=tr("bot.settings.adjust_temperature", locale), callback_data="settings:temperature")],
            [InlineKeyboardButton(text=tr("bot.settings.permission", locale, label=permission_label), callback_data="settings:permission")],
            [InlineKeyboardButton(text=tr("bot.settings.language", locale), callback_data="settings:language")],
            [InlineKeyboardButton(text=tr("bot.settings.stats", locale), callback_data="settings:stats")],
            [InlineKeyboardButton(text=tr("bot.settings.close", locale), callback_data="settings:close")],
        ]
    )
    return keyboard


def get_conversation_list_keyboard(conversations: list, locale: str | None = None) -> InlineKeyboardMarkup:
    """对话列表键盘"""
    buttons = []

    for conv in conversations:
        # 截取标题（最多 30 字符）
        title = conv.title[:30] + "..." if len(conv.title) > 30 else conv.title
        status = "🟢" if conv.is_active else "⚪"

        buttons.append([InlineKeyboardButton(text=f"{status} {title}", callback_data=f"conv:load:{conv.id}")])

    buttons.append([InlineKeyboardButton(text=tr("bot.keyboards.clear_history", locale), callback_data="conv:clear_all")])
    buttons.append([InlineKeyboardButton(text=tr("bot.settings.back", locale), callback_data="conv:back")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_confirmation_keyboard(action: str, locale: str | None = None) -> InlineKeyboardMarkup:
    """确认操作键盘"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=tr("bot.common.confirm", locale), callback_data=f"confirm:{action}"),
                InlineKeyboardButton(text=tr("bot.common.cancel", locale), callback_data=f"cancel:{action}"),
            ]
        ]
    )
    return keyboard


def get_help_keyboard(locale: str | None = None) -> InlineKeyboardMarkup:
    """帮助菜单键盘"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=tr("bot.keyboards.help_tutorial", locale), callback_data="help:tutorial")],
            [InlineKeyboardButton(text=tr("bot.keyboards.help_commands", locale), callback_data="help:commands")],
            [InlineKeyboardButton(text=tr("bot.keyboards.help_markdown", locale), callback_data="help:markdown")],
            [InlineKeyboardButton(text=tr("bot.keyboards.help_contact", locale), url="https://t.me/your_channel")],
            [InlineKeyboardButton(text=tr("bot.common.close", locale), callback_data="help:close")],
        ]
    )
    return keyboard


def get_language_selector(
    available_locales: list[LocaleInfo],
    current_locale: str | None,
    back_callback: str = "settings:back",
    locale: str | None = None,
) -> InlineKeyboardMarkup:
    """Build the language selector inline keyboard.

    Auto-arranges buttons into columns based on count:
    1 locale -> 1 column, 2-4 -> 2 columns, 5+ -> 3 columns.
    Current locale gets a ✅ prefix.
    """
    # Build buttons
    buttons = []
    for info in available_locales:
        label = info.display_name
        if info.locale == current_locale:
            label = f"✅ {label}"
        buttons.append(InlineKeyboardButton(text=label, callback_data=f"lang:set:{info.locale}"))

    # Auto-layout: compute columns
    count = len(buttons)
    if count <= 1:
        columns = 1
    elif count <= 4:
        columns = 2
    else:
        columns = 3

    # Arrange into rows
    rows = []
    for i in range(0, len(buttons), columns):
        rows.append(buttons[i:i + columns])

    # Back button
    rows.append([InlineKeyboardButton(text=tr("bot.settings.back", locale), callback_data=back_callback)])

    return InlineKeyboardMarkup(inline_keyboard=rows)
