from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai.base import Message, MessageRole

from .models import Conversation, ConversationMessage, User


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
        self, user_id: int, thread_id: int | None = None
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
        result = await self.session.execute(
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                thread_clause,
                Conversation.is_active.is_(True),
            )
            .order_by(desc(Conversation.updated_at))
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            conversation = Conversation(
                user_id=user_id,
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

    async def add_message(
        self,
        conversation_id: int,
        role: MessageRole,
        content: str,
        provider: str | None = None,
        model: str | None = None,
        tokens_used: int | None = None,
    ) -> ConversationMessage:
        """添加消息到对话"""
        message = ConversationMessage(
            conversation_id=conversation_id,
            role=role.value,
            content=content,
            provider=provider,
            model=model,
            tokens_used=tokens_used,
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
        self, user_id: int, thread_id: int | None = None
    ) -> Conversation:
        """在同一 thread 内结束当前活跃对话并开启新对话。"""
        thread_clause = (
            Conversation.thread_id.is_(None)
            if thread_id is None
            else Conversation.thread_id == thread_id
        )

        # 结束当前 thread 内的活跃对话（其他 thread 不受影响）
        result = await self.session.execute(
            select(Conversation).where(
                Conversation.user_id == user_id,
                thread_clause,
                Conversation.is_active.is_(True),
            )
        )
        active_conversations = result.scalars().all()

        for conv in active_conversations:
            conv.is_active = False

        # 创建新对话
        new_conversation = Conversation(
            user_id=user_id,
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
