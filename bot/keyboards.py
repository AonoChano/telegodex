from unicodedata import east_asian_width

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from core.orchestrator.chat_tools import permission_mode_label
from i18n import LocaleInfo, tr


def _display_width(text: str) -> int:
    """Estimate Telegram button label width across Latin, CJK, and emoji text."""
    width = 0
    for char in text:
        if east_asian_width(char) in {"F", "W"}:
            width += 2
        elif char.isascii():
            width += 1
        else:
            width += 2
    return width


def arrange_inline_buttons(
    buttons: list[InlineKeyboardButton],
    *,
    max_columns: int = 3,
    wide_button_width: int = 24,
    max_row_width: int = 42,
) -> list[list[InlineKeyboardButton]]:
    """Arrange inline buttons into rows with per-row adaptive column counts.

    Instead of forcing a single column count for the whole button list, this
    packs short buttons into multi-column rows and lets long buttons occupy
    their own row. A single long label no longer drags the whole menu into a
    single column.

    Algorithm:
        - Iterate buttons in order. Maintain a current row.
        - A button whose label width >= *wide_button_width* always starts a
          new row (and ends the previous one) — it gets a full-width row.
        - Otherwise, append to the current row if both:
            * adding it would not exceed *max_row_width* (sum of display widths
              plus 1 unit gap between adjacent buttons), and
            * the row has fewer than *max_columns* buttons already.
        - If either constraint is violated, flush the current row and start a
          new one with the button.

    This keeps locale-agnostic layouts compact: short numeric/language labels
    naturally form 3-column rows, mixed settings menus mix 2-column and
    1-column rows, and long descriptive labels stay on their own row.

    Args:
        buttons: Flat list of ``InlineKeyboardButton`` to arrange.
        max_columns: Upper bound on buttons per row.
        wide_button_width: Labels at least this wide force a full-width row.
        max_row_width: Soft cap on the cumulative display width of a row.

    Returns:
        List of rows (each a list of ``InlineKeyboardButton``).
    """
    if not buttons:
        return []

    max_columns = max(1, max_columns)
    rows: list[list[InlineKeyboardButton]] = []
    current_row: list[InlineKeyboardButton] = []
    current_width = 0

    for button in buttons:
        btn_width = _display_width(button.text or "")

        # Wide buttons always get their own row.
        if btn_width >= wide_button_width:
            if current_row:
                rows.append(current_row)
                current_row = []
                current_width = 0
            rows.append([button])
            continue

        # Gap between adjacent buttons in the same row.
        gap = 1 if current_row else 0
        new_width = current_width + gap + btn_width

        # Flush if row would overflow width or column cap.
        if current_row and (new_width > max_row_width or len(current_row) >= max_columns):
            rows.append(current_row)
            current_row = [button]
            current_width = btn_width
        else:
            current_row.append(button)
            current_width = new_width

    if current_row:
        rows.append(current_row)

    return rows


def smart_inline_keyboard(
    buttons: list[InlineKeyboardButton],
    *,
    footer_buttons: list[InlineKeyboardButton] | None = None,
    max_columns: int = 3,
    wide_button_width: int = 24,
) -> InlineKeyboardMarkup:
    """Build an inline keyboard with compact action rows and full-width footer buttons."""
    rows = arrange_inline_buttons(
        buttons,
        max_columns=max_columns,
        wide_button_width=wide_button_width,
    )
    for footer_button in footer_buttons or []:
        rows.append([footer_button])
    return InlineKeyboardMarkup(inline_keyboard=rows)


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

        buttons.append(InlineKeyboardButton(text=label, callback_data=f"provider:{provider}"))

    return smart_inline_keyboard(
        buttons,
        footer_buttons=[InlineKeyboardButton(text=tr("bot.settings.back", locale), callback_data="settings:back")],
        max_columns=2,
    )


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

        buttons.append(InlineKeyboardButton(text=label, callback_data=f"model:{provider}:{model}"))

    return smart_inline_keyboard(
        buttons,
        footer_buttons=[
            InlineKeyboardButton(text=tr("bot.settings.switch_provider", locale), callback_data="settings:provider"),
            InlineKeyboardButton(text=tr("bot.settings.back", locale), callback_data="settings:back"),
        ],
        max_columns=2,
        wide_button_width=30,
    )


def _normalize_temperature_value(value: str | float | int | None) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def get_temperature_selector(current_temperature: str | float | int | None, locale: str | None = None) -> InlineKeyboardMarkup:
    """Temperature selector keyboard."""
    current = _normalize_temperature_value(current_temperature)
    options = [
        ("0.2", "0.2"),
        ("0.5", "0.5"),
        ("0.7", "0.70"),
        ("1.0", "1.0"),
        ("1.3", "1.3"),
    ]
    buttons = []
    for label_value, stored_value in options:
        label = label_value
        option_value = _normalize_temperature_value(stored_value)
        if current is not None and option_value is not None and abs(current - option_value) < 0.001:
            label = f"✅ {label}"
        buttons.append(InlineKeyboardButton(text=label, callback_data=f"temperature:set:{stored_value}"))

    return smart_inline_keyboard(
        buttons,
        footer_buttons=[InlineKeyboardButton(text=tr("bot.settings.back", locale), callback_data="settings:back")],
        max_columns=3,
        wide_button_width=12,
    )


def get_settings_menu(permission_mode: str | None = None, locale: str | None = None) -> InlineKeyboardMarkup:
    """设置菜单"""
    permission_label = permission_mode_label(permission_mode, locale)
    buttons = [
        InlineKeyboardButton(text=tr("bot.settings.switch_provider", locale), callback_data="settings:provider"),
        InlineKeyboardButton(text=tr("bot.settings.select_model", locale), callback_data="settings:model"),
        InlineKeyboardButton(text=tr("bot.settings.adjust_temperature", locale), callback_data="settings:temperature"),
        InlineKeyboardButton(
            text=tr("bot.settings.permission", locale, label=permission_label),
            callback_data="settings:permission",
        ),
        InlineKeyboardButton(text=tr("bot.settings.language", locale), callback_data="settings:language"),
        InlineKeyboardButton(text=tr("bot.settings.stats", locale), callback_data="settings:stats"),
    ]
    return smart_inline_keyboard(
        buttons,
        footer_buttons=[InlineKeyboardButton(text=tr("bot.settings.close", locale), callback_data="settings:close")],
        max_columns=2,
    )


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


def get_language_selector(
    available_locales: list[LocaleInfo],
    current_locale: str | None,
    back_callback: str = "settings:back",
    locale: str | None = None,
) -> InlineKeyboardMarkup:
    """Build the language selector inline keyboard."""
    buttons = []
    for info in available_locales:
        label = info.display_name
        if info.locale == current_locale:
            label = f"✅ {label}"
        buttons.append(InlineKeyboardButton(text=label, callback_data=f"lang:set:{info.locale}"))

    return smart_inline_keyboard(
        buttons,
        footer_buttons=[InlineKeyboardButton(text=tr("bot.settings.back", locale), callback_data=back_callback)],
        max_columns=3,
        wide_button_width=28,
    )
