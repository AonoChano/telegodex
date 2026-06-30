from collections.abc import AsyncIterator
from typing import Any

from loguru import logger
from openai import AsyncOpenAI

from .base import AIResponse, BaseAIProvider, Message


class OpenAICompatibleProvider(BaseAIProvider):
    """
    OpenAI 兼容 API 通用 Provider
    支持任何实现了 OpenAI API 格式的服务商（国内外通用）
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        provider_name: str = "Custom",
        default_model: str = "gpt-3.5-turbo",
        available_models: list[str] | None = None,
        headers: dict[str, str] | None = None,
        query: dict[str, str] | None = None,
        **kwargs
    ):
        """
        初始化 OpenAI 兼容 Provider

        Args:
            api_key: API Key
            base_url: API 基础 URL（例如：https://api.example.com/v1）
            provider_name: 服务商名称（用于日志和显示）
            default_model: 默认模型名称
            available_models: 可用模型列表
        """
        super().__init__(api_key, **kwargs)
        client_kwargs: dict[str, Any] = {"api_key": api_key, "base_url": base_url}
        if headers:
            client_kwargs["default_headers"] = headers
        if query:
            client_kwargs["default_query"] = query
        self.client = AsyncOpenAI(**client_kwargs)
        self._provider_name = provider_name
        self._default_model = default_model
        self._available_models = available_models or [default_model]

    async def chat(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        **kwargs
    ) -> AIResponse:
        """发送聊天请求"""
        try:
            model = model or self._default_model

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
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                } if response.usage else None,
                finish_reason=choice.finish_reason,
            )

        except Exception as e:
            logger.error(f"{self._provider_name} API 调用失败: {e}")
            raise

    async def chat_stream(
        self,
        messages: list[Message],
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
            logger.error(f"{self._provider_name} Stream 失败: {e}")
            raise

    def get_available_models(self) -> list[str]:
        """获取可用模型列表"""
        return self._available_models

    def validate_api_key(self) -> bool:
        """验证 API Key"""
        try:
            import asyncio
            # 检查是否已在运行的事件循环中
            try:
                asyncio.get_running_loop()
                logger.warning(f"{self._provider_name}: 跳过 API Key 验证（事件循环已运行）")
                return True
            except RuntimeError:
                # 没有运行的循环，可以安全调用 asyncio.run
                try:
                    asyncio.run(self.client.models.list())
                    return True
                except Exception:
                    # 某些 API 可能不支持 models.list()，尝试简单的 chat 请求
                    asyncio.run(self.client.chat.completions.create(
                        model=self._default_model,
                        messages=[{"role": "user", "content": "test"}],
                        max_tokens=1
                    ))
                    return True
        except Exception as e:
            logger.debug(f"{self._provider_name} API Key 验证失败: {e}")
            return False

    @property
    def provider_name(self) -> str:
        return self._provider_name
