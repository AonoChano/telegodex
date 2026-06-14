from typing import List, AsyncIterator
from openai import AsyncOpenAI
from loguru import logger

from .base import BaseAIProvider, Message, AIResponse, MessageRole


class OpenAIProvider(BaseAIProvider):
    """OpenAI 服务商实现"""

    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        self.client = AsyncOpenAI(api_key=api_key)
        self._default_model = "gpt-4o"  # GPT-5 未公开时使用 GPT-4

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
            logger.error(f"OpenAI API 调用失败: {e}")
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
            logger.error(f"OpenAI Stream 失败: {e}")
            raise

    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
            # GPT-5 发布后添加: "gpt-5"
        ]

    def validate_api_key(self) -> bool:
        """验证 API Key"""
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
        return "OpenAI"
