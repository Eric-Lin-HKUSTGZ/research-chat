"""
Database Session Management for FastAPI
纯 SQLAlchemy 数据库会话管理
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
from app.core.config import Config

# 创建数据库引擎
engine = create_engine(
    Config.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=20,
    max_overflow=40,
    pool_timeout=15,
    echo=False  # 默认不输出SQL日志
)

# 创建会话工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI 依赖注入：获取数据库会话

    Yields:
        Session: SQLAlchemy 会话对象
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    上下文管理器：获取数据库会话

    Yields:
        Session: SQLAlchemy 会话对象
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
