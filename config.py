from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Dict, Any
import json
import os


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # Telegram Bot
    telegram_bot_token: str

    # 内置 AI Provider API Keys
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None
    deepseek_api_key: str | None = None
    qwen_api_key: str | None = None
    moonshot_api_key: str | None = None
    zhipu_api_key: str | None = None
    baidu_api_key: str | None = None
    baidu_secret_key: str | None = None

    # 自定义 Provider 配置文件路径
    custom_providers_config: str = "custom_providers.json"

    # Database
    database_url: str = "sqlite+aiosqlite:///telegodex.db"

    # Redis
    redis_url: str | None = None

    # Security
    admin_user_ids: str = ""  # 逗号分隔的 User IDs
    max_requests_per_minute: int = 20
    max_context_messages: int = 50  # 每个会话保留的最大消息数

    # AI Settings
    default_ai_provider: str = "openai"
    default_model: str = "gpt-4"
    max_tokens: int = 4096
    temperature: float = 0.7

    @property
    def admin_ids(self) -> List[int]:
        """解析管理员 ID 列表"""
        if not self.admin_user_ids:
            return []
        return [int(uid.strip()) for uid in self.admin_user_ids.split(",") if uid.strip()]

    def get_ai_providers_config(self) -> Dict[str, Any]:
        """
        获取所有 AI Provider 配置
        包含内置和自定义 Provider
        """
        config = {}

        # 内置 Provider
        if self.openai_api_key:
            config["openai"] = self.openai_api_key
        if self.anthropic_api_key:
            config["anthropic"] = self.anthropic_api_key
        if self.google_api_key:
            config["google"] = self.google_api_key
        if self.deepseek_api_key:
            config["deepseek"] = self.deepseek_api_key
        if self.qwen_api_key:
            config["qwen"] = self.qwen_api_key
        if self.moonshot_api_key:
            config["moonshot"] = self.moonshot_api_key
        if self.zhipu_api_key:
            config["zhipu"] = self.zhipu_api_key
        if self.baidu_api_key:
            config["baidu"] = {
                "api_key": self.baidu_api_key,
                "secret_key": self.baidu_secret_key
            }

        # 加载自定义 Provider
        if os.path.exists(self.custom_providers_config):
            try:
                with open(self.custom_providers_config, "r", encoding="utf-8") as f:
                    custom_config = json.load(f)
                    config.update(custom_config)
            except json.JSONDecodeError as e:
                from loguru import logger
                logger.error(f"自定义 Provider 配置文件 JSON 格式错误: {e}")
            except Exception as e:
                from loguru import logger
                logger.error(f"加载自定义 Provider 配置失败: {e}")

        return config


settings = Settings()
