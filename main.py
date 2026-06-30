import asyncio
import logging
import os
import re
import shutil
import sys
import threading
import time
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.utils.backoff import BackoffConfig
from loguru import logger

from ai import AIRouter
from ai.router import unavailable_default_provider_error
from bot.handlers import (
    callbacks_router,
    codex_router,
    history_router,
    messages_router,
    send_router,
    toolbar_router,
)
from bot.startup import run_telegram_startup_checks
from config import settings
from storage import ContextManager, Database


class _InterceptHandler(logging.Handler):
    """把 Python stdlib 的 logger（aiogram / aiohttp 等）转给 loguru 处理。

    否则这些 logger 会走自己的 Handler，把 traceback 满屏打到 stderr，
    与 loguru 终端简化的目标相冲。
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 找到真正发起 log 的调用栈层（不是 logging 库内部）
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        if _handle_aiogram_polling_retry(record, level, depth):
            return

        # 用 patch 把 {name} 字段覆盖为 stdlib logger 名（如 aiogram.dispatcher）
        # 否则 loguru 默认用调用模块名（会显示 __main__ / main.py 等）
        logger.patch(lambda r: r.update(name=record.name)).opt(
            depth=depth, exception=record.exc_info
        ).log(level, record.getMessage())

def _strip_exception_block(text: str) -> str:
    """loguru 在 format 之后总会把 traceback 块自动追加到行尾。

    对终端来说这破坏"单行"约束；对文件来说这正是我们想要的。所以终端 sink
    通过这个函数把从 "Traceback (most recent call last):" 开始的所有内容砍掉。
    """
    marker = "Traceback (most recent call last):"
    idx = text.find(marker)
    if idx < 0:
        return text
    return text[:idx].rstrip() + "\n"


class _TerminalStatusLine:
    """Single-line terminal status that can be replaced in place."""

    def __init__(self) -> None:
        self._last_line_len = 0
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return sys.stderr.isatty()

    def update(self, text: str) -> None:
        if not self.enabled:
            return
        width = max(shutil.get_terminal_size((120, 20)).columns - 2, 40)
        text = _fit_terminal_status_text(text, width)
        with self._lock:
            sys.stderr.write("\r\033[2K")
            sys.stderr.write(text)
            sys.stderr.flush()
            self._last_line_len = len(text)

    def clear(self) -> None:
        if not self.enabled:
            return
        with self._lock:
            if self._last_line_len <= 0:
                return
            sys.stderr.write("\r\033[2K")
            sys.stderr.flush()
            self._last_line_len = 0


# ── Polling retry status rendering ──────────────────────────────────────

# ANSI: \033[3;38;2;R;G;Bm = italic + true color
# All dim (R,G,B ≈ 120–175) with subtle hue differentiation per block.
# 目标：灰灰的半透明彩色斜体分块 — 块落分明，避免视觉疲劳。
_DIM_GRAY = "\033[3;38;2;150;150;150m"
_DIM_BLUE = "\033[3;38;2;130;155;180m"
_DIM_AMBER = "\033[3;38;2;175;160;130m"
_DIM_GREEN = "\033[3;38;2;130;175;150m"
_DIM_RED = "\033[3;38;2;175;135;135m"
_ANSI_RESET = "\033[0m"

# aiogram exception class → (category, hint)
_POLLING_ERROR_CLASSES: dict[str, tuple[str, str]] = {
    "TelegramNetworkError": ("network", "无法连接 Telegram 服务器"),
    "TelegramUnauthorizedError": ("auth", "Bot token 无效，请检查 TELEGRAM_BOT_TOKEN"),
    "TelegramForbiddenError": ("auth", "Bot 被禁用或无权访问"),
    "TelegramConflictError": ("auth", "Bot token 被其他实例占用"),
    "TelegramServerError": ("server", "Telegram 服务端异常"),
    "RestartingTelegram": ("server", "Telegram 服务器重启中"),
    "TelegramRetryAfter": ("rate_limit", "触发洪水控制，等待重试"),
    "TelegramBadRequest": ("client", "请求格式错误"),
    "TelegramNotFound": ("client", "目标不存在"),
    "TelegramEntityTooLarge": ("client", "文件过大"),
    "ClientDecodeError": ("client", "响应解析失败"),
}

# category → max retries (None = unlimited)
_POLLING_RETRY_LIMITS: dict[str, int | None] = {
    "network": None,
    "auth": 5,
    "server": 10,
    "rate_limit": None,
    "client": 10,
    "unknown": 10,
}

_POLLING_ERROR_PATTERN = re.compile(
    r"^Failed to fetch updates - (?P<type>\w+): (?P<detail>.*)$"
)


def _classify_polling_error(message: str) -> tuple[str, str, str, str]:
    """从 aiogram 的 ``Failed to fetch updates`` 日志中提取错误类型并分类。

    Returns:
        ``(category, error_type, hint, detail)``
    """
    match = _POLLING_ERROR_PATTERN.match(message)
    if match is None:
        return ("unknown", "Unknown", "未知错误", "")

    error_type = match.group("type")
    detail = match.group("detail").strip()

    # 砍掉 aiogram / aiohttp 的冗长前缀
    for prefix in (
        "HTTP Client says - ",
        "ClientConnectorError: ",
        "ClientOSError: ",
        "ClientPayloadError: ",
    ):
        detail = detail.replace(prefix, "", 1)
    detail = " ".join(detail.split())  # normalize whitespace / newlines

    category, hint = _POLLING_ERROR_CLASSES.get(error_type, ("unknown", "未知错误"))
    return (category, error_type, hint, detail)


def _format_retry_limit(category: str) -> str:
    limit = _POLLING_RETRY_LIMITS.get(category, 10)
    return "∞" if limit is None else str(limit)


def _format_reconnect_status(
    category: str,
    error_type: str,
    detail: str,
    attempt: int,
    remaining: float,
    elapsed: float,
) -> str:
    """单行灰度斜体分块：◦ Reconnecting · 1/5 · retry 3.2s · 12.4s · Error: detail"""
    limit_str = _format_retry_limit(category)
    retry_part = f"retry {remaining:.1f}s" if remaining > 0 else "waiting"
    error_part = f"{error_type}: {detail}" if detail else error_type

    return (
        f"{_DIM_BLUE}◦ Reconnecting{_DIM_GRAY} · "
        f"{_DIM_AMBER}{attempt}/{limit_str}{_DIM_GRAY} · "
        f"{_DIM_GREEN}{retry_part}{_DIM_GRAY} · "
        f"{_DIM_GRAY}{elapsed:.1f}s{_DIM_GRAY} · "
        f"{_DIM_RED}{error_part}"
        f"{_ANSI_RESET}"
    )


class _AiogramPollingRetryCompactor:
    """把 aiogram 轮询重试渲染为一条原地更新的终端状态行。

    状态机：
        IDLE ──(Failed to fetch updates)──► RECONNECTING
        RECONNECTING ──(Connection established)──► IDLE + success log
        RECONNECTING ──(attempt > limit)──► IDLE + failure log (+ sys.exit for auth)
        RECONNECTING ──(retry_deadline expired)──► 保持 RECONNECTING（等待响应）
    """

    _REFRESH_SECONDS = 0.2
    _PENDING_RETRY_SECONDS = 2.0  # 仅看到错误、尚未收到 sleep 时的占位倒计时

    def __init__(self, status_line: _TerminalStatusLine) -> None:
        self._status_line = status_line
        self._lock = threading.Lock()
        # 状态
        self._state = "IDLE"  # "IDLE" | "RECONNECTING"
        self._category = "unknown"
        self._error_type = "Unknown"
        self._detail = ""
        self._hint = ""
        self._attempt = 0
        self._retry_deadline = 0.0  # monotonic
        self._error_time = 0.0  # monotonic，本次重连周期首次错误时间
        # worker 生命周期：generation 避免"老 worker 正在退出 / 新 error 跳过启动"的竞态
        self._worker_generation = 0
        self._worker: threading.Thread | None = None

    @property
    def enabled(self) -> bool:
        return self._status_line.enabled

    def handle(self, message: str) -> bool:
        if not self.enabled:
            return False

        if "Failed to fetch updates" in message:
            return self._handle_error(message)

        if "Connection established" in message:
            self._handle_reconnected()
            return True

        sleep = _parse_aiogram_retry_sleep(message)
        if sleep is not None:
            self._handle_sleep(sleep)
            return True

        return False

    # ── 状态转换 ──────────────────────────────────────────────

    def _handle_error(self, message: str) -> bool:
        category, error_type, hint, detail = _classify_polling_error(message)
        now = time.monotonic()

        with self._lock:
            is_new_cycle = self._state == "IDLE"
            if is_new_cycle:
                self._worker_generation += 1
                self._attempt = 1
                self._error_time = now
            else:
                self._attempt += 1

            self._category = category
            self._error_type = error_type
            self._hint = hint
            self._detail = detail
            self._retry_deadline = now + self._PENDING_RETRY_SECONDS
            self._state = "RECONNECTING"

            limit = _POLLING_RETRY_LIMITS.get(category, 10)
            should_fail = limit is not None and self._attempt > limit
            current_gen = self._worker_generation
            need_worker = is_new_cycle  # 新周期总是启动新 worker

        if should_fail:
            self._handle_failed()
            return True

        if need_worker:
            self._start_worker(current_gen)
        return True

    def _handle_sleep(self, sleep: tuple[float, int, str]) -> None:
        seconds, tryings, _bot_id = sleep
        now = time.monotonic()
        with self._lock:
            if self._state != "RECONNECTING":
                return
            # aiogram 的 tryings 是"本次 sleep 前"的计数器（0-indexed）
            self._attempt = max(self._attempt, tryings + 1)
            self._retry_deadline = now + seconds

    def _handle_reconnected(self) -> None:
        with self._lock:
            if self._state != "RECONNECTING":
                return
            attempt = self._attempt
            category = self._category
            error_type = self._error_type
            elapsed = time.monotonic() - self._error_time
            self._state = "IDLE"

        self._status_line.clear()
        # logger.success 走 _terminal_sink → stop()（幂等），不会死锁
        logger.success(
            f"Telegram 重连成功 · {attempt}/{_format_retry_limit(category)} · "
            f"耗时 {elapsed:.1f}s · 最后错误: {error_type}"
        )

    def _handle_failed(self) -> None:
        with self._lock:
            attempt = self._attempt
            category = self._category
            error_type = self._error_type
            hint = self._hint
            self._state = "IDLE"

        self._status_line.clear()
        logger.error(
            f"Telegram 重连失败 · {attempt}/{_format_retry_limit(category)} · "
            f"{error_type} · {hint}"
        )
        # 认证类错误不可恢复 — 退出进程
        # SystemExit 是 BaseException，不会被 aiogram 的 except Exception 捕获
        if category == "auth":
            sys.exit(1)

    # ── worker ───────────────────────────────────────────────

    def _start_worker(self, generation: int) -> None:
        """启动状态渲染 worker。仅在 _handle_error 的新周期调用。"""
        with self._lock:
            if self._state != "RECONNECTING":
                return  # 状态已变（例如 stop），无需启动
            # 同 generation 的 worker 仍在运行则不重复启动
            if (
                self._worker is not None
                and self._worker.is_alive()
                and self._worker_generation == generation
            ):
                return
            self._worker = threading.Thread(
                target=self._run_status_loop,
                args=(generation,),
                name="telegram-polling-status",
                daemon=True,
            )
            worker = self._worker
        worker.start()  # 在锁外启动，避免锁内 I/O

    def stop(self) -> None:
        with self._lock:
            self._state = "IDLE"
        self._status_line.clear()

    def _run_status_loop(self, generation: int) -> None:
        while True:
            if not self._render_status_once(generation):
                return
            time.sleep(self._REFRESH_SECONDS)

    def _render_status_once(self, generation: int) -> bool:
        with self._lock:
            if self._state != "RECONNECTING":
                return False
            if self._worker_generation != generation:
                return False  # 更新的 worker 已接管
            now = time.monotonic()
            remaining = max(self._retry_deadline - now, 0.0)
            elapsed = now - self._error_time
            self._status_line.update(
                _format_reconnect_status(
                    self._category,
                    self._error_type,
                    self._detail,
                    self._attempt,
                    remaining,
                    elapsed,
                )
            )
            return True



_ANSI_ESCAPE_RE = re.compile(r"\033\[[0-9;]*m")


def _visible_len(text: str) -> int:
    """ANSI 转义序列不占可见宽度，测量时需剔除。"""
    return len(_ANSI_ESCAPE_RE.sub("", text))


def _fit_terminal_status_text(text: str, width: int) -> str:
    """按可见宽度截断；若原文含 ANSI 颜色码，截断处补 reset 防泄漏。"""
    if _visible_len(text) <= width:
        return text
    budget = max(width - 3, 0)
    result: list[str] = []
    visible = 0
    pos = 0
    has_ansi = False
    while pos < len(text):
        match = _ANSI_ESCAPE_RE.match(text, pos)
        if match:
            # ANSI 转义码原样保留，不计入可见预算
            result.append(match.group())
            pos = match.end()
            has_ansi = True
            continue
        if visible >= budget:
            break
        result.append(text[pos])
        visible += 1
        pos += 1
    result.append(f"{_ANSI_RESET}..." if has_ansi else "...")
    return "".join(result)


def _parse_aiogram_retry_sleep(message: str) -> tuple[float, int, str] | None:
    match = re.search(
        r"Sleep for (?P<seconds>[0-9.]+) seconds and try again\.\.\. "
        r"\(tryings = (?P<tryings>\d+), bot id = (?P<bot_id>\d+)\)",
        message,
    )
    if match is None:
        return None
    return (
        float(match.group("seconds")),
        int(match.group("tryings")),
        match.group("bot_id"),
    )


_terminal_status_line = _TerminalStatusLine()
_polling_retry_compactor = _AiogramPollingRetryCompactor(_terminal_status_line)


def _handle_aiogram_polling_retry(record: logging.LogRecord, level, depth: int) -> bool:
    if record.name != "aiogram.dispatcher":
        return False

    message = record.getMessage()
    if not _polling_retry_compactor.handle(message):
        return False

    # "Connection established" 由 compactor 发出格式化 success 日志，原始消息完全抑制
    if "Connection established" in message:
        return True

    # 错误 / sleep 消息：抑制终端（状态行处理），保留文件用于调试
    logger.bind(_terminal_suppress=True).patch(lambda r: r.update(name=record.name)).opt(
        depth=depth, exception=record.exc_info
    ).log(level, message)
    return True


def _terminal_sink(message) -> None:
    """终端 sink：单行 + 砍掉 traceback 块。"""
    if message.record["extra"].get("_terminal_suppress"):
        return
    _polling_retry_compactor.stop()
    sys.stderr.write(_strip_exception_block(str(message)))

def _setup_logging() -> None:
    """双 sink：终端精简 / 文件详尽。

    关键：loguru 的默认行为是 format 渲染完之后**自动追加** exception 块。
    这是 source of truth。**不要**在 format 里写 ``{exception}`` token，否则
    会得到两份重复 traceback。正确分流：

    - 终端：用 callable sink + ``_strip_exception_block`` 砍掉追加的 traceback
    - 文件：直接用默认行为，traceback 由 loguru 自动追加
    """
    # 关掉 loguru 的默认 stderr sink
    logger.remove()

    terminal_format = (
        "<green>{time:HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
        "{name}:{function}:{line} - {message}"
    )

    # 终端：单行、彩色、sink 砍掉自动追加的 traceback 块
    logger.add(
        _terminal_sink,
        level="INFO",
        format=terminal_format,
        backtrace=False,
        diagnose=False,
        colorize=True,
    )

    # 文件：默认行为 — message 后由 loguru 自动追加完整 traceback
    # 1 份/错误，不重复。rotation/retain/enqueue/diagnose 保留
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_dir / "bot_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        format=file_format,
        rotation="00:00",
        retention="7 days",
        backtrace=False,
        diagnose=True,
        enqueue=True,
    )

    # 接管 stdlib logger（aiogram / aiohttp / asyncio 等）
    root = logging.getLogger()
    root.handlers = [_InterceptHandler()]
    root.setLevel(logging.INFO)
    for noisy in ("aiogram.event", "aiogram.dispatcher",
                  "aiogram.middlewares", "aiohttp.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

if os.name == "nt":
    import msvcrt
else:
    import fcntl

def _bot_id_from_token(bot_token: str) -> str:
    return bot_token.split(":", 1)[0] if bot_token else "unknown"

def _acquire_polling_lock(bot_token: str):
    """Prevent duplicate local polling processes for the same bot token."""
    lock_dir = Path("logs")
    lock_dir.mkdir(exist_ok=True)
    lock_path = lock_dir / f"telegodex_{_bot_id_from_token(bot_token)}.lock"
    lock_file = lock_path.open("a+b")
    lock_file.seek(0)

    try:
        if os.name == "nt":
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock_file.close()
        logger.error(
            "Another Telegodex polling process is already running for this bot "
            f"(lock: {lock_path}). Stop the other process before starting a new one."
        )
        return None

    lock_file.seek(0)
    lock_file.truncate()
    lock_file.write(f"pid={os.getpid()}\n".encode())
    lock_file.flush()
    return lock_file

def _release_polling_lock(lock_file) -> None:
    if lock_file is None:
        return

    try:
        lock_file.seek(0)
        if os.name == "nt":
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    finally:
        lock_file.close()


async def main():
    """主入口"""
    # 初始化日志（双 sink：终端简 / 文件详）
    _setup_logging()
    logger.info("Telegodex 启动中...")

    # 初始化数据库
    db = Database(settings.database_url)
    await db.init_db()

    # Wire DB session factory into codex handler for approval DB fallback.
    from bot.handlers.codex import set_db_session_factory
    set_db_session_factory(db.get_session)

    # 初始化 AI Router（从 provider.toml 加载所有 provider 配置）
    from config.provider_loader import load_provider_toml

    try:
        provider_configs, global_config = load_provider_toml("provider.toml")
    except FileNotFoundError as e:
        logger.error(f"❌ {e}")
        return
    except Exception as e:
        logger.error(f"❌ 加载 provider.toml 失败: {e}")
        return

    ai_router = AIRouter(provider_configs, global_config)

    if not ai_router.list_available_providers():
        logger.error("❌ 没有任何 AI 服务商可用 — 请检查 provider.toml 的 available_providers 列表与对应 .env 中的 API key")
        return

    if error := unavailable_default_provider_error(ai_router):
        logger.error(f"❌ {error}")
        return

    logger.info(f"可用的 AI 服务商: {', '.join(ai_router.list_available_providers())}")

    # 初始化 Orchestrator
    from core.orchestrator import Orchestrator
    orchestrator = Orchestrator(ai_router)
    from bot.handlers import toolbar as toolbar_module
    if orchestrator.session_manager is not None:
        toolbar_module.set_session_manager(orchestrator.session_manager)

    bot_token = settings.telegram_bot_token
    if hasattr(bot_token, 'get_secret_value'):
        bot_token = bot_token.get_secret_value()

    polling_lock = _acquire_polling_lock(bot_token)
    if polling_lock is None:
        await db.close()
        return

    # 初始化 Bot 和 Dispatcher
    #
    # Bot session 超时：aiogram 默认 AiohttpSession.timeout=60s。这个值会和
    # _listen_updates 里的 polling_timeout 相加变成 aiohttp 的 request_timeout：
    #
    #   request_timeout = bot.session.timeout + polling_timeout
    #                   = 60 + 10  (默认) = 70s
    #
    # 网络断后一次 getUpdates 会卡满 70s 才抛异常，期间 _listen_updates 看起
    # 来在"卡死"。日志打 "Sleep for 1.0 seconds"（这是 backoff delay，跟
    # getUpdates 卡多久无关），但用户感知是 sleep 几分钟后才"看到"重试。
    #
    # 改成 20s：request_timeout = 20 + 10 = 30s，单次失败 30s + backoff 0.5-3s
    # ≈ 30-35s/轮。日常长轮询时 20s 不会触发（polling_timeout=10s，server
    # 端无新消息时会先在 10s 短轮询一次返回），仅在网络故障下兜底。
    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=AiohttpSession(timeout=20),
    )
    await run_telegram_startup_checks(bot, settings.admin_ids)
    dp = Dispatcher()

    # 注册路由
    dp.include_router(toolbar_router)
    dp.include_router(codex_router)
    dp.include_router(history_router)
    dp.include_router(send_router)
    dp.include_router(messages_router)
    dp.include_router(callbacks_router)

    # 依赖注入中间件
    @dp.message.middleware()
    @dp.callback_query.middleware()
    async def inject_dependencies(handler, event, data):
        """注入依赖"""
        async for session in db.get_session():
            data["context_manager"] = ContextManager(
                session,
                max_context_messages=settings.max_context_messages
            )
            data["ai_router"] = ai_router
            data["orchestrator"] = orchestrator
            return await handler(event, data)

    # 启动轮询
    #
    # 黄金分割退避：min=1s, max=30s, factor=1.618
    # 序列：1.0, 1.6, 2.6, 4.2, 6.9, 11.1, 17.9, 29.0, 30.0, 30.0...
    # 网络错误无限重试，最长间隔 30s；认证错误 5 次后退出（≈6.9s 累计）。
    polling_backoff = BackoffConfig(
        min_delay=1.0,
        max_delay=30.0,
        factor=1.618,
        jitter=0.1,
    )
    # 启动 Codex app-server daemon
    if settings.codex_daemon_auto_start:
        from extensions.codex.daemon import get_codex_daemon

        try:
            codex_daemon = get_codex_daemon()
            await codex_daemon.start()
        except Exception as e:
            logger.warning(f"Codex daemon 启动失败: {type(e).__name__}: {e!r}")

    logger.info("✓ Telegodex 启动成功！")
    try:
        await dp.start_polling(bot, backoff_config=polling_backoff)
    finally:
        # 关闭顺序：Codex daemon 先停掉（app-server 子进程），
        # 然后 HTTP 共享 session，再 aiogram session，最后 db。
        from extensions.codex.daemon import get_codex_daemon

        try:
            codex = get_codex_daemon()
            if codex.is_alive():
                await codex.stop()
        except Exception as e:
            logger.warning(
                f"Codex daemon 关闭失败: {type(e).__name__}: {e!r}"
            )

        from bot.utils.rich_messages import close_shared_session

        try:
            await close_shared_session()
        except Exception as e:
            logger.warning(
                f"close_shared_session 失败: {type(e).__name__}: {e!r}"
            )
        await db.close()
        await bot.session.close()
        _release_polling_lock(polling_lock)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot 已停止")
