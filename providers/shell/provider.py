"""Local shell command execution provider."""

from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncIterator
from typing import Any

from loguru import logger


class ShellProvider:
    """Execute shell commands locally via ``asyncio.create_subprocess_shell``."""

    _DANGEROUS_PATTERNS: list[re.Pattern[str]] = [
        re.compile(r"\brm\s+(-[rf]+|--recursive)\b", re.IGNORECASE),
        re.compile(r"\bdd\s+if=", re.IGNORECASE),
        re.compile(r"\bmkfs\b", re.IGNORECASE),
        re.compile(r"\bmkfs\.\w+\b", re.IGNORECASE),
        re.compile(r"\bfdisk\b", re.IGNORECASE),
        re.compile(r">\s*/dev/sd\w", re.IGNORECASE),
        re.compile(r"\bformat\s+\w:", re.IGNORECASE),
        re.compile(r"\bdel\s+/[fqs]\b", re.IGNORECASE),
        re.compile(r"\brd\s+/s\s+/q\b", re.IGNORECASE),
        re.compile(r"\brmdir\s+/s\s+/q\b", re.IGNORECASE),
        re.compile(r"\berase\s+/[fqs]\b", re.IGNORECASE),
        re.compile(r"\bshutdown\b", re.IGNORECASE),
        re.compile(r"\breboot\b", re.IGNORECASE),
        re.compile(r":\(\)\s*{\s*:\|:\s*&\s*}\s*;\s*:\s*", re.IGNORECASE),
    ]

    @classmethod
    def is_dangerous(cls, command: str) -> bool:
        """Detect potentially dangerous shell commands."""
        if not command or not command.strip():
            return False
        for pattern in cls._DANGEROUS_PATTERNS:
            if pattern.search(command):
                return True
        return False

    def __init__(self) -> None:
        self._active_processes: dict[str, asyncio.subprocess.Process] = {}

    def is_running(self, session_id: str) -> bool:
        """Return whether a process is currently running for *session_id*."""
        process = self._active_processes.get(session_id)
        if process is None:
            return False
        return process.returncode is None

    async def send_input(self, session_id: str, data: str) -> None:
        """Send raw input to the stdin of an active process."""
        process = self._active_processes.get(session_id)
        if process is None or process.stdin is None:
            return
        process.stdin.write(data.encode("utf-8"))
        await process.stdin.drain()

    async def terminate(self, session_id: str) -> None:
        """Kill the active process for *session_id*."""
        process = self._active_processes.pop(session_id, None)
        if process is None:
            return
        try:
            process.kill()
            await process.wait()
        except Exception:
            pass

    async def execute(
        self,
        command: str,
        cwd: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Run a shell command and return stdout, stderr, and return code."""
        logger.info(f"ShellProvider execute: {command}")
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        if session_id is not None:
            self._active_processes[session_id] = process
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(), timeout=30.0
            )
        except TimeoutError:
            logger.warning(f"ShellProvider timeout: {command}")
            try:
                process.kill()
                await process.wait()
            except Exception:
                pass
            raise
        finally:
            if session_id is not None:
                self._active_processes.pop(session_id, None)
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        return {
            "stdout": stdout,
            "stderr": stderr,
            "returncode": process.returncode,
        }

    async def execute_streaming(
        self,
        command: str,
        cwd: str | None = None,
        session_id: str | None = None,
    ) -> AsyncIterator[str]:
        """Yield output lines as they arrive from the subprocess."""
        logger.info(f"ShellProvider streaming: {command}")
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        if session_id is not None:
            self._active_processes[session_id] = process
        try:
            async def _read_lines(
                stream: asyncio.StreamReader | None,
            ) -> AsyncIterator[str]:
                if stream is None:
                    return
                while True:
                    try:
                        line = await asyncio.wait_for(stream.readline(), timeout=30.0)
                    except TimeoutError:
                        break
                    if not line:
                        break
                    yield line.decode("utf-8", errors="replace")

            queue: asyncio.Queue[str] = asyncio.Queue()

            async def _enqueue(
                stream: asyncio.StreamReader | None,
                prefix: str,
            ) -> None:
                async for line in _read_lines(stream):
                    await queue.put(prefix + line)

            stdout_task = asyncio.create_task(_enqueue(process.stdout, ""))
            stderr_task = asyncio.create_task(_enqueue(process.stderr, "[stderr] "))

            pending = {stdout_task, stderr_task}
            while pending:
                done, pending = await asyncio.wait(
                    pending, return_when=asyncio.FIRST_COMPLETED
                )
                while not queue.empty():
                    yield queue.get_nowait()
                for task in done:
                    exc = task.exception()
                    if exc:
                        logger.warning(f"ShellProvider stream error: {exc}")

            while not queue.empty():
                yield queue.get_nowait()

            try:
                await asyncio.wait_for(process.wait(), timeout=30.0)
            except TimeoutError:
                logger.warning(f"ShellProvider streaming timeout: {command}")
                try:
                    process.kill()
                    await process.wait()
                except Exception:
                    pass
                raise
        finally:
            if session_id is not None:
                self._active_processes.pop(session_id, None)
