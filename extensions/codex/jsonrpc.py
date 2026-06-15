"""JSON-RPC 2.0 stdio transport for ``codex app-server``.

Newline-delimited JSON, no ``"jsonrpc":"2.0"`` wrapper.  See:
``docs/CodexSourceCode/codex-rs/app-server-protocol/src/jsonrpc_lite.rs``.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from loguru import logger


@dataclass
class _PendingRequest:
    """Tracks an in-flight client request awaiting a server response."""

    event: asyncio.Event = field(default_factory=asyncio.Event)
    result: Any = None
    error: dict[str, Any] | None = None


class JsonRpcError(Exception):
    """JSON-RPC error response."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class JsonRpcTransport:
    """JSON-RPC 2.0 stdio transport for ``codex app-server``.

    Parameters
    ----------
    on_notification:
        Called for every incoming server notification: ``(method, params)``.
    on_server_request:
        Called when the server sends a request that expects a response.
        Must return the result value; the transport sends the response.
        On exception the transport sends a JSON-RPC error response.
    """

    def __init__(
        self,
        on_notification: Callable[[str, dict[str, Any]], Awaitable[None]] | None = None,
        on_server_request: Callable[[str, dict[str, Any]], Awaitable[Any]] | None = None,
    ) -> None:
        self._on_notification = on_notification
        self._on_server_request = on_server_request
        self._reader_task: asyncio.Task[None] | None = None
        self._next_id: int = 1
        self._pending: dict[str | int, _PendingRequest] = {}
        self._writer_lock = asyncio.Lock()
        self._stdout: asyncio.StreamWriter | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, stdin: asyncio.StreamReader, stdout: asyncio.StreamWriter) -> None:
        """Start the reader task over the given stdio streams."""
        self._stdout = stdout
        self._reader_task = asyncio.create_task(self._reader(stdin))
        logger.info("JsonRpcTransport: connected")

    async def close(self) -> None:
        """Stop the reader and cancel all pending futures."""
        if self._reader_task is not None:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
            self._reader_task = None

        for pending in self._pending.values():
            pending.event.set()
        self._pending.clear()
        logger.info("JsonRpcTransport: disconnected")

    # ------------------------------------------------------------------
    # Outgoing
    # ------------------------------------------------------------------

    async def send_request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        """Send a JSON-RPC request and await the response.

        Raises ``JsonRpcError`` when the server responds with an error.
        """
        request_id = self._next_id
        self._next_id += 1

        pending = _PendingRequest()
        self._pending[request_id] = pending

        message: dict[str, Any] = {"id": request_id, "method": method}
        if params is not None:
            message["params"] = params

        await self._write(message)
        await pending.event.wait()

        if pending.error is not None:
            raise JsonRpcError(
                code=pending.error.get("code", -1),
                message=pending.error.get("message", "Unknown error"),
            )
        return pending.result

    async def send_notification(self, method: str, params: dict[str, Any] | None = None) -> None:
        """Send a fire-and-forget JSON-RPC notification."""
        message: dict[str, Any] = {"method": method}
        if params is not None:
            message["params"] = params
        await self._write(message)

    async def send_response(self, request_id: str | int, result: Any) -> None:
        """Send a JSON-RPC success response to a server request."""
        await self._write({"id": request_id, "result": result})

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _write(self, message: dict[str, Any]) -> None:
        """Write a newline-delimited JSON message to stdout."""
        assert self._stdout is not None, "Transport not started"
        line = json.dumps(message, ensure_ascii=False) + "\n"
        async with self._writer_lock:
            self._stdout.write(line.encode("utf-8"))
            await self._stdout.drain()

    async def _reader(self, stdin: asyncio.StreamReader) -> None:
        """Read newline-delimited JSON from stdin and dispatch."""
        try:
            while True:
                line = await stdin.readline()
                if not line:
                    logger.info("JsonRpcTransport: stdin closed")
                    break

                try:
                    message = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError as exc:
                    logger.error(f"JsonRpcTransport: invalid JSON: {exc}")
                    continue

                await self._dispatch(message)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.exception(f"JsonRpcTransport: reader error: {exc}")
        finally:
            for pending in self._pending.values():
                pending.event.set()
            self._pending.clear()

    async def _dispatch(self, message: dict[str, Any]) -> None:
        msg_id = message.get("id")
        method = message.get("method")

        if msg_id is not None and method is not None:
            # Server request → invoke callback, send response
            await self._handle_server_request(msg_id, method, message.get("params", {}))
        elif msg_id is not None:
            # Response to one of our requests
            pending = self._pending.pop(msg_id, None)
            if pending is not None:
                if "result" in message:
                    pending.result = message["result"]
                elif "error" in message:
                    pending.error = message["error"]
                pending.event.set()
        else:
            # Notification
            if self._on_notification is not None and method is not None:
                try:
                    await self._on_notification(method, message.get("params", {}))
                except Exception as exc:
                    logger.exception(
                        f"JsonRpcTransport: notification handler '{method}' failed: {exc}"
                    )

    async def _handle_server_request(
        self, request_id: str | int, method: str, params: dict[str, Any]
    ) -> None:
        if self._on_server_request is None:
            await self._write(
                {
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }
            )
            return
        try:
            result = await self._on_server_request(method, params)
            await self.send_response(request_id, result)
        except Exception as exc:
            logger.exception(f"JsonRpcTransport: server request '{method}' failed: {exc}")
            await self._write(
                {
                    "id": request_id,
                    "error": {"code": -32603, "message": str(exc)},
                }
            )