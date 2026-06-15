"""Codex app-server daemon — manages the persistent ``codex app-server`` subprocess.

Lifecycle:
    Bot start → ``codex app-server --listen stdio://`` → ``initialize`` handshake
    Bot stop  → ``turn/interrupt`` (active turns) → SIGTERM → 3s → SIGKILL
    Crash     → exponential backoff restart (1s/2s/4s, max 3)
"""

from __future__ import annotations

import asyncio
import os
import shutil
from dataclasses import dataclass
from typing import Any

from loguru import logger

from config import settings
from extensions.codex.jsonrpc import JsonRpcError, JsonRpcTransport

_SIGKILL_TIMEOUT = 3.0
_RESTART_BACKOFFS = [1.0, 2.0, 4.0]


def _detect_codex_executable() -> str:
    """Find the ``codex`` executable, respecting CODEX_EXECUTABLE_PATH first."""
    explicit = settings.codex_executable_path
    if explicit:
        candidate = shutil.which(explicit)
        if candidate:
            logger.info(f"Codex executable resolved via config: {candidate}")
            return candidate
        if os.path.isfile(explicit):
            logger.info(f"Codex executable resolved via config: {explicit}")
            return explicit
        logger.warning(
            f"CODEX_EXECUTABLE_PATH={explicit} is not found; falling back to auto-detection"
        )

    # shutil.which("codex") covers Unix and npm global on Windows PATH.
    candidate = shutil.which("codex")
    if candidate:
        logger.info(f"Codex executable auto-detected: {candidate}")
        return candidate

    # Windows fallback: npm global installs (codex.cmd)
    if os.name == "nt":
        appdata = os.environ.get("APPDATA", "")
        npm_cmd = os.path.join(appdata, "npm", "codex.cmd")
        if os.path.isfile(npm_cmd):
            logger.info(f"Codex executable auto-detected (Windows npm): {npm_cmd}")
            return npm_cmd

    # npx fallback
    npx = shutil.which("npx")
    if npx:
        return npx

    raise FileNotFoundError(
        "Codex executable not found. Install Codex CLI or set CODEX_EXECUTABLE_PATH in .env."
    )


class CodexDaemon:
    """Singleton manager for the ``codex app-server`` subprocess.

    Usage::

        daemon = CodexDaemon()
        await daemon.start()

        # Use daemon.transport directly for RPC calls
        result = await daemon.transport.send_request("thread/start", {})
    """

    def __init__(self, executable_path: str | None = None) -> None:
        self._executable = executable_path or _detect_codex_executable()
        self._proc: asyncio.subprocess.Process | None = None
        self._restart_count = 0
        self._startup_done = asyncio.Event()
        self._shutting_down = False
        self._on_shutdown: list[asyncio.Event] = []

        # Transport is created fresh on each start().
        self.transport: JsonRpcTransport | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start ``codex app-server`` and complete the initialization handshake."""
        if self._proc is not None and self.is_alive():
            logger.info("CodexDaemon: already running")
            self._startup_done.set()
            return

        logger.info(f"CodexDaemon: starting {self._executable} app-server --listen stdio://")
        self._startup_done.clear()
        self._shutting_down = False

        try:
            self._proc = await asyncio.create_subprocess_exec(
                self._executable,
                "app-server",
                "--listen",
                "stdio://",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Create a fresh transport wired to the subprocess stdio.
            transport = JsonRpcTransport()
            transport.start(self._proc.stdout, self._proc.stdin)  # type: ignore[arg-type]
            self.transport = transport

            # Handshake: initialize → initialized
            logger.info("CodexDaemon: sending initialize")
            result = await transport.send_request(
                "initialize",
                {
                    "clientInfo": {
                        "name": "telegodex",
                        "title": "Telegodex Telegram Bot",
                        "version": "2.0.0",
                    },
                },
            )
            logger.info(
                f"CodexDaemon: server ready — "
                f"platform={result.get('platformFamily', '?')}/"
                f"{result.get('platformOs', '?')}"
            )

            await transport.send_notification("initialized")

            self._restart_count = 0
            self._startup_done.set()
            logger.info("CodexDaemon: initialized successfully")
        except Exception:
            logger.exception("CodexDaemon: startup failed")
            await self._cleanup()
            self._startup_done.set()  # unblock waiters so they see the failed state
            raise

    async def shutdown(self) -> None:
        """Gracefully shut down the app-server subprocess."""
        self._shutting_down = True
        logger.info("CodexDaemon: shutting down")

        # Notify shutdown listeners.
        for evt in self._on_shutdown:
            evt.set()
        self._on_shutdown.clear()

        if self.transport is not None:
            try:
                await self.transport.close()
            except Exception as exc:
                logger.warning(f"CodexDaemon: transport close error: {exc}")
            self.transport = None

        if self._proc is not None:
            await self._terminate_proc()
        logger.info("CodexDaemon: shutdown complete")

    def is_alive(self) -> bool:
        """Check whether the subprocess is currently running."""
        if self._proc is None:
            return False
        return self._proc.returncode is None

    async def wait_ready(self, timeout: float = 30.0) -> None:
        """Wait until the daemon has completed startup."""
        try:
            await asyncio.wait_for(self._startup_done.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            raise RuntimeError("CodexDaemon did not become ready within timeout")

    def on_shutdown(self) -> asyncio.Event:
        """Return an event that is set when shutdown begins."""
        evt = asyncio.Event()
        self._on_shutdown.append(evt)
        return evt

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _cleanup(self) -> None:
        """Release transport and proc references."""
        if self.transport is not None:
            try:
                await self.transport.close()
            except Exception:
                pass
            self.transport = None
        self._proc = None

    async def _terminate_proc(self) -> None:
        """Send SIGTERM, wait 3s, then SIGKILL."""
        proc = self._proc
        if proc is None or proc.returncode is not None:
            return

        logger.info("CodexDaemon: sending SIGTERM")
        try:
            proc.terminate()
        except ProcessLookupError:
            self._proc = None
            return

        try:
            await asyncio.wait_for(proc.wait(), timeout=_SIGKILL_TIMEOUT)
            logger.info("CodexDaemon: process exited cleanly")
        except asyncio.TimeoutError:
            logger.warning("CodexDaemon: SIGTERM timed out, sending SIGKILL")
            try:
                proc.kill()
                await proc.wait()
            except ProcessLookupError:
                pass
        self._proc = None

    async def _restart(self) -> None:
        """Attempt restart with exponential backoff. Raises on exhaustion."""
        if self._restart_count >= len(_RESTART_BACKOFFS):
            raise RuntimeError(
                f"CodexDaemon: max restarts ({len(_RESTART_BACKOFFS)}) exceeded"
            )

        delay = _RESTART_BACKOFFS[self._restart_count]
        self._restart_count += 1
        logger.warning(
            f"CodexDaemon: restarting in {delay}s "
            f"(attempt {self._restart_count}/{len(_RESTART_BACKOFFS)})"
        )
        await asyncio.sleep(delay)
        await self.start()


# Global singleton — initialized by the bot startup in main.py.
codex_daemon = CodexDaemon()