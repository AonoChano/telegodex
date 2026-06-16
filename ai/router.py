from typing import Any

from loguru import logger

from .anthropic_provider import AnthropicProvider
from .base import BaseAIProvider
from .china_providers import BaiduProvider, MoonshotProvider, QwenProvider, ZhipuProvider
from .deepseek_provider import DeepSeekProvider
from .google_provider import GoogleProvider
from .openai_compatible_provider import OpenAICompatibleProvider
from .openai_provider import OpenAIProvider


class AIRouter:
    """AI 服务商路由器 - 统一管理多个 AI Provider，支持自定义配置"""

    # 内置 Provider 类
    BUILTIN_PROVIDERS: dict[str, type[BaseAIProvider]] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "google": GoogleProvider,
        "deepseek": DeepSeekProvider,
        "qwen": QwenProvider,
        "moonshot": MoonshotProvider,
        "zhipu": ZhipuProvider,
        "baidu": BaiduProvider,
    }

    def __init__(self, config: dict[str, Any]):
        """
        初始化路由器

        Args:
            config: 配置字典，格式：
                {
                    "openai": "sk-xxx",  # 简单字符串 = API Key
                    "deepseek": {"api_key": "sk-xxx"},  # 字典格式
                    "custom_provider": {  # 自定义 Provider
                        "type": "openai_compatible",
                        "api_key": "sk-xxx",
                        "base_url": "https://api.example.com/v1",
                        "models": ["model-1", "model-2"],
                        "default_model": "model-1"
                    }
                }
        """
        self.providers: dict[str, BaseAIProvider] = {}
        self._initialize_providers(config)

    def _initialize_providers(self, config: dict[str, Any]):
        """初始化所有配置的 Provider"""
        for provider_name, provider_config in config.items():
            if not provider_config:
                logger.warning(f"跳过 {provider_name}，未配置")
                continue

            try:
                # 简单字符串 = API Key
                if isinstance(provider_config, str):
                    provider_config = {"api_key": provider_config}

                # 检查是否是内置 Provider
                if provider_name in self.BUILTIN_PROVIDERS:
                    provider_class = self.BUILTIN_PROVIDERS[provider_name]
                    self.providers[provider_name] = provider_class(**provider_config)
                    logger.info(f"✓ 初始化内置 Provider: {provider_name}")

                # 自定义 Provider
                elif isinstance(provider_config, dict) and "type" in provider_config:
                    self._initialize_custom_provider(provider_name, provider_config)

                else:
                    logger.warning(f"未知的 Provider 配置: {provider_name}")

            except Exception as e:
                logger.error(f"✗ 初始化 {provider_name} 失败: {e}")

    def _initialize_custom_provider(self, name: str, config: dict[str, Any]):
        """初始化自定义 Provider"""
        provider_type = config.pop("type")

        if provider_type == "openai_compatible":
            # OpenAI 兼容 API
            api_key = config.pop("api_key")
            base_url = config.pop("base_url")
            models = config.pop("models", [])
            default_model = config.pop("default_model", models[0] if models else "gpt-3.5-turbo")

            self.providers[name] = OpenAICompatibleProvider(
                api_key=api_key,
                base_url=base_url,
                provider_name=name,
                default_model=default_model,
                available_models=models,
                **config
            )
            logger.info(f"✓ 初始化自定义 Provider: {name} (OpenAI 兼容)")

        else:
            logger.error(f"不支持的自定义 Provider 类型: {provider_type}")

    def get_provider(self, name: str) -> BaseAIProvider | None:
        """获取指定的 Provider"""
        return self.providers.get(name)

    def get_default_provider(self) -> BaseAIProvider | None:
        """获取默认 Provider（第一个可用的）"""
        if not self.providers:
            return None
        return list(self.providers.values())[0]

    def list_available_providers(self) -> list[str]:
        """列出所有可用的 Provider"""
        return list(self.providers.keys())

    def is_provider_available(self, name: str) -> bool:
        """检查 Provider 是否可用"""
        return name in self.providers

    def get_all_models(self) -> dict[str, list[str]]:
        """获取所有 Provider 的可用模型"""
        return {
            name: provider.get_available_models()
            for name, provider in self.providers.items()
        }

    def get_provider_display_name(self, name: str) -> str:
        """获取 Provider 的显示名称"""
        provider = self.get_provider(name)
        if provider:
            return provider.provider_name
        return name
