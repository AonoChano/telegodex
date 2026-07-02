from datetime import datetime

from loguru import logger
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Mapped, declarative_base, relationship

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
    tool_permission_mode = Column(String(20), default="confirm")
    ui_language = Column(String(10), nullable=True)  # UI language preference (e.g., "zh-cn", "en")
    # 关系
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")


class Conversation(Base):
    """对话会话表"""

    __tablename__ = "conversations"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id"), nullable=False)
    # Telegram chat_id (group/supergroup/DM identifier)
    chat_id: Mapped[int | None] = Column(BigInteger, nullable=True)
    title: Mapped[str | None] = Column(String(500), nullable=True)  # 对话标题（自动生成）
    # Telegram topic / message_thread_id；普通私聊下为 NULL，相当于旧版的"全局会话"
    thread_id: Mapped[int | None] = Column(BigInteger, nullable=True)
    # Transport name for multi-transport support (e.g. "telegram")
    transport: Mapped[str | None] = Column(String(50), nullable=True)
    # Normalized topic id ( mirrors thread_id for new records )
    topic_id: Mapped[int | None] = Column(BigInteger, nullable=True)
    # Codex app-server thread ID（与 Telegram thread_id 不同）
    codex_thread_id: Mapped[str | None] = Column(String, nullable=True)
    # Codex 会话文件路径
    codex_thread_path: Mapped[str | None] = Column(String, nullable=True)
    # Codex working directory
    cwd: Mapped[str | None] = Column(String, nullable=True)
    # Provider-isolated session buckets: dict[str, ProviderSessionData]
    provider_sessions: Mapped[dict | None] = Column(JSON, nullable=True)
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active: Mapped[bool] = Column(Boolean, default=True)

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    messages: Mapped[list["ConversationMessage"]] = relationship(
        "ConversationMessage", back_populates="conversation", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # 一个用户在同一 thread 内只保留少量活跃会话，定位最快
        Index("ix_conversations_user_thread_active", "user_id", "thread_id", "is_active"),
        Index("ix_conversations_user_chat_thread_active", "user_id", "chat_id", "thread_id", "is_active"),
    )


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
        self.async_session = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    async def init_db(self):
        """初始化数据库表，并对老库做轻量列补齐"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await self._ensure_column(conn, "conversations", "chat_id", "BIGINT")
            await self._ensure_column(conn, "conversations", "thread_id", "BIGINT")
            await self._ensure_column(conn, "conversations", "transport", "VARCHAR")
            await self._ensure_column(conn, "conversations", "topic_id", "BIGINT")
            await self._ensure_column(conn, "conversations", "codex_thread_id", "VARCHAR")
            await self._ensure_column(conn, "conversations", "codex_thread_path", "VARCHAR")
            await self._ensure_column(conn, "conversations", "cwd", "VARCHAR")
            await self._ensure_column(conn, "conversations", "provider_sessions", "JSON")
            await self._ensure_column(conn, "users", "tool_permission_mode", "VARCHAR(20)")
            await self._ensure_column(conn, "users", "ui_language", "VARCHAR(10)")
            await self._ensure_index(conn, "conversations", "ix_conversations_user_chat_thread_active")
        logger.info("✓ 数据库初始化完成")

    async def _ensure_column(self, conn, table_name: str, column_name: str, column_type: str) -> None:
        """
        轻量 schema 迁移：列已存在则跳过，不存在则 ADD COLUMN。

        兼容 SQLite / PostgreSQL / MySQL。SQLite 没有
        ``ALTER TABLE ... ADD COLUMN IF NOT EXISTS``，需要先 ``PRAGMA`` 探测。
        """
        dialect = self.engine.dialect.name
        if dialect == "sqlite":
            result = await conn.execute(text(f"PRAGMA table_info({table_name})"))
            existing = {row[1] for row in result.fetchall()}
            if column_name in existing:
                return
            await conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
        else:
            # PostgreSQL 9.6+ / MySQL 8.0+ 都支持 IF NOT EXISTS
            await conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_name} {column_type}"))
        logger.info(f"Schema migration: added {table_name}.{column_name}")

    async def _ensure_index(self, conn, table_name: str, index_name: str) -> None:
        """Create a metadata-defined index for existing databases if missing."""
        table = Base.metadata.tables[table_name]
        index = next((idx for idx in table.indexes if idx.name == index_name), None)
        if index is None:
            raise RuntimeError(f"Index {index_name} is not defined on table {table_name}")
        await conn.run_sync(lambda sync_conn: index.create(sync_conn, checkfirst=True))

    async def get_session(self) -> AsyncSession:
        """获取数据库会话"""
        async with self.async_session() as session:
            yield session

    async def close(self):
        """关闭数据库连接"""
        await self.engine.dispose()
        logger.info("数据库连接已关闭")
