from typing import List, AsyncIterator
from openai import AsyncOpenAI
from loguru import logger

from .base import BaseAIProvider, Message, AIResponse, MessageRole


class DeepSeekProvider(BaseAIProvider):
    """
    DeepSeek 服务商实现

    支持两种 API 格式：
    1. OpenAI 兼容接口（默认）: https://api.deepseek.com
    2. Anthropic 兼容接口: https://api.deepseek.com （通过 base_url 参数指定）

    参考: https://api-docs.deepseek.com/zh-cn/guides/anthropic_api
    """

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com", **kwargs):
        super().__init__(api_key, **kwargs)
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self._default_model = "deepseek-v4-pro"

    async def chat(
        self,
        messages: List[Message],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        **kwargs
    ) -> AIResponse:
        """发送聊天请求"""
        try:
            model = model or self._default_model

            # 转换消息格式
            openai_messages = [
                {"role": msg.role.value, "content": msg.content}
                for msg in messages
            ]

            response = await self.client.chat.completions.create(
                model=model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            choice = response.choices[0]
            return AIResponse(
                content=choice.message.content or "",
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                } if response.usage else None,
                finish_reason=choice.finish_reason,
            )

        except Exception as e:
            logger.error(f"DeepSeek API 调用失败: {e}")
            raise

    async def chat_stream(
        self,
        messages: List[Message],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> AsyncIterator[str]:
        """流式聊天请求"""
        try:
            model = model or self._default_model

            openai_messages = [
                {"role": msg.role.value, "content": msg.content}
                for msg in messages
            ]

            stream = await self.client.chat.completions.create(
                model=model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"DeepSeek Stream 失败: {e}")
            raise

    def get_available_models(self) -> List[str]:
        """获取可用模型列表（2026 年 4 月最新）"""
        return [
            "deepseek-v4-pro",      # 1.6T 参数，49B 激活，GPT-4 级别性能
            "deepseek-v4-flash",    # 更快的轻量版本
            # 注意：deepseek-chat 和 deepseek-reasoner 将于 2026-07-24 弃用
        ]

    def validate_api_key(self) -> bool:
        """验证 API Key（同步方法，仅在启动时调用）"""
        try:
            import asyncio
            # 检查是否已在运行的事件循环中
            try:
                loop = asyncio.get_running_loop()
                logger.warning(f"{self.provider_name}: 跳过 API Key 验证（事件循环已运行）")
                return True
            except RuntimeError:
                # 没有运行的循环，可以安全调用 asyncio.run
                asyncio.run(self.client.models.list())
                return True
        except Exception as e:
            logger.debug(f"{self.provider_name} API Key 验证失败: {e}")
            return False

    @property
    def provider_name(self) -> str:
        return "DeepSeek"
