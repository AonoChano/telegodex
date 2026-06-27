"""Unit tests for providers.shell.provider.ShellProvider."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from providers.shell import provider as shell_provider_module
from providers.shell.provider import ShellProvider, _platform_shell_command


def test_windows_commands_are_wrapped_with_powershell(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shell_provider_module.os, "name", "nt", raising=False)

    wrapped = _platform_shell_command("Start-Process notepad")

    assert wrapped.startswith("powershell.exe")
    assert "-NoProfile" in wrapped
    assert "-Command" in wrapped
    assert "Start-Process notepad" in wrapped


class TestDangerousCommandDetection:
    """Cover ``ShellProvider.is_dangerous``."""

    @pytest.mark.parametrize(
        "command,expected",
        [
            ("", False),
            ("   ", False),
            ("echo hello", False),
            ("ls -la", False),
            ("rm -rf /", True),
            ("RM -Rf /home", True),
            ("dd if=/dev/zero of=/dev/sda", True),
            ("mkfs.ext4 /dev/sdb1", True),
            ("fdisk /dev/sda", True),
            ("echo foo > /dev/sda", True),  # pattern allows space before /dev/sd
            ("format C:", True),
            ("del /f /q file.txt", True),
            ("rd /s /q folder", True),
            ("rmdir /s /q folder", True),
            ("erase /f file.txt", True),
            ("shutdown now", True),
            ("reboot", True),
            (":(){ :|: & };:", True),
        ],
    )
    def test_is_dangerous(self, command: str, expected: bool) -> None:
        assert ShellProvider.is_dangerous(command) is expected


class TestExecute:
    """Cover ``ShellProvider.execute`` with mocked subprocess."""

    @pytest.mark.asyncio
    async def test_execute_success(self) -> None:
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"hello stdout", b""))
        mock_process.returncode = 0

        with patch(
            "asyncio.create_subprocess_shell",
            new=AsyncMock(return_value=mock_process),
        ):
            provider = ShellProvider()
            result = await provider.execute("echo hello")

        assert result["stdout"] == "hello stdout"
        assert result["stderr"] == ""
        assert result["returncode"] == 0

    @pytest.mark.asyncio
    async def test_execute_with_stderr(self) -> None:
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"", b"error msg"))
        mock_process.returncode = 1

        with patch(
            "asyncio.create_subprocess_shell",
            new=AsyncMock(return_value=mock_process),
        ):
            provider = ShellProvider()
            result = await provider.execute("false")

        assert result["stdout"] == ""
        assert result["stderr"] == "error msg"
        assert result["returncode"] == 1

    @pytest.mark.asyncio
    async def test_execute_timeout(self) -> None:
        mock_process = MagicMock()
        mock_process.kill = MagicMock()
        mock_process.wait = AsyncMock()

        with (
            patch(
                "asyncio.create_subprocess_shell",
                new=AsyncMock(return_value=mock_process),
            ),
            patch(
                "asyncio.wait_for",
                new=AsyncMock(side_effect=TimeoutError),
            ),
        ):
            provider = ShellProvider()
            with pytest.raises(TimeoutError):
                await provider.execute("sleep 100")

        mock_process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_tracks_session(self) -> None:
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"out", b""))
        mock_process.returncode = 0

        with patch(
            "asyncio.create_subprocess_shell",
            new=AsyncMock(return_value=mock_process),
        ):
            provider = ShellProvider()
            assert not provider.is_running("sess-1")
            result = await provider.execute("echo x", session_id="sess-1")
            assert not provider.is_running("sess-1")

        assert result["stdout"] == "out"


class TestExecuteStreaming:
    """Cover ``ShellProvider.execute_streaming``."""

    @pytest.mark.asyncio
    async def test_execute_streaming_yields_lines(self) -> None:
        stdout_reader = asyncio.StreamReader()
        stdout_reader.feed_data(b"line one\nline two\n")
        stdout_reader.feed_eof()

        stderr_reader = asyncio.StreamReader()
        stderr_reader.feed_eof()

        mock_process = MagicMock()
        mock_process.stdout = stdout_reader
        mock_process.stderr = stderr_reader
        mock_process.wait = AsyncMock(return_value=0)

        with patch(
            "asyncio.create_subprocess_shell",
            new=AsyncMock(return_value=mock_process),
        ):
            provider = ShellProvider()
            lines = [line async for line in provider.execute_streaming("echo test")]

        assert "line one\n" in lines
        assert "line two\n" in lines

    @pytest.mark.asyncio
    async def test_execute_streaming_stderr_prefix(self) -> None:
        stdout_reader = asyncio.StreamReader()
        stdout_reader.feed_eof()

        stderr_reader = asyncio.StreamReader()
        stderr_reader.feed_data(b"error here\n")
        stderr_reader.feed_eof()

        mock_process = MagicMock()
        mock_process.stdout = stdout_reader
        mock_process.stderr = stderr_reader
        mock_process.wait = AsyncMock(return_value=0)

        with patch(
            "asyncio.create_subprocess_shell",
            new=AsyncMock(return_value=mock_process),
        ):
            provider = ShellProvider()
            lines = [line async for line in provider.execute_streaming("cmd")]

        assert any("[stderr] error here" in line for line in lines)

    @pytest.mark.asyncio
    async def test_execute_streaming_timeout(self) -> None:
        stdout_reader = asyncio.StreamReader()
        stdout_reader.feed_eof()

        mock_process = MagicMock()
        mock_process.stdout = stdout_reader
        mock_process.stderr = asyncio.StreamReader()
        mock_process.stderr.feed_eof()
        mock_process.kill = MagicMock()
        mock_process.wait = AsyncMock()

        with (
            patch(
                "asyncio.create_subprocess_shell",
                new=AsyncMock(return_value=mock_process),
            ),
            patch(
                "asyncio.wait_for",
                new=AsyncMock(side_effect=TimeoutError),
            ),
        ):
            provider = ShellProvider()
            with pytest.raises(TimeoutError):
                async for _ in provider.execute_streaming("sleep 100"):
                    pass

        mock_process.kill.assert_called_once()


class TestSendInputAndTerminate:
    """Cover interactive process control."""

    @pytest.mark.asyncio
    async def test_send_input(self) -> None:
        mock_stdin = MagicMock()
        mock_stdin.drain = AsyncMock()
        mock_process = MagicMock()
        mock_process.stdin = mock_stdin
        mock_process.returncode = None

        provider = ShellProvider()
        provider._active_processes["sess"] = mock_process

        await provider.send_input("sess", "hello\n")
        mock_stdin.write.assert_called_once_with(b"hello\n")
        mock_stdin.drain.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_input_missing_process(self) -> None:
        provider = ShellProvider()
        # Should not raise
        await provider.send_input("missing", "data")

    @pytest.mark.asyncio
    async def test_terminate(self) -> None:
        mock_process = MagicMock()
        mock_process.kill = MagicMock()
        mock_process.wait = AsyncMock()

        provider = ShellProvider()
        provider._active_processes["sess"] = mock_process

        await provider.terminate("sess")
        mock_process.kill.assert_called_once()
        assert "sess" not in provider._active_processes

    @pytest.mark.asyncio
    async def test_terminate_missing_session(self) -> None:
        provider = ShellProvider()
        # Should not raise
        await provider.terminate("missing")
