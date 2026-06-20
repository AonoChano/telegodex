"""Unit tests for Codex turn notification consumption."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from core.orchestrator.core import (
    _NOTIFICATION_QUEUES,
    Orchestrator,
    StreamingCallbacks,
)
from core.session import SessionKey


def _orchestrator_for_consume_turn() -> Orchestrator:
    orchestrator = Orchestrator.__new__(Orchestrator)
    orchestrator._session_manager = object()
    orchestrator._approval_handler = MagicMock()
    return orchestrator


async def _consume_with_events(
    events: list[tuple[str, dict]],
    callbacks: StreamingCallbacks,
) -> str:
    key = SessionKey.from_telegram_message(100, 222)
    session = SimpleNamespace(turn_completed=asyncio.Event())
    orchestrator = _orchestrator_for_consume_turn()

    async def _producer() -> None:
        while key not in _NOTIFICATION_QUEUES:
            await asyncio.sleep(0)
        queue = _NOTIFICATION_QUEUES[key]
        for event in events:
            await queue.put(event)

    producer = asyncio.create_task(_producer())
    try:
        return await orchestrator._consume_turn(key, session, callbacks)
    finally:
        await producer
        _NOTIFICATION_QUEUES.pop(key, None)


@pytest.mark.asyncio
async def test_consume_turn_filters_codex_internal_delta() -> None:
    text_deltas: list[tuple[str, str]] = []

    async def on_text_delta(delta: str, accumulated: str) -> None:
        text_deltas.append((delta, accumulated))

    final = await _consume_with_events(
        [
            (
                "item/agentMessage/delta",
                {"delta": "Thinking...Received."},
            ),
            ("item/agentMessage/delta", {"delta": "Visible answer"}),
            ("turn/completed", {"turn": {"status": "completed"}}),
        ],
        StreamingCallbacks(on_text_delta=on_text_delta),
    )

    assert final == "Visible answer"
    assert text_deltas == [("Visible answer", "Visible answer")]


@pytest.mark.asyncio
async def test_consume_turn_streams_command_output_into_final_text() -> None:
    text_deltas: list[tuple[str, str]] = []
    output_deltas: list[tuple[str, str]] = []

    async def on_text_delta(delta: str, accumulated: str) -> None:
        text_deltas.append((delta, accumulated))

    async def on_command_output_delta(delta: str, accumulated: str) -> None:
        output_deltas.append((delta, accumulated))

    final = await _consume_with_events(
        [
            (
                "item/started",
                {
                    "item": {
                        "id": "cmd-1",
                        "type": "commandExecution",
                        "command": "pytest",
                    }
                },
            ),
            ("item/commandExecution/outputDelta", {"delta": "tests passed\n"}),
            (
                "item/completed",
                {
                    "item": {
                        "id": "cmd-1",
                        "type": "commandExecution",
                        "exitCode": 0,
                    }
                },
            ),
            ("turn/completed", {"turn": {"status": "completed"}}),
        ],
        StreamingCallbacks(
            on_text_delta=on_text_delta,
            on_command_output_delta=on_command_output_delta,
        ),
    )

    assert "pytest" in final
    assert "tests passed" in final
    assert "Success" in final
    assert text_deltas == [
        ("tests passed\n", text_deltas[0][1]),
    ]
    assert "Exec" in text_deltas[0][1]
    assert "pytest" in text_deltas[0][1]
    assert "tests passed" in text_deltas[0][1]
    assert output_deltas == [("tests passed\n", "tests passed\n")]


@pytest.mark.asyncio
async def test_consume_turn_surfaces_app_server_retry_error_without_polluting_final_text() -> None:
    codex_errors: list[tuple[str, str | None, bool]] = []
    detail = (
        "unexpected status 403 Forbidden: quota exhausted "
        "(traceid: trace-123), url: https://new.sharedchat.cc/codex/responses, cf-ray: ray-KIX"
    )

    async def on_codex_error(message: str, additional_details: str | None, will_retry: bool) -> None:
        codex_errors.append((message, additional_details, will_retry))

    final = await _consume_with_events(
        [
            (
                "error",
                {
                    "threadId": "thread-1",
                    "turnId": "turn-1",
                    "willRetry": True,
                    "error": {
                        "message": "Reconnecting... 1/5",
                        "codexErrorInfo": "other",
                        "additionalDetails": detail,
                    },
                },
            ),
            ("turn/completed", {"turn": {"status": "completed"}}),
        ],
        StreamingCallbacks(on_codex_error=on_codex_error),
    )

    assert final == "Codex completed with no output."
    assert codex_errors == [("Reconnecting... 1/5", detail, True)]
