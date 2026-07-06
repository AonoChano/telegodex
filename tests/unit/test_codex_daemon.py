"""Smoke tests for the Codex app-server daemon lifecycle."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import pytest

import extensions.codex.daemon as daemon_module
from extensions.codex.daemon import CodexDaemon


class _FakeTransport:
    instances: list[_FakeTransport] = []

    def __init__(self) -> None:
        self.started_with: tuple[Any, Any] | None = None
        self.requests: list[tuple[str, dict[str, Any] | None]] = []
        self.notifications: list[tuple[str, dict[str, Any] | None]] = []
        self.closed = False
        _FakeTransport.instances.append(self)

    def start(self, stdin: Any, stdout: Any) -> None:
        self.started_with = (stdin, stdout)

    async def send_request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        self.requests.append((method, params))
        if method == "initialize":
            return {"platformFamily": "test", "platformOs": "test-os"}
        return {}

    async def send_notification(self, method: str, params: dict[str, Any] | None = None) -> None:
        self.notifications.append((method, params))

    async def close(self) -> None:
        self.closed = True


class _FakeProcess:
    def __init__(self) -> None:
        self.stdin = object()
        self.stdout = object()
        self.stderr = asyncio.StreamReader()
        self.stderr.feed_eof()
        self.returncode: int | None = None
        self.terminate_calls = 0
        self.kill_calls = 0
        self._wait_done = asyncio.Event()

    def terminate(self) -> None:
        self.terminate_calls += 1
        self.returncode = 0
        self._wait_done.set()

    def kill(self) -> None:
        self.kill_calls += 1
        self.returncode = -9
        self._wait_done.set()

    async def wait(self) -> int | None:
        await self._wait_done.wait()
        return self.returncode


@pytest.fixture(autouse=True)
def fake_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeTransport.instances.clear()
    monkeypatch.setattr(daemon_module, "JsonRpcTransport", _FakeTransport)


@pytest.mark.asyncio
async def test_start_performs_initialize_handshake_and_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    process = _FakeProcess()

    async def create_subprocess_exec(*args: Any, **kwargs: Any) -> _FakeProcess:
        created.append((args, kwargs))
        return process

    monkeypatch.setattr(daemon_module.asyncio, "create_subprocess_exec", create_subprocess_exec)

    daemon = CodexDaemon(executable_path="codex-test")
    await daemon.start()

    assert daemon.is_alive() is True
    assert created[0][0] == ("codex-test", "app-server", "--listen", "stdio://")
    assert _FakeTransport.instances[0].started_with == (process.stdout, process.stdin)
    assert _FakeTransport.instances[0].requests == [
        (
            "initialize",
            {
                "clientInfo": {
                    "name": "telegodex",
                    "title": "Telegodex Telegram Bot",
                    "version": "2.0.0",
                }
            },
        )
    ]
    assert _FakeTransport.instances[0].notifications == [("initialized", None)]

    await daemon.shutdown()

    assert _FakeTransport.instances[0].closed is True
    assert process.terminate_calls == 1
    assert process.kill_calls == 0
    assert daemon.transport is None
    assert daemon.is_alive() is False


@pytest.mark.asyncio
async def test_start_is_idempotent_when_process_is_alive(monkeypatch: pytest.MonkeyPatch) -> None:
    async def create_subprocess_exec(*args: Any, **kwargs: Any) -> _FakeProcess:
        raise AssertionError("start should not spawn a second process while alive")

    monkeypatch.setattr(daemon_module.asyncio, "create_subprocess_exec", create_subprocess_exec)

    daemon = CodexDaemon(executable_path="codex-test")
    daemon._proc = _FakeProcess()

    await daemon.start()
    await daemon.wait_ready(timeout=0.1)

    assert _FakeTransport.instances == []


@pytest.mark.asyncio
async def test_shutdown_sets_listeners_before_process_termination() -> None:
    daemon = CodexDaemon(executable_path="codex-test")
    process = _FakeProcess()
    transport = _FakeTransport()
    shutdown_event = daemon.on_shutdown()
    daemon._proc = process
    daemon.transport = transport  # type: ignore[assignment]

    await daemon.shutdown()

    assert shutdown_event.is_set() is True
    assert transport.closed is True
    assert process.terminate_calls == 1


@pytest.mark.asyncio
async def test_restart_waits_backoff_before_start(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[float] = []

    async def sleep(delay: float) -> None:
        sleeps.append(delay)

    daemon = CodexDaemon(executable_path="codex-test")
    start = AsyncMock()
    monkeypatch.setattr(daemon_module.asyncio, "sleep", sleep)
    monkeypatch.setattr(daemon, "start", start)

    await daemon._restart()

    assert sleeps == [1.0]
    start.assert_awaited_once()
    assert daemon._restart_count == 1
