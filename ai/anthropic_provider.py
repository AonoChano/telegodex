from collections.abc import AsyncIterator

from anthropic import AsyncAnthropic
from loguru import logger

from .base import AIResponse, BaseAIProvider, Message, MessageRole


class AnthropicProvider(BaseAIProvider):
    """Anthropic (Claude) 服务商实现"""

    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        self.client = AsyncAnthropic(api_key=api_key)
        self._default_model = "claude-opus-4-8"

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

            # Anthropic API 要求 system 消息单独传递
            system_message = None
            user_messages = []

            for msg in messages:
                if msg.role == MessageRole.SYSTEM:
                    system_message = msg.content
                else:
                    user_messages.append({
                        "role": msg.role.value,
                        "content": msg.content
                    })

            response = await self.client.messages.create(
                model=model,
                messages=user_messages,
                system=system_message,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            return AIResponse(
                content=response.content[0].text,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                },
                finish_reason=response.stop_reason,
            )

        except Exception as e:
            logger.error(f"Anthropic API 调用失败: {e}")
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

            system_message = None
            user_messages = []

            for msg in messages:
                if msg.role == MessageRole.SYSTEM:
                    system_message = msg.content
                else:
                    user_messages.append({
                        "role": msg.role.value,
                        "content": msg.content
                    })

            async with self.client.messages.stream(
                model=model,
                messages=user_messages,
                system=system_message,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            ) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            logger.error(f"Anthropic Stream 失败: {e}")
            raise

    def get_available_models(self) -> list[str]:
        """获取可用模型列表"""
        return [
            "claude-fable-5",         # 最新最强
            "claude-opus-4-8",
            "claude-sonnet-4-6",
            "claude-haiku-4-5-20251001",
        ]

    def validate_api_key(self) -> bool:
        """验证 API Key"""
        try:
            import asyncio
            asyncio.run(self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=10
            ))
            return True
        except Exception:
            return False

    @property
    def provider_name(self) -> str:
        return "Anthropic (Claude)"
