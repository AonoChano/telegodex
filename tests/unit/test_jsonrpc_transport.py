"""Tests for ``extensions.codex.jsonrpc.JsonRpcTransport``.

Covers the reader-non-blocking contract for server requests: a long-running
``on_server_request`` handler must NOT stall the reader loop, otherwise
subsequent notifications (e.g. ``item/agentMessage/delta``) pile up in the
socket buffer and streaming appears frozen.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from extensions.codex.jsonrpc import JsonRpcTransport


def _encode(obj: Any) -> bytes:
    import json

    return (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")


class _StreamWriterSpy:
    """Minimal StreamWriter stand-in that records outgoing lines."""

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    def write(self, data: bytes) -> None:
        import json

        for line in data.decode("utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            self.sent.append(json.loads(line))

    async def drain(self) -> None:
        return None


@pytest.mark.asyncio
async def test_server_request_does_not_block_subsequent_notifications() -> None:
    """A pending server request must not stall the reader.

    Reproduces the streaming-freeze root cause: when ``on_server_request``
    awaits a long-lived event (e.g. user approval, up to 60s), the reader
    must keep draining the stream so notifications still arrive on time.
    """
    reader = asyncio.StreamReader()
    writer = _StreamWriterSpy()
    transport = JsonRpcTransport()
    transport.start(reader, writer)

    arrivals: list[str] = []
    approval_event = asyncio.Event()

    async def on_notification(method: str, params: dict[str, Any]) -> None:
        arrivals.append(method)

    async def on_server_request(method: str, params: dict[str, Any]) -> Any:
        await asyncio.wait_for(approval_event.wait(), timeout=5.0)
        return {"decision": "decline"}

    transport._on_notification = on_notification
    transport._on_server_request = on_server_request

    # Feed stdin: one server request (id=1) then two notifications.
    reader.feed_data(_encode({"id": 1, "method": "item/commandExecution/requestApproval", "params": {}}))
    reader.feed_data(_encode({"method": "item/agentMessage/delta", "params": {"delta": "hi"}}))
    reader.feed_data(_encode({"method": "item/agentMessage/delta", "params": {"delta": "!"}}))

    # Give the reader a chance to process all lines without the request done.
    await asyncio.sleep(0.3)

    # Critical assertion: notifications arrived even though the request
    # handler is still blocked on approval_event.
    assert "item/agentMessage/delta" in arrivals, (
        "reader stalled by pending server request; notifications not drained"
    )
    assert arrivals.count("item/agentMessage/delta") == 2

    approval_event.set()
    await asyncio.sleep(0.1)
    await transport.close()


@pytest.mark.asyncio
async def test_server_request_still_sends_response_after_completion() -> None:
    """Response is sent exactly once, after the handler completes."""
    reader = asyncio.StreamReader()
    writer = _StreamWriterSpy()
    transport = JsonRpcTransport()
    transport.start(reader, writer)

    release = asyncio.Event()

    async def on_server_request(method: str, params: dict[str, Any]) -> Any:
        await asyncio.wait_for(release.wait(), timeout=5.0)
        return {"decision": "accept"}

    transport._on_server_request = on_server_request

    reader.feed_data(_encode({"id": 7, "method": "item/commandExecution/requestApproval", "params": {}}))
    await asyncio.sleep(0.2)

    # No response yet while handler is blocked.
    assert writer.sent == []

    release.set()
    await asyncio.sleep(0.2)

    # Exactly one response with the right id and result.
    assert len(writer.sent) == 1
    resp = writer.sent[0]
    assert resp["id"] == 7
    assert resp["result"] == {"decision": "accept"}
    await transport.close()


@pytest.mark.asyncio
async def test_close_cancels_in_flight_server_request_task() -> None:
    """``close()`` must cancel a pending server-request handler promptly."""
    reader = asyncio.StreamReader()
    writer = _StreamWriterSpy()
    transport = JsonRpcTransport()
    transport.start(reader, writer)

    started = asyncio.Event()

    async def on_server_request(method: str, params: dict[str, Any]) -> Any:
        started.set()
        await asyncio.sleep(30)  # would hang if not cancelled
        return {"decision": "accept"}

    transport._on_server_request = on_server_request
    reader.feed_data(_encode({"id": 9, "method": "item/fileChange/requestApproval", "params": {}}))
    await asyncio.wait_for(started.wait(), timeout=2.0)

    # close() should return promptly instead of waiting 30s.
    await asyncio.wait_for(transport.close(), timeout=3.0)
