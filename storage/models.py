from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship
from loguru import logger

Base = declarative_base()


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)  # Telegram User ID
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    language_code = Column(String(10), nullable=True)
    is_admin = Column(Boolean, default=False)
    is_blocked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 用户偏好
    preferred_provider = Column(String(50), default="openai")  # AI 服务商
    preferred_model = Column(String(100), nullable=True)
    temperature = Column(String(10), default="0.7")

    # 关系
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")


class Conversation(Base):
    """对话会话表"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(500), nullable=True)  # 对话标题（自动生成）
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # 关系
    user = relationship("User", back_populates="conversations")
    messages = relationship("ConversationMessage", back_populates="conversation", cascade="all, delete-orphan")


class ConversationMessage(Base):
    """对话消息表"""
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)

    # AI 响应元数据
    provider = Column(String(50), nullable=True)  # 使用的 AI 服务商
    model = Column(String(100), nullable=True)  # 使用的模型
    tokens_used = Column(Integer, nullable=True)  # token 使用量

    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    conversation = relationship("Conversation", back_populates="messages")


class Database:
    """数据库管理器"""

    def __init__(self, database_url: str):
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def init_db(self):
        """初始化数据库表"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✓ 数据库初始化完成")

    async def get_session(self) -> AsyncSession:
        """获取数据库会话"""
        async with self.async_session() as session:
            yield session

    async def close(self):
        """关闭数据库连接"""
        await self.engine.dispose()
        logger.info("数据库连接已关闭")
