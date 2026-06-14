import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from loguru import logger

from config import settings
from storage import Database, ContextManager
from ai import AIRouter
from bot import messages_router, callbacks_router


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

    # 初始化 Bot 和 Dispatcher
    bot = Bot(
        token=settings.telegram_bot_token,
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


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot 已停止")
