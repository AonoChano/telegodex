from typing import List, AsyncIterator
from loguru import logger

from .base import BaseAIProvider, Message, AIResponse, MessageRole
from .openai_compatible_provider import OpenAICompatibleProvider


class QwenProvider(OpenAICompatibleProvider):
    """阿里通义千问 (Qwen) Provider"""

    def __init__(self, api_key: str, **kwargs):
        super().__init__(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            provider_name="阿里通义千问 (Qwen)",
            default_model="qwen-max",
            available_models=[
                "qwen-max",           # 通义千问最强模型
                "qwen-plus",          # 平衡性能
                "qwen-turbo",         # 快速响应
                "qwen-long",          # 长文本处理
                "qwen-vl-plus",       # 视觉理解
                "qwen-vl-max",        # 视觉理解旗舰
            ],
            **kwargs
        )


class MoonshotProvider(OpenAICompatibleProvider):
    """Moonshot Kimi Provider（2026 年 6 月最新）"""

    def __init__(self, api_key: str, **kwargs):
        super().__init__(
            api_key=api_key,
            base_url="https://api.moonshot.cn/v1",
            provider_name="Moonshot Kimi",
            default_model="kimi-k2-7-code",
            available_models=[
                "kimi-k2-7-code",     # 2026-06 最新，代码优化版，1T 参数
                "kimi-k2-6",          # 2026-04，多模态，256K 上下文
                "kimi-k2-5",          # 2026-03，256K 上下文
            ],
            **kwargs
        )


class ZhipuProvider(OpenAICompatibleProvider):
    """智谱AI GLM Provider（2026 最新）"""

    def __init__(self, api_key: str, **kwargs):
        super().__init__(
            api_key=api_key,
            base_url="https://open.bigmodel.cn/api/paas/v4",
            provider_name="智谱AI (GLM)",
            default_model="glm-4-6",
            available_models=[
                "glm-4-6",            # 2026 最新旗舰，355B 参数，200K 上下文
                "glm-4-plus",         # GLM-4 增强版
                "glm-4-air",          # 轻量高速版
                "glm-4-flash",        # 免费版
                "glm-4v",             # 多模态视觉
            ],
            **kwargs
        )


class BaiduProvider(OpenAICompatibleProvider):
    """百度文心一言 (ERNIE) Provider（需要特殊鉴权）"""

    def __init__(self, api_key: str, secret_key: str | None = None, **kwargs):
        """
        百度文心需要 API Key 和 Secret Key

        注意：百度的认证机制与 OpenAI 不同，需要先获取 access_token
        这里简化实现，生产环境需要实现完整的 OAuth 2.0 流程
        """
        # 百度 API 需要特殊处理，这里先提供基础框架
        base_url = kwargs.pop("base_url", "https://aip.baidubce.com/rpc/2.0/ai_custom/v1")

        super().__init__(
            api_key=api_key,
            base_url=base_url,
            provider_name="百度文心一言 (ERNIE)",
            default_model="ernie-5.0-thinking-latest",
            available_models=[
                "ernie-5.0-thinking-latest",  # ERNIE 5.0 最新
                "ernie-4.5-turbo-latest",     # ERNIE 4.5 Turbo
                "ernie-4.0-turbo-latest",     # ERNIE 4.0 Turbo
                "ernie-x-1.1",                # 多模态深度推理
            ],
            **kwargs
        )
        self.secret_key = secret_key

    async def chat(self, messages: List[Message], **kwargs) -> AIResponse:
        """
        百度 API 需要特殊处理
        TODO: 实现百度的 OAuth 2.0 鉴权流程
        """
        logger.warning("百度文心 API 需要特殊鉴权流程，当前为简化实现")
        # 这里可以调用父类方法或实现百度特定的 API 调用
        return await super().chat(messages, **kwargs)
