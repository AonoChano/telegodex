"""Reaction tracker: maps Codex events to Telegram message reactions."""

from __future__ import annotations

import asyncio

from aiogram import Bot
from aiogram.types import ReactionTypeEmoji
from loguru import logger

_REACTION_STATES: dict[str, str] = {
    "thinking": "🤔",
    "reading": "👀",
    "editing": "✍️",
    "shell": "👨‍💻",
    "done": "✅",
}


class ReactionTracker:
    """包装 Telegram ``setMessageReaction`` API，为 Codex 流式事件提供状态映射。

    状态与 emoji 映射：
    * thinking → 🤔
    * reading → 👀
    * editing → ✍️
    * shell → 👨‍💻
    * done → ✅
    """

    def __init__(
        self,
        bot: Bot,
        chat_id: int | str,
        message_id: int,
    ) -> None:
        self._bot = bot
        self._chat_id = chat_id
        self._message_id = message_id
        self._current_state: str | None = None
        self._lock = asyncio.Lock()

    async def set_state(self, state: str) -> None:
        """设置消息反应状态。同一状态不会重复发送 API 请求。"""
        emoji = _REACTION_STATES.get(state)
        if emoji is None:
            return

        async with self._lock:
            if self._current_state == state:
                return
            self._current_state = state
            try:
                await self._bot.set_message_reaction(
                    chat_id=self._chat_id,
                    message_id=self._message_id,
                    reaction=[ReactionTypeEmoji(emoji=emoji)],
                )
            except Exception as exc:
                logger.debug(f"ReactionTracker set_state failed: {exc}")

    async def clear(self) -> None:
        """清除消息反应。"""
        async with self._lock:
            self._current_state = None
            try:
                await self._bot.set_message_reaction(
                    chat_id=self._chat_id,
                    message_id=self._message_id,
                    reaction=[],
                )
            except Exception as exc:
                logger.debug(f"ReactionTracker clear failed: {exc}")

    async def on_codex_event(self, method: str, item_type: str | None = None) -> None:
        """根据 Codex JSON-RPC 事件方法自动映射并设置反应状态。"""
        state = self.map_codex_event(method, item_type)
        if state is not None:
            await self.set_state(state)

    @classmethod
    def map_codex_event(cls, method: str, item_type: str | None = None) -> str | None:
        """将 Codex JSON-RPC 事件映射为反应状态。

        返回 ``None`` 表示无需切换状态。
        """
        if method == "item/started":
            if item_type == "commandExecution":
                return "shell"
            if item_type == "reasoning":
                return "thinking"
            return "reading"
        if method == "item/reasoning/summaryTextDelta":
            return "thinking"
        if method == "item/commandExecution/outputDelta":
            return "shell"
        if method == "item/agentMessage/delta":
            return "editing"
        if method == "turn/completed":
            return "done"
        if method == "error":
            return None
        return None
