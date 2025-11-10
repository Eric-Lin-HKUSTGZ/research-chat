"""
FastAPI Authentication Service
提供JWT认证和用户验证
"""
import hashlib
import hmac
import base64
import jwt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.entity.auth import User
from app.core.database import get_db
from app.core.config import get_jwt_config
from sqlalchemy import select
from app.utils.logger import get_logger
from app.utils.tools import UTC8

logger = get_logger('auth_fastapi')


def md5_hash(text: str) -> str:
    """MD5哈希"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()


# JWT Manager for FastAPI
class JWTManager:
    """JWT管理器"""

    def __init__(self):
        self.config = get_jwt_config()

    def generate_token(self, user_id, email):
        """
        生成JWT访问令牌

        Args:
            user_id (int): 用户ID
            email (str): 邮箱

        Returns:
            str: JWT令牌
        """
        now = datetime.now(UTC8)
        payload = {
            'user_id': user_id,
            'email': email,
            'iat': now,
            'exp': now + timedelta(seconds=self.config['expires']),
            'type': 'access'
        }

        token = jwt.encode(
            payload,
            self.config['secret_key'],
            algorithm=self.config['algorithm']
        )

        logger.info(f"Generated JWT token for user {email} (ID: {user_id})")
        return token

    def decode_token(self, token):
        """
        解码JWT令牌

        Args:
            token (str): JWT令牌

        Returns:
            dict: 解码后的payload，如果失败返回None
        """
        try:
            logger.debug("Attempting to decode JWT token")

            # 先做 HMAC 签名规范性检查（防止非规范base64url篡改未改变字节导致绕过）
            alg = self.config['algorithm']
            if alg in {'HS256', 'HS384', 'HS512'}:
                parts = token.split('.')
                if len(parts) != 3:
                    logger.warning("Invalid JWT format: not 3 segments")
                    return None
                header_b64, payload_b64, sig_b64 = parts
                signing_input = f"{header_b64}.{payload_b64}".encode('ascii')
                hash_name = {'HS256': 'sha256', 'HS384': 'sha384', 'HS512': 'sha512'}[alg]
                digestmod = getattr(hashlib, hash_name)
                expected_sig = hmac.new(self.config['secret_key'].encode('utf-8'), signing_input, digestmod).digest()
                canonical_sig_b64 = base64.urlsafe_b64encode(expected_sig).rstrip(b'=').decode('ascii')
                if sig_b64 != canonical_sig_b64:
                    logger.warning("JWT signature segment non-canonical or mismatched")
                    return None

            payload = jwt.decode(
                token,
                self.config['secret_key'],
                algorithms=[alg]
            )

            # 检查令牌类型
            if payload.get('type') != 'access':
                logger.warning(f"Invalid token type: {payload.get('type')}")
                return None

            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"JWT decode error: {str(e)}")
            return None


# 全局JWT管理器实例
jwt_manager = JWTManager()


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> dict:
    """
    FastAPI依赖：从Authorization header获取当前用户

    Args:
        authorization: Authorization header (格式: "Bearer <token>")
        db: 数据库会话

    Returns:
        dict: 用户信息 {user_id, email}

    Raises:
        HTTPException: 401 未授权
    """
    if not authorization:
        logger.warning("未提供Authorization header")
        raise HTTPException(
            status_code=401,
            detail="未授权：缺少认证令牌",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # 解析 "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.warning(f"无效的Authorization格式: {authorization}")
        raise HTTPException(
            status_code=401,
            detail="未授权：无效的认证格式",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = parts[1]

    # 验证JWT
    payload = jwt_manager.decode_token(token)
    if not payload:
        logger.warning(f"JWT验证失败")
        raise HTTPException(
            status_code=401,
            detail="未授权：令牌无效或已过期",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = payload.get('user_id')
    email = payload.get('email')

    if not user_id or not email:
        logger.error(f"JWT payload缺少必要字段: {payload}")
        raise HTTPException(
            status_code=401,
            detail="未授权：令牌数据不完整"
        )

    # 验证用户是否存在且活跃
    query = select(User).where(User.id == user_id, User.is_active == True)
    user = db.execute(query).scalar_one_or_none()

    if not user:
        logger.warning(f"用户不存在或未激活: user_id={user_id}")
        raise HTTPException(
            status_code=401,
            detail="未授权：用户不存在或已禁用"
        )

    logger.debug(f"用户认证成功: user_id={user_id}, email={email}")

    return {
        "user_id": user_id,
        "email": email
    }


def verify_user_credentials(email: str, password: str, db: Session) -> Optional[User]:
    """
    验证用户凭据

    Args:
        email: 邮箱
        password: 明文密码
        db: 数据库会话

    Returns:
        User: 验证成功返回用户对象，否则返回None
    """
    password_hash = md5_hash(password)

    query = select(User).where(
        User.email == email,
        User.password_hash == password_hash,
        User.is_active == True
    )

    user = db.execute(query).scalar_one_or_none()

    if user:
        logger.info(f"用户凭据验证成功: {email}")
    else:
        logger.warning(f"用户凭据验证失败: {email}")

    return user


def generate_access_token(user: User) -> str:
    """
    生成访问令牌

    Args:
        user: 用户对象

    Returns:
        str: JWT访问令牌
    """
    token = jwt_manager.generate_token(str(user.id), user.email)
    logger.info(f"为用户生成访问令牌: user_id={user.id}, email={user.email}")

    return token
