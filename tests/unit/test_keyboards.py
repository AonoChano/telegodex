from aiogram.types import InlineKeyboardButton

from bot.keyboards import (
    arrange_inline_buttons,
    get_language_selector,
    get_model_selector,
    get_provider_selector,
    get_settings_menu,
    get_temperature_selector,
)
from i18n import LocaleInfo


def _buttons(count: int) -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=f"B{i}", callback_data=f"b:{i}") for i in range(count)]


def _row_lengths(markup) -> list[int]:
    return [len(row) for row in markup.inline_keyboard]


def test_arrange_inline_buttons_uses_three_columns_for_many_short_labels() -> None:
    rows = arrange_inline_buttons(_buttons(7))

    assert [len(row) for row in rows] == [3, 3, 1]


def test_arrange_inline_buttons_keeps_wide_labels_single_column() -> None:
    buttons = [
        InlineKeyboardButton(text="Extremely long action label", callback_data="a"),
        InlineKeyboardButton(text="Another extremely long label", callback_data="b"),
    ]

    rows = arrange_inline_buttons(buttons)

    assert [len(row) for row in rows] == [1, 1]


def test_settings_menu_uses_mobile_friendly_mixed_rows() -> None:
    markup = get_settings_menu("confirm", "zh-cn")

    assert _row_lengths(markup) == [1, 2, 1, 1, 1, 1]
    assert markup.inline_keyboard[0][0].callback_data == "settings:provider"
    assert [button.callback_data for button in markup.inline_keyboard[1]] == [
        "settings:model",
        "settings:language",
    ]
    assert markup.inline_keyboard[3][0].callback_data == "settings:permission"
    assert markup.inline_keyboard[-1][0].callback_data == "settings:close"


def test_language_selector_uses_three_columns_for_many_short_locales() -> None:
    locales = [
        LocaleInfo(locale="en", display_name="EN"),
        LocaleInfo(locale="zh-cn", display_name="ZH"),
        LocaleInfo(locale="ja", display_name="JA"),
        LocaleInfo(locale="ko", display_name="KO"),
        LocaleInfo(locale="fr", display_name="FR"),
        LocaleInfo(locale="de", display_name="DE"),
        LocaleInfo(locale="es", display_name="ES"),
    ]

    markup = get_language_selector(locales, "en", locale="en")

    assert _row_lengths(markup) == [3, 3, 1, 1]
    assert markup.inline_keyboard[-1][0].callback_data == "settings:back"


def test_provider_selector_uses_pairs_with_full_width_back() -> None:
    markup = get_provider_selector(["openai", "anthropic", "deepseek"], "openai", "en")

    # "✅ 🟢 OpenAI (GPT)" (18) + "🔵 Anthropic (Claude)" (21) = 40 <= 42 row width,
    # so they pair up; the shorter "deepseek" (8) gets its own row.
    assert _row_lengths(markup) == [2, 1, 1]
    assert markup.inline_keyboard[-1][0].callback_data == "settings:back"

def test_model_selector_uses_compact_rows_with_provider_and_settings_footer() -> None:
    markup = get_model_selector("deepseek", ["chat", "coder", "reasoner"], "coder", "en")

    assert _row_lengths(markup) == [2, 1, 1, 1]
    assert markup.inline_keyboard[-2][0].callback_data == "settings:provider"
    assert markup.inline_keyboard[-1][0].callback_data == "settings:back"


def test_model_selector_keeps_long_model_names_single_column() -> None:
    markup = get_model_selector(
        "deepseek",
        ["deepseek-extremely-long-model-name", "deepseek-another-long-model-name"],
        None,
        "en",
    )

    assert _row_lengths(markup) == [1, 1, 1, 1]


def test_temperature_selector_marks_current_value_and_keeps_back_footer() -> None:
    markup = get_temperature_selector("0.70", "en")

    # Five short numeric labels pack into [3, 2] under the adaptive layout,
    # plus the full-width back button on its own row.
    assert _row_lengths(markup) == [3, 2, 1]
    # ✅ prefix is on the "0.70" button (3rd button, index 2)
    flat = [btn for row in markup.inline_keyboard for btn in row]
    marked = [btn for btn in flat if btn.text.startswith("✅")]
    assert len(marked) == 1
    assert marked[0].callback_data == "temperature:set:0.70"
    assert markup.inline_keyboard[-1][0].callback_data == "settings:back"
