"""
FastAPI Main Application
FastAPI 主应用
参考 digital_twin_academic/backend/app/main.py
"""
import os
import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import Config
from app.utils.logger import get_logger

logger = get_logger('main')


# 生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("=== Starting Research Chat FastAPI Application ===")
    logger.info(f"Environment: {os.getenv('APP_ENV', 'dev')}")
    logger.info(f"Database: {Config.SQLALCHEMY_DATABASE_URI}")

    yield

    # 关闭时
    logger.info("=== Shutting down Research Chat FastAPI Application ===")


def create_app() -> FastAPI:
    """
    创建FastAPI应用实例

    Returns:
        FastAPI: 应用实例
    """
    app = FastAPI(
        title="Research Chat API",
        description="科研智能体后端服务 - FastAPI",
        version="2.0.0",
        docs_url="/digital_twin/research_chat/api/docs",
        redoc_url="/digital_twin/research_chat/api/redoc",
        openapi_url="/digital_twin/research_chat/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS中间件
    cors_origins = Config.CORS_ORIGINS
    if cors_origins == "*":
        allow_origins = ["*"]
    else:
        allow_origins = [origin.strip() for origin in cors_origins.split(",")]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type", "x-page-id"],
        expose_headers=["Content-Type", "X-Request-Id", "X-Trace-Id"],
    )

    # GZip压缩
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # 请求追踪中间件
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        """添加请求追踪信息"""
        start_time = time.time()

        # 生成请求ID和追踪ID
        request_id = request.headers.get('X-Request-Id') or request.headers.get('X-Request-ID') or uuid.uuid4().hex
        trace_id = request.headers.get('X-Trace-Id') or request.headers.get('X-Trace-ID') or request_id

        # 存储到request state
        request.state.request_id = request_id
        request.state.trace_id = trace_id
        request.state.start_time = start_time

        response = await call_next(request)

        # 添加响应头
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Process-Time"] = str(time.time() - start_time)

        # 记录请求日志（跳过某些路径）
        if not any(path in request.url.path for path in ['/docs', '/redoc', '/openapi.json', '/health']):
            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(
                f"event: {request.method}, path: {request.url.path}, "
                f"status: {response.status_code}, duration_ms: {duration_ms}"
            )

        return response

    # 全局异常处理
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """全局异常处理"""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": 500,
                "message": "服务器内部错误",
                "success": False,
                "data": {}
            }
        )

    # 注册路由
    register_routers(app)

    # 根路由
    @app.get("/")
    async def root():
        return {
            "service": "Research Chat Backend API",
            "version": "2.0.0",
            "description": "科研智能体后端服务 - FastAPI",
            "docs": "/digital_twin/research_chat/api/docs"
        }

    # 健康检查
    @app.get("/health")
    async def health():
        return {
            "status": "healthy",
            "service": "research_chat_backend_fastapi"
        }

    return app


def register_routers(app: FastAPI):
    """注册所有路由"""
    from app.routes.auth import router as auth_router
    from app.routes.chat_routes import router as chat_router
    from app.routes.websocket_routes import router as websocket_router

    # 注册认证路由
    app.include_router(
        auth_router,
        tags=["Authentication"]
    )

    # 注册研究聊天路由
    app.include_router(
        chat_router,
        tags=["Research Chat"]
    )

    # 注册WebSocket路由
    app.include_router(
        websocket_router,
        prefix="/digital_twin/research_chat",
        tags=["WebSocket"]
    )

    logger.info("All routers registered successfully")


# 创建应用实例
app = create_app()
