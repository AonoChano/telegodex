from __future__ import annotations

import asyncio
import io
import os
from types import SimpleNamespace

from aiogram.utils.backoff import BackoffConfig

from main import (
    _AiogramPollingRetryCompactor,
    _await_polling_response,
    _classify_polling_error,
    _fit_terminal_status_text,
    _format_duration,
    _format_reconnect_status,
    _format_retry_limit,
    _parse_aiogram_retry_sleep,
    _TelegodexDispatcher,
    _TerminalStatusLine,
    _visible_width,
    _wait_for_bot_identity,
    _wrap_terminal_status_text,
)


class _FakeStatusLine:
    enabled = True

    def __init__(self) -> None:
        self.updates: list[str] = []
        self.clears = 0

    def update(self, text: str) -> None:
        self.updates.append(text)

    def clear(self) -> None:
        self.clears += 1


# ── _classify_polling_error ────────────────────────────────────────────


def test_classify_polling_error_network() -> None:
    message = (
        "Failed to fetch updates - TelegramNetworkError: HTTP Client says - "
        "ClientConnectorError: Cannot connect to host api.telegram.org:443 ssl:default [None]"
    )
    category, error_type, hint, detail = _classify_polling_error(message)
    assert category == "network"
    assert error_type == "TelegramNetworkError"
    assert "Cannot connect to host" in detail


def test_classify_polling_error_auth() -> None:
    message = "Failed to fetch updates - TelegramUnauthorizedError: Not Found"
    category, error_type, hint, detail = _classify_polling_error(message)
    assert category == "auth"
    assert error_type == "TelegramUnauthorizedError"
    assert "TELEGRAM_BOT_TOKEN" in hint


def test_classify_polling_error_strips_noisy_prefixes() -> None:
    message = (
        "Failed to fetch updates - TelegramNetworkError: HTTP Client says - "
        "ClientOSError: [WinError 1236] network connection aborted"
    )
    _, _, _, detail = _classify_polling_error(message)
    assert "HTTP Client says" not in detail
    assert "ClientOSError" not in detail
    assert "WinError 1236" in detail


def test_classify_polling_error_unknown_exception() -> None:
    message = "Failed to fetch updates - SomeNewError: something broke"
    category, error_type, hint, detail = _classify_polling_error(message)
    assert category == "unknown"
    assert error_type == "SomeNewError"
    assert detail == "something broke"



def test_classify_polling_error_phase_variant() -> None:
    message = (
        "Failed to fetch updates - TelegramNetworkError after 3.104s during "
        "startup getMe #2: HTTP Client says - Request timeout error"
    )
    category, error_type, _, detail = _classify_polling_error(message)
    assert category == "network"
    assert error_type == "TelegramNetworkError"
    assert "startup getMe #2 after 3.104s" in detail
    assert "Request timeout error" in detail


def test_classify_polling_error_startup_getme_detail() -> None:
    message = (
        "Failed to fetch updates - TelegramNetworkError: startup getMe #2 "
        "failed after 3.104s: HTTP Client says - Request timeout error"
    )
    category, error_type, _, detail = _classify_polling_error(message)
    assert category == "network"
    assert error_type == "TelegramNetworkError"
    assert "startup getMe #2 failed after 3.104s" in detail
    assert "Request timeout error" in detail

# ── _format_retry_limit ────────────────────────────────────────────────


def test_format_retry_limit_unlimited() -> None:
    assert _format_retry_limit("network") == "∞"
    assert _format_retry_limit("rate_limit") == "∞"


def test_format_retry_limit_finite() -> None:
    assert _format_retry_limit("auth") == "5"
    assert _format_retry_limit("server") == "10"
    assert _format_retry_limit("unknown") == "10"


# ── _format_reconnect_status ───────────────────────────────────────────


def test_format_reconnect_status_with_countdown() -> None:
    text = _format_reconnect_status(
        "auth", "TelegramForbiddenError", "Bot was kicked", 2, 3.2, 12.4
    )
    assert "Reconnecting" in text
    assert "2/5" in text
    assert "retry in 3s" in text
    assert "12s" in text
    assert "TelegramForbiddenError" in text
    assert "\033[0m" in text  # ANSI reset


def test_format_reconnect_status_probing() -> None:
    text = _format_reconnect_status(
        "network", "TelegramNetworkError", "", 1, 0.0, 5.0
    )
    assert "1/∞" in text
    assert "probing" in text


def test_format_reconnect_status_duration_rolls_up() -> None:
    text = _format_reconnect_status(
        "network", "TelegramNetworkError", "timeout", 2, 0.0, 65.0
    )
    assert "2/∞" in text
    assert "probing" in text
    assert "1m05s" in text


def test_format_reconnect_status_unlimited_limit() -> None:
    text = _format_reconnect_status(
        "network", "TelegramNetworkError", "timeout", 7, 2.0, 15.0
    )
    assert "7/∞" in text



def test_format_duration_rolls_up_units() -> None:
    assert _format_duration(0.2) == "0s"
    assert _format_duration(72.4) == "1m12s"
    assert _format_duration(3723) == "1h02m03s"

# ── status text wrapping / _TerminalStatusLine ────────────────────────


def test_fit_terminal_status_text_uses_ascii_ellipsis() -> None:
    assert _fit_terminal_status_text("abcdefghij", 8) == "abcde..."


def test_fit_terminal_status_text_ansi_aware() -> None:
    text = _format_reconnect_status(
        "network", "TelegramNetworkError", "timeout", 1, 3.2, 12.4
    )
    truncated = _fit_terminal_status_text(text, 20)
    assert _visible_width(truncated) == 20
    assert truncated.endswith("\033[0m...")
    assert "Reconnecting" in truncated


def test_fit_terminal_status_text_cjk_double_width() -> None:
    text = _format_reconnect_status(
        "network",
        "TelegramNetworkError",
        "[WinError 1236] 由本地系统终止网络连接",
        1,
        3.2,
        12.4,
    )
    truncated = _fit_terminal_status_text(text, 40)
    assert _visible_width(truncated) <= 40
    assert truncated.endswith("\033[0m...")



def test_wrap_terminal_status_text_keeps_full_detail() -> None:
    text = _format_reconnect_status(
        "network",
        "TelegramNetworkError",
        "Request timeout error with enough extra detail to wrap",
        2,
        0.0,
        65.0,
    )
    lines = _wrap_terminal_status_text(text, 38)
    assert len(lines) > 1
    assert "Request timeout error" in "".join(lines)
    assert all(_visible_width(line) <= 38 for line in lines)


def test_terminal_status_line_replaces_known_physical_rows(monkeypatch) -> None:
    stream = io.StringIO()
    stream.isatty = lambda: True
    monkeypatch.setattr("main.sys.stderr", stream)
    monkeypatch.setattr(
        "main.shutil.get_terminal_size",
        lambda fallback: os.terminal_size((60, 20)),
    )

    status = _TerminalStatusLine()
    long_detail = "TelegramNetworkError: " + "Request timeout " * 8
    status.update("Telegram polling | " + long_detail)
    status.update("Telegram polling / Telegram API unreachable (2/∞), retry in 2.3s")

    output = stream.getvalue()
    assert output.count("\033[2K") == 3
    assert output.count("\033[1A") == 2
    assert "Request timeout Request timeout" in output
    assert "Telegram API unreachable" in output

# ── _AiogramPollingRetryCompactor state machine ────────────────────────


def test_compactor_transitions_to_reconnecting_on_error(monkeypatch) -> None:
    """错误消息触发 IDLE → RECONNECTING。"""
    status = _FakeStatusLine()
    compactor = _AiogramPollingRetryCompactor(status)  # type: ignore[arg-type]
    now = 100.0
    monkeypatch.setattr("main.time.monotonic", lambda: now)
    compactor._start_worker = lambda gen: None  # 避免启动真实线程

    result = compactor.handle(
        "Failed to fetch updates - TelegramNetworkError: HTTP Client says - "
        "ClientConnectorError: Cannot connect to host api.telegram.org:443 ssl:default [None]"
    )
    assert result is True
    assert compactor._state == "RECONNECTING"
    assert compactor._category == "network"
    assert compactor._attempt == 1
    assert compactor._error_type == "TelegramNetworkError"


def test_compactor_increments_attempt_on_repeated_error(monkeypatch) -> None:
    """同一周期内连续错误递增 attempt。"""
    status = _FakeStatusLine()
    compactor = _AiogramPollingRetryCompactor(status)  # type: ignore[arg-type]
    now = 100.0
    monkeypatch.setattr("main.time.monotonic", lambda: now)
    compactor._start_worker = lambda gen: None

    compactor.handle("Failed to fetch updates - TelegramNetworkError: timeout")
    assert compactor._attempt == 1

    compactor.handle("Failed to fetch updates - TelegramNetworkError: timeout")
    assert compactor._attempt == 2


def test_compactor_handles_reconnected(monkeypatch) -> None:
    """Connection established 触发 success 日志并回到 IDLE。"""
    status = _FakeStatusLine()
    compactor = _AiogramPollingRetryCompactor(status)  # type: ignore[arg-type]
    now = 100.0
    monkeypatch.setattr("main.time.monotonic", lambda: now)
    compactor._start_worker = lambda gen: None

    compactor.handle("Failed to fetch updates - TelegramNetworkError: timeout")

    now = 105.0  # 5 秒后重连成功
    compactor.handle("Connection established (tryings = 1, bot id = 123)")

    assert compactor._state == "IDLE"
    assert status.clears >= 1


def test_compactor_handles_sleep_updates_deadline(monkeypatch) -> None:
    """Sleep 消息更新 retry_deadline 和 attempt。"""
    status = _FakeStatusLine()
    compactor = _AiogramPollingRetryCompactor(status)  # type: ignore[arg-type]
    now = 100.0
    monkeypatch.setattr("main.time.monotonic", lambda: now)
    compactor._start_worker = lambda gen: None

    compactor.handle("Failed to fetch updates - TelegramNetworkError: timeout")
    assert compactor._retry_deadline == 102.0  # 100 + _PENDING_RETRY_SECONDS

    compactor.handle(
        "Sleep for 5.0 seconds and try again... (tryings = 1, bot id = 123)"
    )
    assert compactor._retry_deadline == 105.0  # 100 + 5.0
    assert compactor._attempt >= 1


def test_compactor_render_shows_status_in_reconnecting(monkeypatch) -> None:
    """RECONNECTING 状态下 _render_status_once 渲染状态行。"""
    status = _FakeStatusLine()
    compactor = _AiogramPollingRetryCompactor(status)  # type: ignore[arg-type]
    now = 100.0
    monkeypatch.setattr("main.time.monotonic", lambda: now)
    compactor._start_worker = lambda gen: None

    compactor.handle("Failed to fetch updates - TelegramNetworkError: timeout")

    gen = compactor._worker_generation
    assert compactor._render_status_once(gen) is True
    assert len(status.updates) == 1
    assert "Reconnecting" in status.updates[0]


def test_compactor_render_returns_false_in_idle() -> None:
    """IDLE 状态下 _render_status_once 返回 False，不调用 clear。"""
    status = _FakeStatusLine()
    compactor = _AiogramPollingRetryCompactor(status)  # type: ignore[arg-type]
    assert compactor._render_status_once(0) is False
    assert status.clears == 0


def test_compactor_render_rejects_mismatched_generation(monkeypatch) -> None:
    """generation 不匹配时 _render_status_once 返回 False（新 worker 已接管）。"""
    status = _FakeStatusLine()
    compactor = _AiogramPollingRetryCompactor(status)  # type: ignore[arg-type]
    now = 100.0
    monkeypatch.setattr("main.time.monotonic", lambda: now)
    compactor._start_worker = lambda gen: None

    compactor.handle("Failed to fetch updates - TelegramNetworkError: timeout")
    assert compactor._render_status_once(999) is False  # 错误的 generation


def test_compactor_stop_sets_idle_and_clears() -> None:
    """stop() 设置 IDLE 并清除状态行。"""
    status = _FakeStatusLine()
    compactor = _AiogramPollingRetryCompactor(status)  # type: ignore[arg-type]
    compactor._state = "RECONNECTING"

    compactor.stop()

    assert compactor._state == "IDLE"
    assert status.clears == 1


# ── _parse_aiogram_retry_sleep ─────────────────────────────────────────


def test_parse_aiogram_retry_sleep_message() -> None:
    assert _parse_aiogram_retry_sleep(
        "Sleep for 0.638185 seconds and try again... (tryings = 2, bot id = 8944500007)"
    ) == (0.638185, 2, "8944500007")


def test_parse_aiogram_retry_sleep_ignores_other_messages() -> None:
    assert _parse_aiogram_retry_sleep("Bot started") is None


async def test_wait_for_bot_identity_retries_and_rebuilds_session(monkeypatch) -> None:
    class FakeSession:
        timeout = 8

        def __init__(self) -> None:
            self.closed = 0

        async def close(self) -> None:
            self.closed += 1

    class FakeBot:
        id = 456

        def __init__(self) -> None:
            self.session = FakeSession()
            self.calls = 0
            self._me = None

        async def get_me(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("Request timeout error")
            return SimpleNamespace(username="telegodex_bot", full_name="Telegodex")

    async def tiny_sleep(self):
        return None

    monkeypatch.setattr("main.Backoff.asleep", tiny_sleep)
    bot = FakeBot()
    user = await asyncio.wait_for(
        _wait_for_bot_identity(
            bot,
            backoff_config=BackoffConfig(
                min_delay=1.0,
                max_delay=5.0,
                factor=1.3,
                jitter=0.0,
            ),
        ),
        timeout=0.5,
    )

    assert user.username == "telegodex_bot"
    assert bot._me is user
    assert bot.calls == 2
    assert bot.session.closed == 1

async def test_await_polling_response_timeout_does_not_wait_for_stuck_cancel(monkeypatch) -> None:
    class FakeBot:
        async def __call__(self, *args, **kwargs):
            try:
                await asyncio.sleep(999)
            except asyncio.CancelledError:
                await asyncio.sleep(999)

    class FakeGetUpdates:
        pass

    monkeypatch.setattr("main._POLLING_HARD_TIMEOUT_SECONDS", 0.01)
    started = asyncio.get_running_loop().time()
    try:
        await _await_polling_response(FakeBot(), FakeGetUpdates(), request_timeout=18)
    except TimeoutError:
        elapsed = asyncio.get_running_loop().time() - started
    else:
        raise AssertionError("expected polling timeout")

    assert elapsed < 0.2

# ── _TelegodexDispatcher polling hard timeout ──────────────────────────


async def test_telegodex_dispatcher_hard_timeout_rebuilds_session(monkeypatch) -> None:
    class FakeSession:
        timeout = 8

        def __init__(self) -> None:
            self.closed = 0

        async def close(self) -> None:
            self.closed += 1

    class FakeUpdate:
        update_id = 1

    class FakeBot:
        id = 123

        def __init__(self) -> None:
            self.session = FakeSession()
            self.calls = 0
            self.probes = 0

        async def __call__(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 1:
                await asyncio.sleep(999)
            return [FakeUpdate()]

        async def get_me(self, *args, **kwargs):
            self.probes += 1
            return object()

    async def tiny_sleep(self):
        return None

    monkeypatch.setattr("main._POLLING_HARD_TIMEOUT_SECONDS", 0.01)
    monkeypatch.setattr("main.Backoff.asleep", tiny_sleep)
    bot = FakeBot()
    updates = _TelegodexDispatcher._listen_updates(bot, polling_timeout=10)
    update = await asyncio.wait_for(updates.__anext__(), timeout=0.5)
    await updates.aclose()

    assert update.update_id == 1
    assert bot.calls == 2
    assert bot.probes == 1
    assert bot.session.closed == 1

async def test_telegodex_dispatcher_network_error_rebuilds_session(monkeypatch) -> None:
    class FakeSession:
        timeout = 8

        def __init__(self) -> None:
            self.closed = 0

        async def close(self) -> None:
            self.closed += 1

    class FakeUpdate:
        update_id = 2

    class FakeBot:
        id = 123

        def __init__(self) -> None:
            self.session = FakeSession()
            self.calls = 0
            self.probes = 0

        async def __call__(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("Request timeout error")
            return [FakeUpdate()]

        async def get_me(self, *args, **kwargs):
            self.probes += 1
            return object()

    async def tiny_sleep(self):
        return None

    monkeypatch.setattr("main.Backoff.asleep", tiny_sleep)
    bot = FakeBot()
    updates = _TelegodexDispatcher._listen_updates(bot, polling_timeout=10)
    update = await asyncio.wait_for(updates.__anext__(), timeout=0.5)
    await updates.aclose()

    assert update.update_id == 2
    assert bot.calls == 2
    assert bot.probes == 1
    assert bot.session.closed == 1
