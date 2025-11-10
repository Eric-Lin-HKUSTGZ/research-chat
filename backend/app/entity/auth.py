"""
User Entity - 用户实体模型
支持 users 表结构
"""
from datetime import datetime
from ..utils.tools import UTC8
from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    """用户表 - users"""
    __tablename__ = 'users'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    email = Column(String(128), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    username = Column(String(255), nullable=True)
    identity_tag = Column(
        Enum('student', 'researcher', 'pioneer', name='identity_tag_enum'),
        nullable=True,
        default=None
    )
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now(UTC8))
    updated_at = Column(DateTime, nullable=False, default=datetime.now(UTC8), onupdate=datetime.now(UTC8))

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'identity_tag': self.identity_tag,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
