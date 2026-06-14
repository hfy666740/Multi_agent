# db_models.py — SQLAlchemy ORM 数据模型定义
# 技术栈: SQLAlchemy 2.0 (ORM 映射), PostgreSQL (关系型数据库)
# 说明: 定义项目中所有数据库表的 ORM 模型，与现有 PostgreSQL schema 保持一致

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey,
    func, UniqueConstraint, Index, TIMESTAMP
)
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from sqlalchemy.sql import func as sqlfunc
import uuid


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""
    pass


class User(Base):
    """用户表 — 存储用户注册信息、角色和状态"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, comment="用户名")
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, comment="邮箱")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码哈希(bcrypt)")
    role: Mapped[str] = mapped_column(String(20), default="user", comment="角色: user/admin")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=sqlfunc.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=sqlfunc.now(), onupdate=sqlfunc.now(), comment="更新时间")

    chat_sessions = relationship("ChatSession", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"


class ChatSession(Base):
    """聊天会话表 — 存储用户的对话会话"""
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, comment="会话唯一标识(UUID)")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, comment="关联用户ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=sqlfunc.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=sqlfunc.now(), onupdate=sqlfunc.now(), comment="最后更新时间")

    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    token_records = relationship("TokenUsage", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_sessions_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<ChatSession(session_id={self.session_id})>"


class ChatMessage(Base):
    """聊天消息表 — 存储会话中的每条消息"""
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(100), ForeignKey("chat_sessions.session_id", ondelete="CASCADE"), nullable=False, comment="所属会话ID")
    role: Mapped[str] = mapped_column(String(20), nullable=False, comment="角色: user/assistant/system")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息内容")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=sqlfunc.now(), comment="发送时间")

    session = relationship("ChatSession", back_populates="messages")

    __table_args__ = (
        Index("idx_messages_session_id", "session_id"),
    )

    def __repr__(self):
        return f"<ChatMessage(session_id={self.session_id}, role={self.role})>"


class TokenUsage(Base):
    """Token 使用记录表 — 追踪每次 LLM 调用的 Token 消耗"""
    __tablename__ = "token_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, comment="调用来源: supervisor/knowledge/weather/report/direct")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, comment="输入(Prompt) Token 数")
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, comment="输出(Completion) Token 数")
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, comment="总 Token 数")
    session_id: Mapped[str] = mapped_column(String(100), ForeignKey("chat_sessions.session_id", ondelete="SET NULL"), nullable=True, comment="关联会话ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=sqlfunc.now(), comment="记录时间")

    session = relationship("ChatSession", back_populates="token_records")

    __table_args__ = (
        Index("idx_token_usage_source", "source"),
        Index("idx_token_usage_session", "session_id"),
        Index("idx_token_usage_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<TokenUsage(source={self.source}, total={self.total_tokens})>"
