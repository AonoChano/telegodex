from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class MessageRole(str, Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Message:
    """统一消息格式"""
    role: MessageRole
    content: str
    metadata: Dict[str, Any] | None = None


@dataclass
class AIResponse:
    """AI 响应结果"""
    content: str
    model: str
    usage: Dict[str, int] | None = None  # tokens 使用情况
    finish_reason: str | None = None
    metadata: Dict[str, Any] | None = None


class BaseAIProvider(ABC):
    """AI 服务商基类 - 统一接口"""

    def __init__(self, api_key: str, **kwargs):
        self.api_key = api_key
        self.config = kwargs

    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        **kwargs
    ) -> AIResponse:
        """
        发送聊天请求

        Args:
            messages: 消息历史
            model: 模型名称（None 使用默认）
            temperature: 温度参数
            max_tokens: 最大 token 数
            stream: 是否流式输出
            **kwargs: 其他服务商特定参数

        Returns:
            AIResponse 对象
        """
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: List[Message],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        流式聊天请求

        Yields:
            逐步生成的文本片段
        """
        pass

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        pass

    @abstractmethod
    def validate_api_key(self) -> bool:
        """验证 API Key 是否有效"""
        pass

    def format_telegram_markdown(self, text: str) -> str:
        """
        格式化为 Telegram MarkdownV2
        子类可覆盖以实现特定格式转换
        """
        # 转义 MarkdownV2 特殊字符
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """服务商名称"""
        pass
