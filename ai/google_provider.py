from collections.abc import AsyncIterator

import google.generativeai as genai
from loguru import logger

from .base import AIResponse, BaseAIProvider, Message, MessageRole


class GoogleProvider(BaseAIProvider):
    """Google (Gemini) 服务商实现"""

    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        genai.configure(api_key=api_key)
        self._default_model = "gemini-2.0-flash-exp"

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
            model_name = model or self._default_model
            model_instance = genai.GenerativeModel(model_name)

            # 转换消息格式 - Gemini 使用不同的结构
            gemini_messages = []
            for msg in messages:
                if msg.role == MessageRole.SYSTEM:
                    # Gemini 将 system 消息作为第一条 user 消息
                    gemini_messages.insert(0, {
                        "role": "user",
                        "parts": [msg.content]
                    })
                else:
                    gemini_messages.append({
                        "role": "user" if msg.role == MessageRole.USER else "model",
                        "parts": [msg.content]
                    })

            response = await model_instance.generate_content_async(
                gemini_messages,
                generation_config=genai.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    **kwargs
                )
            )

            return AIResponse(
                content=response.text,
                model=model_name,
                usage={
                    "prompt_tokens": response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
                    "completion_tokens": response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
                    "total_tokens": response.usage_metadata.total_token_count if response.usage_metadata else 0,
                },
                finish_reason=str(response.candidates[0].finish_reason) if response.candidates else None,
            )

        except Exception as e:
            logger.error(f"Google API 调用失败: {e}")
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
            model_name = model or self._default_model
            model_instance = genai.GenerativeModel(model_name)

            gemini_messages = []
            for msg in messages:
                if msg.role == MessageRole.SYSTEM:
                    gemini_messages.insert(0, {
                        "role": "user",
                        "parts": [msg.content]
                    })
                else:
                    gemini_messages.append({
                        "role": "user" if msg.role == MessageRole.USER else "model",
                        "parts": [msg.content]
                    })

            response = await model_instance.generate_content_async(
                gemini_messages,
                generation_config=genai.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    **kwargs
                ),
                stream=True
            )

            async for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"Google Stream 失败: {e}")
            raise

    def get_available_models(self) -> list[str]:
        """获取可用模型列表"""
        return [
            "gemini-2.0-flash-exp",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ]

    def validate_api_key(self) -> bool:
        """验证 API Key"""
        try:
            genai.list_models()
            return True
        except Exception:
            return False

    @property
    def provider_name(self) -> str:
        return "Google (Gemini)"
