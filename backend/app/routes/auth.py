"""
FastAPI Authentication Routes - FastAPI认证路由模块
处理用户登录功能
参考 digital_twin_academic/backend/app/routes/email_auth.py
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.auth import verify_user_credentials, generate_access_token
from app.utils.logger import get_logger

logger = get_logger('auth_fastapi')

# 创建APIRouter
router = APIRouter(prefix="/digital_twin/research_chat/api/auth", tags=["auth"])


# Pydantic Models
class LoginRequest(BaseModel):
    """登录请求"""
    email: EmailStr = Field(..., description="用户邮箱")
    password: str = Field(..., min_length=1, description="用户密码")


class UserResponse(BaseModel):
    """用户响应"""
    id: int
    email: str
    username: Optional[str] = None
    identity_tag: Optional[str] = None
    is_active: bool
    created_at: str
    updated_at: str


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str
    token_type: str
    user: dict


class APIResponse(BaseModel):
    """统一API响应格式"""
    code: int
    message: str
    success: bool
    data: dict


def create_response(data=None, message="Success", code=200):
    """创建统一的响应格式"""
    return {
        "code": code,
        "message": message,
        "success": code < 400,
        "data": data if data is not None else {}
    }


@router.post("/login", response_model=APIResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    用户登录

    Args:
        request: 登录请求，包含email和password
        db: 数据库会话

    Returns:
        APIResponse: 统一响应格式，包含access_token和用户信息

    Raises:
        HTTPException: 400/401/403/404 等错误
    """
    try:
        email = request.email.strip().lower()
        password = request.password

        logger.info(f"用户尝试登录: {email}")

        # 验证用户凭据
        user = verify_user_credentials(email, password, db)

        if not user:
            logger.warning(f"登录失败：用户不存在或密码错误: {email}")
            raise HTTPException(
                status_code=401,
                detail="邮箱或密码错误"
            )

        # 检查用户状态
        if not user.is_active:
            logger.warning(f"登录失败：用户已被禁用: {email}")
            raise HTTPException(
                status_code=403,
                detail="用户已被禁用"
            )

        # 生成token
        token = generate_access_token(user)

        logger.info(f"用户登录成功: {email}")

        return create_response(
            code=200,
            message="登录成功",
            data={
                "access_token": token,
                "token_type": "Bearer",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "identity_tag": user.identity_tag,
                    "is_active": user.is_active,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "updated_at": user.updated_at.isoformat() if user.updated_at else None
                }
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"登录失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="服务器内部错误"
        )


@router.get("/health")
async def auth_health():
    """认证服务健康检查"""
    return {
        "status": "healthy",
        "service": "research_chat_auth"
    }
