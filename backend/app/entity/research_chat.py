from datetime import datetime, timezone
from ..utils.tools import UTC8
from sqlalchemy import Column, BigInteger, String, Text, Boolean, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ResearchChatSession(Base):
    """研究聊天会话表 - research_chat_sessions"""
    __tablename__ = 'research_chat_sessions'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    page_session_id = Column(String(128), nullable=False, index=True)
    session_name = Column(String(255), nullable=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    email = Column(String(128), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC8))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC8), onupdate=lambda: datetime.now(UTC8))


class ResearchChatMessage(Base):
    """研究聊天消息表 - research_chat_messages"""
    __tablename__ = 'research_chat_messages'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(BigInteger, ForeignKey('research_chat_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    email = Column(String(128), nullable=False, index=True)
    content = Column(Text, nullable=False)
    result_papers = Column(JSON, nullable=True)
    extra_info = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC8))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC8), onupdate=lambda: datetime.now(UTC8))


class ResearchChatProcessInfo(Base):
    """研究聊天进程信息表 - research_chat_process_infos"""
    __tablename__ = 'research_chat_process_infos'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(BigInteger, ForeignKey('research_chat_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    message_id = Column(BigInteger, ForeignKey('research_chat_messages.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    email = Column(String(128), nullable=False, index=True)
    process_info = Column(JSON, nullable=True)
    extra_info = Column(JSON, nullable=True)
    creation_status = Column(
        Enum('pending', 'creating', 'created', 'failed', name='creation_status_enum'),
        nullable=False,
        default='pending'
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC8))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC8), onupdate=lambda: datetime.now(UTC8))
