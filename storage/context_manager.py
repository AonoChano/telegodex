from dataclasses import dataclass

from loguru import logger
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai.base import Message, MessageRole

from .models import Conversation, ConversationMessage, User


@dataclass(frozen=True)
class TokenUsageSummary:
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    counted_messages: int
    estimated_messages: int


@dataclass(frozen=True)
class TokenUsageBreakdown:
    provider: str | None
    model: str | None
    total_tokens: int
    counted_messages: int


class ContextManager:
    """上下文管理器 - 管理对话历史和上下文"""

    def __init__(self, session: AsyncSession, max_context_messages: int = 50):
        self.session = session
        self.max_context_messages = max_context_messages

    async def get_or_create_user(
        self,
        user_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        language_code: str | None = None,
    ) -> User:
        """获取或创建用户"""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code,
            )
            self.session.add(user)
            await self.session.commit()
            logger.info(f"创建新用户: {user_id} (@{username})")

        return user

    async def get_or_create_conversation(
        self,
        user_id: int,
        thread_id: int | None = None,
        chat_id: int | None = None,
    ) -> Conversation:
        """获取或创建当前 thread 的活跃对话。

        ``thread_id=None`` 时落到旧版"全局会话"语义上，保证非 topic 私聊
        / 群聊行为不变；``thread_id`` 给定时则按 topic 维度隔离。
        """
        thread_clause = (
            Conversation.thread_id.is_(None)
            if thread_id is None
            else Conversation.thread_id == thread_id
        )
        scope = [
            Conversation.user_id == user_id,
            thread_clause,
            Conversation.is_active.is_(True),
        ]
        if chat_id is not None:
            scope.append(Conversation.chat_id == chat_id)

        result = await self.session.execute(
            select(Conversation)
            .where(*scope)
            .order_by(desc(Conversation.updated_at), desc(Conversation.id))
        )
        conversations = list(result.scalars().all())
        conversation = conversations[0] if conversations else None

        if len(conversations) > 1:
            for stale in conversations[1:]:
                stale.is_active = False
            await self.session.commit()
            logger.warning(
                "Archived duplicate active conversations: "
                f"user_id={user_id}, chat_id={chat_id}, thread_id={thread_id}, "
                f"kept_conversation_id={conversation.id}, "
                f"archived={len(conversations) - 1}"
            )

        if not conversation:
            conversation = Conversation(
                user_id=user_id,
                chat_id=chat_id,
                thread_id=thread_id,
                topic_id=thread_id,
                transport="telegram",
                title="新对话",
            )
            self.session.add(conversation)
            await self.session.commit()
            logger.info(
                f"创建新对话: user_id={user_id}, thread_id={thread_id}"
            )

        return conversation

    async def get_active_conversation(
        self,
        user_id: int,
        thread_id: int | None = None,
        chat_id: int | None = None,
    ) -> Conversation | None:
        """Return the current active conversation without creating one."""
        thread_clause = (
            Conversation.thread_id.is_(None)
            if thread_id is None
            else Conversation.thread_id == thread_id
        )
        scope = [
            Conversation.user_id == user_id,
            thread_clause,
            Conversation.is_active.is_(True),
        ]
        if chat_id is not None:
            scope.append(Conversation.chat_id == chat_id)

        result = await self.session.execute(
            select(Conversation)
            .where(*scope)
            .order_by(desc(Conversation.updated_at), desc(Conversation.id))
        )
        return result.scalars().first()

    async def add_message(
        self,
        conversation_id: int,
        role: MessageRole,
        content: str,
        provider: str | None = None,
        model: str | None = None,
        tokens_used: int | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        token_count_estimated: bool | None = None,
        tokenizer_name: str | None = None,
    ) -> ConversationMessage:
        """添加消息到对话"""
        message = ConversationMessage(
            conversation_id=conversation_id,
            role=role.value,
            content=content,
            provider=provider,
            model=model,
            tokens_used=tokens_used,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            token_count_estimated=token_count_estimated,
            tokenizer_name=tokenizer_name,
        )
        self.session.add(message)
        await self.session.commit()
        return message

    async def get_conversation_history(
        self,
        conversation_id: int,
        limit: int | None = None,
    ) -> list[Message]:
        """获取对话历史"""
        limit = limit or self.max_context_messages

        result = await self.session.execute(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(desc(ConversationMessage.created_at))
            .limit(limit)
        )
        messages = result.scalars().all()

        # 转换为 AI Message 格式（倒序）
        return [
            Message(
                role=MessageRole(msg.role),
                content=msg.content,
                metadata={
                    "provider": msg.provider,
                    "model": msg.model,
                    "tokens": msg.tokens_used,
                }
            )
            for msg in reversed(messages)
        ]

    async def clear_conversation(self, conversation_id: int):
        """清空对话历史"""
        result = await self.session.execute(
            select(ConversationMessage).where(
                ConversationMessage.conversation_id == conversation_id
            )
        )
        messages = result.scalars().all()

        for msg in messages:
            await self.session.delete(msg)

        await self.session.commit()
        logger.info(f"清空对话历史: conversation_id={conversation_id}")

    async def create_new_conversation(
        self,
        user_id: int,
        thread_id: int | None = None,
        chat_id: int | None = None,
    ) -> Conversation:
        """在同一 thread 内结束当前活跃对话并开启新对话。"""
        thread_clause = (
            Conversation.thread_id.is_(None)
            if thread_id is None
            else Conversation.thread_id == thread_id
        )

        # 结束当前 thread 内的活跃对话（其他 thread 不受影响）
        scope = [
            Conversation.user_id == user_id,
            thread_clause,
            Conversation.is_active.is_(True),
        ]
        if chat_id is not None:
            scope.append(Conversation.chat_id == chat_id)

        result = await self.session.execute(select(Conversation).where(*scope))
        active_conversations = result.scalars().all()

        for conv in active_conversations:
            conv.is_active = False

        # 创建新对话
        new_conversation = Conversation(
            user_id=user_id,
            chat_id=chat_id,
            thread_id=thread_id,
            topic_id=thread_id,
            transport="telegram",
            title="新对话",
        )
        self.session.add(new_conversation)
        await self.session.commit()

        logger.info(
            f"创建新对话: user_id={user_id}, thread_id={thread_id}, "
            f"conversation_id={new_conversation.id}"
        )
        return new_conversation

    async def get_user_conversations(self, user_id: int, limit: int = 10) -> list[Conversation]:
        """获取用户的对话列表"""
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_conversation_token_usage(self, conversation_id: int) -> TokenUsageSummary:
        """Aggregate recorded AI Chat token usage for one conversation."""
        result = await self.session.execute(
            select(
                func.coalesce(func.sum(ConversationMessage.tokens_used), 0),
                func.coalesce(func.sum(ConversationMessage.prompt_tokens), 0),
                func.coalesce(func.sum(ConversationMessage.completion_tokens), 0),
                func.count(ConversationMessage.id),
            ).where(
                ConversationMessage.conversation_id == conversation_id,
                ConversationMessage.tokens_used.is_not(None),
            )
        )
        total_tokens, prompt_tokens, completion_tokens, counted_messages = result.one()
        estimated_messages = await self._count_estimated_messages(
            ConversationMessage.conversation_id == conversation_id
        )
        return TokenUsageSummary(
            total_tokens=int(total_tokens or 0),
            prompt_tokens=int(prompt_tokens or 0),
            completion_tokens=int(completion_tokens or 0),
            counted_messages=int(counted_messages or 0),
            estimated_messages=estimated_messages,
        )

    async def get_user_token_usage(self, user_id: int) -> TokenUsageSummary:
        """Aggregate recorded AI Chat token usage since the user first used the bot."""
        result = await self.session.execute(
            select(
                func.coalesce(func.sum(ConversationMessage.tokens_used), 0),
                func.coalesce(func.sum(ConversationMessage.prompt_tokens), 0),
                func.coalesce(func.sum(ConversationMessage.completion_tokens), 0),
                func.count(ConversationMessage.id),
            )
            .join(Conversation, Conversation.id == ConversationMessage.conversation_id)
            .where(
                Conversation.user_id == user_id,
                ConversationMessage.tokens_used.is_not(None),
            )
        )
        total_tokens, prompt_tokens, completion_tokens, counted_messages = result.one()
        estimated_messages = await self._count_estimated_messages(Conversation.user_id == user_id)
        return TokenUsageSummary(
            total_tokens=int(total_tokens or 0),
            prompt_tokens=int(prompt_tokens or 0),
            completion_tokens=int(completion_tokens or 0),
            counted_messages=int(counted_messages or 0),
            estimated_messages=estimated_messages,
        )

    async def get_user_token_usage_by_model(
        self,
        user_id: int,
        limit: int = 5,
    ) -> list[TokenUsageBreakdown]:
        """Return the user's largest AI Chat token buckets by provider/model."""
        total_expr = func.coalesce(func.sum(ConversationMessage.tokens_used), 0).label("total_tokens")
        result = await self.session.execute(
            select(
                ConversationMessage.provider,
                ConversationMessage.model,
                total_expr,
                func.count(ConversationMessage.id),
            )
            .join(Conversation, Conversation.id == ConversationMessage.conversation_id)
            .where(
                Conversation.user_id == user_id,
                ConversationMessage.tokens_used.is_not(None),
            )
            .group_by(ConversationMessage.provider, ConversationMessage.model)
            .order_by(total_expr.desc())
            .limit(limit)
        )
        return [
            TokenUsageBreakdown(
                provider=provider,
                model=model,
                total_tokens=int(total_tokens or 0),
                counted_messages=int(counted_messages or 0),
            )
            for provider, model, total_tokens, counted_messages in result.all()
        ]

    async def _count_estimated_messages(self, *where_clauses) -> int:
        result = await self.session.execute(
            select(func.count(ConversationMessage.id))
            .join(Conversation, Conversation.id == ConversationMessage.conversation_id)
            .where(
                *where_clauses,
                ConversationMessage.tokens_used.is_not(None),
                ConversationMessage.token_count_estimated.is_(True),
            )
        )
        return int(result.scalar_one() or 0)
