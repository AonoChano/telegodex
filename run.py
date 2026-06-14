#!/usr/bin/env python3
"""
Telegodex 启动脚本

使用示例：
    python run.py
    python run.py --check-config
"""

import asyncio
import sys
from pathlib import Path
from loguru import logger

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from config import settings


def check_configuration():
    """检查配置是否正确"""
    logger.info("开始检查配置...")

    errors = []

    # 检查必需的配置
    if not settings.telegram_bot_token:
        errors.append("❌ TELEGRAM_BOT_TOKEN 未配置")
    else:
        logger.info("✓ Telegram Bot Token 已配置")

    # 检查 AI 服务商配置
    ai_providers = []
    if settings.openai_api_key:
        ai_providers.append("OpenAI")
    if settings.anthropic_api_key:
        ai_providers.append("Anthropic")
    if settings.google_api_key:
        ai_providers.append("Google")

    if not ai_providers:
        errors.append("❌ 至少需要配置一个 AI 服务商的 API Key")
    else:
        logger.info(f"✓ 已配置 AI 服务商: {', '.join(ai_providers)}")

    # 检查数据库配置
    logger.info(f"✓ 数据库: {settings.database_url}")

    # 检查管理员配置
    if settings.admin_ids:
        logger.info(f"✓ 管理员 IDs: {settings.admin_ids}")
    else:
        logger.warning("⚠️ 未配置管理员 ID")

    # 输出结果
    if errors:
        logger.error("\n配置检查失败：")
        for error in errors:
            logger.error(error)
        return False
    else:
        logger.success("\n✅ 配置检查通过！")
        return True


def print_banner():
    """打印启动横幅"""
    banner = """
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║   ████████╗███████╗██╗     ███████╗ ██████╗  ██████╗   ║
║   ╚══██╔══╝██╔════╝██║     ██╔════╝██╔════╝ ██╔═══██╗  ║
║      ██║   █████╗  ██║     █████╗  ██║  ███╗██║   ██║  ║
║      ██║   ██╔══╝  ██║     ██╔══╝  ██║   ██║██║   ██║  ║
║      ██║   ███████╗███████╗███████╗╚██████╔╝╚██████╔╝  ║
║      ╚═╝   ╚══════╝╚══════╝╚══════╝ ╚═════╝  ╚═════╝   ║
║                                                          ║
║           多 AI 服务商 Telegram Bot 平台                ║
║                    v1.0.0                                ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """
    print(banner)


async def main():
    """主函数"""
    print_banner()

    # 检查命令行参数
    if "--check-config" in sys.argv:
        check_configuration()
        return

    # 检查配置
    if not check_configuration():
        logger.error("\n请修复配置错误后重新启动")
        sys.exit(1)

    # 导入 main 并启动
    logger.info("\n正在启动 Telegodex...")
    from main import main as bot_main
    await bot_main()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\n👋 Telegodex 已停止")
    except Exception as e:
        logger.exception(f"启动失败: {e}")
        sys.exit(1)
