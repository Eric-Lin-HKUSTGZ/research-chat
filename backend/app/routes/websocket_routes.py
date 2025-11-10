# -*- coding: utf-8 -*-
"""
WebSocket路由模块
WebSocket Routes for Real-time Communication
"""

import json
import time
import asyncio
from typing import Dict, List, Optional
from fastapi import WebSocket, WebSocketDisconnect, Depends
from fastapi.routing import APIRouter

from app.services.auth import jwt_manager
from app.core.database import SessionLocal
from app.utils.logger import get_logger
from app.entity.research_chat import ResearchChatProcessInfo
from app.constants.task_status import CreationStatus
from sqlalchemy import select
from app.core.config import Config

logger = get_logger('websocket')

router = APIRouter()


async def validate_message_exists(message_id: int) -> Optional[ResearchChatProcessInfo]:
    """
    任务存在性验证依赖（Dependency）

    验证 message_id 对应的任务是否存在于数据库

    Args:
        message_id: 消息ID

    Returns:
        任务对象（如果存在）或 None（如果不存在或查询异常）
    """
    try:
        with SessionLocal() as db:
            stmt = select(ResearchChatProcessInfo).where(
                ResearchChatProcessInfo.message_id == message_id
            )
            result = db.execute(stmt).scalar_one_or_none()

            if result:
                logger.info(f"任务验证通过: message_id={message_id}")
            else:
                logger.warning(f"任务不存在: message_id={message_id}")

            return result
    except Exception as e:
        logger.error(f"任务验证异常: message_id={message_id}, error={e}", exc_info=True)
        return None


async def authenticate_websocket(websocket: WebSocket) -> Optional[dict]:
    """
    WebSocket 认证依赖（Dependency）

    从 query 参数获取并验证 JWT token
    注意：浏览器原生 WebSocket API 不支持自定义 header，必须使用 query 参数

    Args:
        websocket: WebSocket 连接对象

    Returns:
        认证成功返回用户信息字典 {"user_id": str, "email": str}
        认证失败返回 None
    """
    try:
        # 从 query 参数获取 token
        token = websocket.query_params.get("token")

        if not token:
            logger.warning("WebSocket 认证失败: 缺少 token 参数")
            return None

        # 验证 JWT 令牌
        payload = jwt_manager.decode_token(token)
        if not payload:
            logger.warning("WebSocket 认证失败: token 无效或已过期")
            return None

        user_info = {
            "user_id": payload["user_id"],
            "email": payload["email"]
        }
        
        # 提取locale参数
        locale = websocket.query_params.get("locale", "cn")
        user_info["locale"] = locale
        
        logger.info(f"WebSocket 认证通过: user_id={user_info['user_id']}, email={user_info['email']}, locale={locale}")
        return user_info

    except Exception as e:
        logger.error(f"WebSocket 认证异常: {e}", exc_info=True)
        return None


@router.websocket("/ws/status/{message_id}")
async def websocket_status(
    websocket: WebSocket,
    message_id: int,
    user_info: Optional[dict] = Depends(authenticate_websocket),
    task: Optional[ResearchChatProcessInfo] = Depends(validate_message_exists)
):
    """
    WebSocket 状态追踪接口

    实时推送任务执行状态，监听 research_chat_process_infos 表
    当 creation_status 为 'created' 或 'failed' 时自动断开连接

    依赖注入：
        - user_info: JWT 认证（失败返回 None）
        - task: 任务存在性验证（不存在返回 None）

    认证方式：
        Query 参数 ?token=xxx （浏览器 WebSocket 不支持自定义 header）

    错误处理：
        - 认证失败：返回 403 Forbidden (reason: "Authentication failed (403 equivalent)")
        - 任务不存在：返回 403 Forbidden (reason: "Task not found (404 equivalent)")

        ⚠️ 注意：由于 WebSocket 协议限制，握手失败时无法自定义 HTTP 状态码
        FastAPI/Starlette 在握手阶段调用 close() 会统一返回 403 Forbidden
        客户端应通过 WebSocket 关闭事件的 reason 字段区分具体错误类型

    性能优化：
        1. 任务不存在/认证失败时，在握手前拒绝（返回 WebSocket 关闭码 1003）
        2. 任务完成后立即断开，无需等待轮询间隔（延迟从 10 秒优化到毫秒级）
        3. 轮询间隔从 5 秒优化到 1 秒（可通过环境变量 WS_POLL_INTERVAL_SECONDS 配置）
        4. 关闭超时从 0.5 秒优化到 0.2 秒，增加耗时监控
    """
    # ==================== 入口验证（依赖注入已完成） ====================

    # 验证1: 用户认证（依赖注入：authenticate_websocket）
    if not user_info:
        # 注意：虽然是认证失败(403)，但由于 WebSocket 协议限制，实际返回的 HTTP 状态码也是 403
        # 客户端应通过 reason 字段识别具体错误类型
        logger.warning(f"拒绝连接 - 认证失败: message_id={message_id}")
        await websocket.close(code=1003, reason="Authentication failed (403 equivalent)")
        return

    # 验证2: 任务存在性（依赖注入：validate_message_exists）
    if not task:
        # 注意：虽然是任务不存在(404)，但由于 WebSocket 协议限制，实际返回的 HTTP 状态码是 403
        # 客户端应通过 reason 字段识别具体错误类型
        logger.warning(f"拒绝连接 - 任务不存在: message_id={message_id}, user_id={user_info['user_id']}")
        await websocket.close(code=1003, reason="Task not found (404 equivalent)")
        return

    # ==================== 建立连接 ====================

    await websocket.accept()
    logger.info(
        f"WebSocket 连接已建立: message_id={message_id}, "
        f"user_id={user_info['user_id']}, email={user_info['email']}"
    )

    try:
        # ==================== 轮询任务状态 ====================

        last_sent_status = None
        while True:
            try:
                with SessionLocal() as db:
                    stmt = select(ResearchChatProcessInfo).where(
                        ResearchChatProcessInfo.message_id == message_id
                    )
                    result = db.execute(stmt).scalar_one_or_none()
            except Exception as e:
                logger.error(f"数据库查询异常: message_id={message_id}, error={e}")
                result = None

            if result:
                # 准备状态数据
                status_data = {
                    "message_id": int(result.message_id),
                    "status": result.creation_status,
                    "logs": result.process_info.get("logs", []) if result.process_info else []
                }

                # 根据状态确定消息文本
                status_messages = {
                    CreationStatus.CREATED: "任务成功完成",
                    CreationStatus.FAILED: "任务失败",
                }
                message_text = status_messages.get(result.creation_status, "任务正在进行中")

                # 组装统一格式消息
                message_to_send = {
                    "code": 200, "message": message_text, "data": status_data
                }

                # 只在状态变化时发送
                if message_to_send != last_sent_status:
                    await websocket.send_json(message_to_send)
                    last_sent_status = message_to_send

                # 终止条件：任务完成或失败
                if result.creation_status in CreationStatus.FINISHED:
                    logger.info(f"任务已完成，准备关闭连接: message_id={message_id}, status={result.creation_status}")
                    # 优化点: 发送完成后立即跳出，不再等待sleep（从10秒优化到毫秒级）
                    break
            else:
                break

            # 使用配置的轮询间隔（从5秒优化到1秒，可通过环境变量调整）
            # 仅在任务未完成时才会执行到这里
            await asyncio.sleep(Config.WS_POLL_INTERVAL_SECONDS)

    except WebSocketDisconnect:
        logger.info(f"WebSocket客户端断开连接: message_id={message_id}")
    except Exception as e:
        logger.error(f"WebSocket错误: message_id={message_id}, error={e}")
        # 发生错误时尝试发送错误消息
        try:
            await websocket.send_json({
                "code": 500, "message": "WebSocket 通信发生内部错误", "data": {}
            })
        except:
            pass
    finally:
        # 优化关闭流程，快速释放资源
        try:
            if websocket.client_state.name != 'DISCONNECTED':
                # 使用更短的超时并记录关闭耗时
                start_time = time.time()

                # 使用较短的超时（0.2秒），避免阻塞
                await asyncio.wait_for(websocket.close(code=1000), timeout=0.2)

                elapsed = time.time() - start_time
                logger.info(f"WebSocket连接已关闭: message_id={message_id}, 耗时={elapsed:.3f}秒")
            else:
                logger.info(f"WebSocket连接已断开: message_id={message_id}")
        except asyncio.TimeoutError:
            logger.warning(f"WebSocket关闭超时，强制释放: message_id={message_id}")
        except Exception as e:
            logger.error(f"WebSocket关闭异常: message_id={message_id}, error={e}")
