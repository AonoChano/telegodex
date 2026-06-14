import asyncio
import os
from pathlib import Path
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from loguru import logger

from config import settings
from storage import Database, ContextManager
from ai import AIRouter
from bot import messages_router, callbacks_router

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
    lock_file.write(f"pid={os.getpid()}\n".encode("utf-8"))
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
    # 初始化日志
    logger.add("logs/bot_{time}.log", rotation="1 day", retention="7 days", level="INFO")
    logger.info("Telegodex 启动中...")

    # 初始化数据库
    db = Database(settings.database_url)
    await db.init_db()

    # 初始化 AI Router（包含内置和自定义 Provider）
    ai_router = AIRouter(settings.get_ai_providers_config())

    if not ai_router.list_available_providers():
        logger.error("❌ 没有配置任何 AI 服务商，请检查 .env 文件")
        return

    logger.info(f"可用的 AI 服务商: {', '.join(ai_router.list_available_providers())}")

    bot_token = settings.telegram_bot_token
    if hasattr(bot_token, 'get_secret_value'):
        bot_token = bot_token.get_secret_value()

    polling_lock = _acquire_polling_lock(bot_token)
    if polling_lock is None:
        await db.close()
        return

    # 初始化 Bot 和 Dispatcher
    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # 注册路由
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
            return await handler(event, data)

    # 启动轮询
    logger.info("✓ Telegodex 启动成功！")
    try:
        await dp.start_polling(bot)
    finally:
        await db.close()
        await bot.session.close()
        _release_polling_lock(polling_lock)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot 已停止")
