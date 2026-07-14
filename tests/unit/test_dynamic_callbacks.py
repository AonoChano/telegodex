"""End-to-end tests for tokenized dynamic callback handlers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.handlers import callbacks
from bot.utils.callback_data import encode_callback_data


@pytest.mark.asyncio
async def test_model_handler_resolves_tokenized_model_name() -> None:
    model = "模型-" * 40
    user = SimpleNamespace(
        id=7,
        ui_language="en",
        language_code="en",
        preferred_model=None,
        tool_permission_mode="confirm",
    )
    result = MagicMock()
    result.scalar_one.return_value = user
    session = SimpleNamespace(
        execute=AsyncMock(return_value=result),
        commit=AsyncMock(),
    )
    context = SimpleNamespace(session=session)
    callback = SimpleNamespace(
        data=encode_callback_data("model", f"custom-provider:{model}"),
        from_user=SimpleNamespace(id=7),
        answer=AsyncMock(),
        message=SimpleNamespace(edit_text=AsyncMock()),
    )

    await callbacks.handle_model_change(callback, context)

    assert user.preferred_model == model
    session.commit.assert_awaited_once()
    callback.answer.assert_awaited_once()
    callback.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_model_handler_rejects_unknown_token() -> None:
    user = SimpleNamespace(
        id=7,
        ui_language="en",
        language_code="en",
        preferred_model=None,
        tool_permission_mode="confirm",
    )
    result = MagicMock()
    result.scalar_one.return_value = user
    session = SimpleNamespace(
        execute=AsyncMock(return_value=result),
        commit=AsyncMock(),
    )
    callback = SimpleNamespace(
        data="model:~missing",
        from_user=SimpleNamespace(id=7),
        answer=AsyncMock(),
        message=SimpleNamespace(edit_text=AsyncMock()),
    )

    await callbacks.handle_model_change(callback, SimpleNamespace(session=session))

    assert user.preferred_model is None
    session.commit.assert_not_awaited()
    callback.answer.assert_awaited_once()
    assert callback.answer.await_args.kwargs["show_alert"] is True
    callback.message.edit_text.assert_not_awaited()
