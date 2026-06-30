import asyncio
import logging
import os
import re
import shutil
import sys
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

    @property
    def enabled(self) -> bool:
        return sys.stderr.isatty()

    def update(self, text: str) -> None:
        if not self.enabled:
            return
        width = max(shutil.get_terminal_size((120, 20)).columns - 1, 40)
        if len(text) > width:
            text = text[: max(width - 1, 0)] + "…"
        padding = " " * max(self._last_line_len - len(text), 0)
        sys.stderr.write(f"\r{text}{padding}")
        sys.stderr.flush()
        self._last_line_len = len(text)

    def clear(self) -> None:
        if not self.enabled or self._last_line_len <= 0:
            return
        sys.stderr.write("\r" + " " * self._last_line_len + "\r")
        sys.stderr.flush()
        self._last_line_len = 0


class _AiogramPollingRetryCompactor:
    """Render repeated aiogram polling network retries as one terminal line."""

    def __init__(self, status_line: _TerminalStatusLine) -> None:
        self._status_line = status_line
        self._last_error = ""

    @property
    def enabled(self) -> bool:
        return self._status_line.enabled

    def handle(self, message: str) -> bool:
        if not self.enabled:
            return False

        if "Failed to fetch updates" in message:
            self._last_error = _compact_aiogram_polling_error(message)
            self._status_line.update(f"Telegram polling retry: {self._last_error}")
            return True

        sleep = _parse_aiogram_retry_sleep(message)
        if sleep is not None:
            seconds, tryings, bot_id = sleep
            error = self._last_error or "waiting for Telegram API"
            self._status_line.update(
                f"Telegram polling retry: {error} | try={tryings}, next={seconds:.2f}s, bot={bot_id}"
            )
            return True

        return False


def _compact_aiogram_polling_error(message: str) -> str:
    text = message.replace("Failed to fetch updates - ", "", 1)
    text = text.replace("TelegramNetworkError: HTTP Client says - ", "", 1)
    text = text.replace("ClientConnectorError: ", "", 1)
    return " ".join(text.split())


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

    logger.bind(_terminal_suppress=True).patch(lambda r: r.update(name=record.name)).opt(
        depth=depth, exception=record.exc_info
    ).log(level, message)
    return True


def _terminal_sink(message) -> None:
    """终端 sink：单行 + 砍掉 traceback 块。"""
    if message.record["extra"].get("_terminal_suppress"):
        return
    _terminal_status_line.clear()
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
    # 显式传 backoff_config 收紧重试节奏。aiogram 默认是 min=0.5, max=5.0,
    # factor=1.5, jitter=0.1，连续失败 5 次后 delay 累积到 4.6s。
    # 这里用更紧凑的 max=3.0 + factor=1.3：失败 5 次后 delay ≈ 1.4s，
    # 配合 30s 单次 getUpdates 上限，5 轮失败 = 5*30 + 7 ≈ 2.5 分钟。
    # 避免"打了 sleep 1s 结果卡 5 分钟"的感知错位。
    polling_backoff = BackoffConfig(
        min_delay=0.5,
        max_delay=3.0,
        factor=1.3,
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
