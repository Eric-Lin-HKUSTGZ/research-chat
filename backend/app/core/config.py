import os
from datetime import timedelta


class Config:
    """应用配置类 - 参考 digital_twin_academic 的配置结构"""

    # JWT配置
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=int(os.getenv("JWT_EXPIRE_DAYS", "1")))
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

    # 数据库配置 - 使用 MySQL
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "agent!1234")
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_NAME = os.getenv("DB_NAME", "sci_agent_academic")
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # CORS配置
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

    # 速率限制配置
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "6000 per minute")
    RATELIMIT_GLOBAL = os.getenv("RATELIMIT_GLOBAL", "6000 per minute")
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", None)
    RATE_LIMIT_CHAT = os.getenv("RATE_LIMIT_CHAT", "6000 per minute")

    # Redis配置
    REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")

    # LLM服务配置
    CUSTOM_API_ENDPOINT = os.getenv("CUSTOM_API_ENDPOINT")
    CUSTOM_API_KEY = os.getenv("CUSTOM_API_KEY")
    CUSTOM_MODEL = os.getenv("CUSTOM_MODEL")
    LLM_REQUEST_TIMEOUT = int(os.getenv("LLM_REQUEST_TIMEOUT", "180"))

    # WebSocket 轮询配置
    WS_POLL_INTERVAL_SECONDS = float(os.getenv("WS_POLL_INTERVAL_SECONDS", "1"))

    # 日志配置
    LOG_MAX_BYTES = os.getenv("LOG_MAX_BYTES", "10485760")
    LOG_BACKUP_COUNT = os.getenv("LOG_BACKUP_COUNT", "30")


def get_jwt_config():
    """获取JWT配置"""
    secret = os.getenv("JWT_SECRET_KEY", Config.SECRET_KEY)
    expires = Config.JWT_ACCESS_TOKEN_EXPIRES
    if hasattr(expires, "total_seconds"):
        expires_seconds = int(expires.total_seconds())
    else:
        try:
            expires_seconds = int(expires)
        except Exception:
            expires_seconds = int(timedelta(days=1).total_seconds())
    algorithm = Config.JWT_ALGORITHM
    return {"secret_key": secret, "expires": expires_seconds, "algorithm": algorithm}


