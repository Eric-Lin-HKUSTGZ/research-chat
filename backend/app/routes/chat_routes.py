"""
FastAPI Research Chat Routes
研究聊天路由模块 - FastAPI 实现
迁移自 Flask Blueprint
"""
from fastapi import APIRouter, Depends, Header, Request, Response, BackgroundTasks
from typing import Optional
from datetime import datetime
from ..utils.tools import UTC8
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import time
import logging
import os

from app.services.auth import get_current_user
from app.core.database import get_db, SessionLocal
from app.entity.research_chat import ResearchChatSession, ResearchChatMessage, ResearchChatProcessInfo
from app.utils.logger import get_logger
from app.utils.error_handler import ErrorCode, ErrorResponse, ErrorMessage
from app.services.llm_service import LLMClient, get_newest_paper, get_highly_cited_paper, get_relevence_paper, get_prompt, construct_paper
from app.constants.task_status import CreationStatus
from sqlalchemy import select

logger = get_logger('research_chat_fastapi')

# 创建 APIRouter
router = APIRouter(prefix="/digital_twin/research_chat/api", tags=["research_chat"])

def get_localized_message(key: str, locale: str = "cn") -> str:
    """根据locale返回对应语言的日志信息"""
    messages = {
        "task_start": {
            "cn": "🚀 研究任务启动！",
            "en": "🚀 Research task started!"
        },
        "step1_keywords": {
            "cn": "🔄 第一步：提取研究关键词...",
            "en": "🔄 Step 1: Extracting research keywords..."
        },
        "keywords_complete": {
            "cn": "✅ 关键词提取完成！",
            "en": "✅ Keywords extraction completed!"
        },
        "step2_papers": {
            "cn": "🔄 第二步：检索相关论文...",
            "en": "🔄 Step 2: Retrieving related papers..."
        },
        "papers_complete": {
            "cn": "✅ 论文检索完成！",
            "en": "✅ Paper retrieval completed!"
        },
        "step3_inspiration": {
            "cn": "🔄 第三步：生成研究灵感...",
            "en": "🔄 Step 3: Generating research inspiration..."
        },
        "inspiration_complete": {
            "cn": "✅ 研究灵感生成完成！",
            "en": "✅ Research inspiration generated!"
        },
        "step4_plan": {
            "cn": "🔄 第四步：生成初步研究计划...",
            "en": "🔄 Step 4: Generating preliminary research plan..."
        },
        "plan_complete": {
            "cn": "✅ 初步研究计划生成完成！",
            "en": "✅ Preliminary research plan generated!"
        },
        "step5_review": {
            "cn": "🔄 第五步：批判性审查...",
            "en": "🔄 Step 5: Critical review..."
        },
        "review_complete": {
            "cn": "✅ 批判性审查完成！",
            "en": "✅ Critical review completed!"
        },
        "step6_finalize": {
            "cn": "🔄 第六步：完善最终研究计划...",
            "en": "🔄 Step 6: Finalizing research plan..."
        },
        "finalize_complete": {
            "cn": "✅ 最终研究计划完善完成！",
            "en": "✅ Final research plan completed!"
        },
        "task_complete": {
            "cn": "🎉 研究任务完成！",
            "en": "🎉 Research task completed!"
        },
        "task_failed": {
            "cn": "❌ 研究任务失败",
            "en": "❌ Research task failed"
        },
        "llm_init_failed": {
            "cn": "LLM客户端初始化失败",
            "en": "LLM client initialization failed"
        },
        "keywords_failed": {
            "cn": "关键词提取失败",
            "en": "Keywords extraction failed"
        },
        "papers_failed": {
            "cn": "论文检索失败",
            "en": "Paper retrieval failed"
        },
        "inspiration_failed": {
            "cn": "研究灵感生成失败",
            "en": "Research inspiration generation failed"
        },
        "plan_failed": {
            "cn": "研究计划生成失败",
            "en": "Research plan generation failed"
        },
        "review_failed": {
            "cn": "批判性审查失败",
            "en": "Critical review failed"
        },
        "finalize_failed": {
            "cn": "研究计划完善失败",
            "en": "Research plan finalization failed"
        }
    }
    
    return messages.get(key, {}).get(locale, messages.get(key, {}).get("cn", key))


def format_log_with_timestamp(message: str) -> str:
    """为日志消息添加时间戳"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"[{timestamp}] {message}"


# ===== Pydantic 模型定义 =====

class CreateResearchRequest(BaseModel):
    content: str = Field(..., description="研究内容/问题")
    session_id: Optional[str] = Field(None, description="会话ID")
    locale: str = Field("cn", description="界面语言，cn=中文，en=英文")


class UpdateSessionNameRequest(BaseModel):
    session_name: str = Field(..., description="新的会话名称")


class StandardResponse(BaseModel):
    code: int = 200
    message: str = "Success"
    success: bool = True
    data: dict = {}


# ===== 辅助函数 =====

def generate_page_session_id(x_page_id: Optional[str] = None) -> str:
    """生成 page_session_id"""
    return x_page_id or f"page_{int(time.time() * 1000)}"


# ===== 路由处理器 =====

@router.get("/sessions")
async def get_sessions(
    page: Optional[int] = None,
    size: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取会话列表"""
    try:
        user_id = current_user["user_id"]

        # 构建查询
        query = select(ResearchChatSession).where(
            ResearchChatSession.user_id == user_id
        ).order_by(ResearchChatSession.updated_at.desc())

        # 始终保持分页查询
        page = int(page or 1)
        size = int(size or 20)
        size = max(1, min(size, 50))
        items = db.execute(query.offset((page - 1) * size).limit(size)).scalars().all()
        
        # 获取总数
        from sqlalchemy import func
        total = db.scalar(
            select(func.count(ResearchChatSession.id)).where(
                ResearchChatSession.user_id == user_id
            )
        )
        
        result = {
            "user_id": user_id,
            "chat_type": "research_chat",
            "sessions": [
                {
                    "id": s.id,
                    "session_id": s.page_session_id,
                    "session_name": s.session_name or "",
                    "is_active": s.is_active,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                }
                for s in items
            ],
            "pagination": {
                "page": page,
                "size": size,
                "total": total,
                "pages": (total + size - 1) // size if total is not None else 0
            }
        }
        return ErrorResponse.success_response("成功", result)

    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        return ErrorResponse.create_error_response(ErrorCode.INTERNAL_SERVER_ERROR, ErrorMessage.INTERNAL_SERVER_ERROR)


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取会话消息"""
    try:
        user_id = current_user["user_id"]
        latest = str(request.query_params.get('latest') or '').lower() in {'1', 'true', 'yes'}
        page_param = request.query_params.get('page')
        size_param = request.query_params.get('size')

        def _to_conversations(rows):
            convs = []
            for m, p in rows:
                convs.append({
                    "id": m.id,
                    "question": (m.content or ""),
                    "answer": (m.result_papers or None),
                    "process": {
                        "id": p.id if p else None,
                        "creation_status": p.creation_status if p else None,
                        "process_info": p.process_info if p else None,
                        "created_at": p.created_at.isoformat() if p and p.created_at else None,
                        "updated_at": p.updated_at.isoformat() if p and p.updated_at else None,
                    } if p else {},
                    "question_timestamp": m.created_at.isoformat() if m.created_at else None,
                    "answer_timestamp": m.updated_at.isoformat() if m.updated_at else None,
                })
            return convs

        # 验证会话权限
        session = db.scalar(
            select(ResearchChatSession).where(
                ResearchChatSession.page_session_id == session_id,
                ResearchChatSession.user_id == user_id
            )
        )

        if not session:
            return ErrorResponse.success_response("成功", [])

        # 构建复杂的查询逻辑，与lit_research.py保持一致
        from sqlalchemy import func
        from sqlalchemy.orm import aliased
        
        # 创建排名子查询
        ranked = select(
            ResearchChatProcessInfo.id.label('pid'),
            ResearchChatProcessInfo.message_id.label('mid'),
            func.row_number().over(
                partition_by=ResearchChatProcessInfo.message_id,
                order_by=ResearchChatProcessInfo.created_at.desc()
            ).label('rn')
        ).where(
            ResearchChatProcessInfo.user_id == user_id
        ).subquery()
        
        # 获取最新的进程信息
        latest_proc = select(ranked.c.pid, ranked.c.mid).where(ranked.c.rn == 1).subquery()
        
        # 创建进程信息别名
        P = aliased(ResearchChatProcessInfo)
        
        # 构建基础查询语句
        base_stmt = select(
            ResearchChatMessage,
            P
        ).select_from(ResearchChatMessage).outerjoin(
            latest_proc, latest_proc.c.mid == ResearchChatMessage.id
        ).outerjoin(
            P, P.id == latest_proc.c.pid
        ).where(
            ResearchChatMessage.session_id == session.id,
            ResearchChatMessage.user_id == user_id
        )

        if latest:
            row = db.execute(base_stmt.order_by(ResearchChatMessage.created_at.desc()).limit(1)).first()
            convs = _to_conversations([row]) if row else []
            return ErrorResponse.success_response("成功", convs)
        
        if page_param is None and size_param is None:
            rows = db.execute(base_stmt.order_by(ResearchChatMessage.created_at.asc())).all()
            convs = _to_conversations(rows)
            return ErrorResponse.success_response("成功", convs)
        
        # 分页查询
        page = int(page_param or 1)
        size = int(size_param or 20)
        size = max(1, min(size, 50))
        rows = db.execute(base_stmt.order_by(ResearchChatMessage.created_at.asc()).offset((page - 1) * size).limit(size)).all()
        
        # 获取总数
        total = db.scalar(
            select(func.count(ResearchChatMessage.id)).where(
                ResearchChatMessage.session_id == session.id,
                ResearchChatMessage.user_id == user_id
            )
        )
        
        result = {
            "content": _to_conversations(rows),
            "pagination": {
                "page": page,
                "size": size,
                "total": total,
                "pages": (total + size - 1) // size if total is not None else 0
            }
        }
        return ErrorResponse.success_response("成功", result)

    except Exception as e:
        logger.error(f"获取会话消息失败: {e}")
        return ErrorResponse.create_error_response(ErrorCode.INTERNAL_SERVER_ERROR, ErrorMessage.INTERNAL_SERVER_ERROR)


@router.put("/sessions/{session_id}/name")
async def update_session_name(
    session_id: str,
    request: UpdateSessionNameRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新会话名称"""
    try:
        user_id = current_user["user_id"]

        # 验证会话权限
        session = db.scalar(
            select(ResearchChatSession).where(
                ResearchChatSession.page_session_id == session_id,
                ResearchChatSession.user_id == user_id
            )
        )

        if not session:
            return ErrorResponse.create_error_response(ErrorCode.NOT_FOUND, "会话不存在")

        # 更新会话名称
        session.session_name = request.session_name
        db.commit()

        logger.info(f"会话名称已更新: {session_id} -> {request.session_name}")

        return ErrorResponse.success_response("会话名称更新成功")

    except Exception as e:
        logger.error(f"更新会话名称失败: {e}")
        db.rollback()
        return ErrorResponse.create_error_response(ErrorCode.INTERNAL_SERVER_ERROR, ErrorMessage.INTERNAL_SERVER_ERROR)


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除会话"""
    try:
        user_id = current_user["user_id"]

        # 验证会话权限
        session = db.scalar(
            select(ResearchChatSession).where(
                ResearchChatSession.page_session_id == session_id,
                ResearchChatSession.user_id == user_id
            )
        )

        if not session:
            return ErrorResponse.create_error_response(ErrorCode.NOT_FOUND, "会话不存在")

        # 删除会话（级联删除消息和进程信息）
        db.delete(session)
        db.commit()

        logger.info(f"会话已删除: {session_id}")

        return ErrorResponse.success_response("会话删除成功", {"session_id": session_id})

    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        db.rollback()
        return ErrorResponse.create_error_response(ErrorCode.INTERNAL_SERVER_ERROR, ErrorMessage.INTERNAL_SERVER_ERROR)


@router.post("/create")
async def create_research(
    request: CreateResearchRequest,
    response: Response,
    x_page_id: Optional[str] = Header(None),
    background_tasks: BackgroundTasks = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    创建研究请求（异步解耦）
    - 检查当前会话是否有正在处理中的任务（避免同一会话多个WebSocket连接）
    - 立即写入 messages 和 process_infos
    - 启动后台任务处理 prompt/LLM 并更新数据库
    - 立即返回 message_id 和 session_id，前端据此建立 WebSocket
    """
    try:
        user_id = current_user["user_id"]
        user_email = current_user["email"]
        content = request.content
        session_id = request.session_id
        locale = request.locale  # 提取locale参数

        # 获取或创建会话
        if session_id:
            session = db.scalar(
                select(ResearchChatSession).where(
                    ResearchChatSession.page_session_id == session_id,
                    ResearchChatSession.user_id == user_id
                )
            )
        else:
            session = None

        if not session:
            # 创建新会话
            new_session_id = generate_page_session_id(x_page_id)
            session_name = content[:30] + '...' if len(content) > 30 else content
            session = ResearchChatSession(
                page_session_id=new_session_id,
                user_id=user_id,
                email=user_email,
                session_name=session_name,
                is_active=True
            )
            db.add(session)
            db.flush()

        # 检查当前会话是否有正在处理中的任务
        # creation_status 为 'pending' 或 'creating' 时表示任务正在处理中
        in_progress_task = db.scalar(
            select(ResearchChatProcessInfo).where(
                ResearchChatProcessInfo.session_id == session.id,
                ResearchChatProcessInfo.user_id == user_id,
                ResearchChatProcessInfo.creation_status.in_(CreationStatus.IN_PROGRESS)
            )
        )

        if in_progress_task:
            logger.warning(f"会话 {session.page_session_id} 已有正在处理中的任务 (message_id={in_progress_task.message_id})，拒绝创建新消息")
            # 设置 HTTP 状态码为 409，同时保持 ErrorResponse 格式
            response.status_code = ErrorCode.CONFLICT.value
            return ErrorResponse.create_error_response(
                ErrorCode.CONFLICT,
                f"当前会话已有正在处理中的任务，请等待任务完成后再提交新的研究请求"
            )

        # 创建消息记录
        message = ResearchChatMessage(
            session_id=session.id,
            user_id=user_id,
            email=user_email,
            content=content
        )
        db.add(message)
        db.flush()

        # 创建进程记录（初始为 creating）
        process = ResearchChatProcessInfo(
            session_id=session.id,
            message_id=message.id,
            user_id=user_id,
            email=user_email,
            creation_status=CreationStatus.CREATING,
            process_info={"logs": [format_log_with_timestamp("🚀 开始处理研究请求")]}
        )
        db.add(process)
        db.commit()

        logger.info(f"研究请求已创建(异步): message_id={message.id}, session={session.page_session_id}")

        # 启动后台任务（异步处理 LLM & 更新DB）
        if background_tasks is not None:
            background_tasks.add_task(_background_process_prompt_and_update,
                                      message.id, session.id, user_id, user_email, content, locale)

        # 立即返回（前端拿到 message_id 后再连接 WS）
        return ErrorResponse.success_response("研究消息已成功创建", {
            "message_id": message.id,
            "session_id": session.page_session_id
        })

    except Exception as e:
        logger.error(f"创建研究请求失败: {e}")
        db.rollback()
        return ErrorResponse.create_error_response(ErrorCode.INTERNAL_SERVER_ERROR, ErrorMessage.INTERNAL_SERVER_ERROR)


def _background_process_prompt_and_update(message_id: int, session_db_id: int, user_id: int, user_email: str, content: str, locale: str = "cn"):
    """
    后台任务：结合 prompt 调用模型并异步更新数据库
    - 仿照deepresearch的run_research_async函数模式
    - 追加进度日志到 ResearchChatProcessInfo.process_info.logs
    - 调用keyu-ideation的6步研究计划生成流程
    - 更新 ResearchChatMessage.result_papers 与进程状态
    """
    # 定义任务超时时间 (1小时 = 3600秒)
    TASK_TIMEOUT_SECONDS = 3600.0
    
    db = SessionLocal()
    
    # Create task-specific logger (following deepresearch pattern)
    task_logger = logging.getLogger(f"research_task.msg_{message_id}")
    task_logger.setLevel(logging.INFO)
    if task_logger.hasHandlers():
        task_logger.handlers.clear()

    formatter = logging.Formatter(
        f'[%(asctime)s] [%(levelname)s] [msg:{message_id}] %(message)s',
        '%Y-%m-%d %H:%M:%S'
    )

    # File handler
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"message_{message_id}_task.log")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    task_logger.addHandler(file_handler)

    # Stream handler
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    task_logger.addHandler(stream_handler)
    
    # 核心业务逻辑函数
    def _execute_research():
        # 用户状态日志 (db_log) 的设置 - 仿照deepresearch模式
        logs = []
        
        def db_log(msg: str, stage: str = CreationStatus.CREATING):
            nonlocal logs
            log_entry = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
            logs.append(log_entry)
            print(log_entry)  # 保留简单的控制台输出

            # 直接更新数据库 - 仿照deepresearch的数据库更新模式
            try:
                proc = db.scalar(
                    select(ResearchChatProcessInfo).where(ResearchChatProcessInfo.message_id == message_id)
                )
                if proc:
                    proc.process_info = {"logs": logs}
                    proc.creation_status = stage
                    proc.updated_at = datetime.now()
                    db.commit()
            except Exception as e:
                task_logger.error(f"Failed to update process info: {e}")
                db.rollback()

        try:
            db_log(get_localized_message("task_start", locale))
            task_logger.info(f"Research task started. Topic: '{content}'")
            
            # 初始化LLM客户端
            try:
                client = LLMClient(provider="custom")
                task_logger.info("LLM client initialized successfully")
            except Exception as e:
                raise Exception(get_localized_message("llm_init_failed", locale) + f": {e}")

            # === Step 1: Extract Keywords ===
            db_log(get_localized_message("step1_keywords", locale))
            task_logger.info("Step 1: Extracting keywords from query")
            try:
                prompt = get_prompt("retrieve_query", locale=locale, user_query=content)
                response = client.get_response(prompt=prompt)
                task_logger.info(f"Keywords extracted: {response}")
                
                query_list = [kw.strip() for kw in response.split(",")]
                if len(query_list) == 1:
                    query = query_list[0]
                else:
                    query = " | ".join(f'"{item}"' for item in query_list)
                
                db_log(get_localized_message("keywords_complete", locale))
                task_logger.info(f"Constructed query: {query}")
            except Exception as e:
                raise Exception(get_localized_message("keywords_failed", locale) + f": {e}")

            # === Step 2: Retrieve Papers ===
            db_log(get_localized_message("step2_papers", locale))
            task_logger.info("Step 2: Retrieving related papers")
            try:
                newest_paper = get_newest_paper(query)
                highly_cited_paper = get_highly_cited_paper(query)
                relevence_paper = get_relevence_paper(query)
                paper = construct_paper(newest_paper, highly_cited_paper, relevence_paper)
                
                task_logger.info(f"Papers retrieved: {len(newest_paper)} newest, {len(highly_cited_paper)} highly cited, {len(relevence_paper)} relevant")
                db_log(get_localized_message("papers_complete", locale))
            except Exception as e:
                raise Exception(get_localized_message("papers_failed", locale) + f": {e}")

            # === Step 3: Generate Inspiration ===
            db_log(get_localized_message("step3_inspiration", locale))
            task_logger.info("Step 3: Generating inspiration from papers")
            try:
                prompt = get_prompt("get_inspiration", locale=locale, user_query=content, paper=paper)
                inspiration = client.get_response(prompt=prompt)
                task_logger.info(f"Inspiration generated (length: {len(inspiration)} chars)")
                db_log(get_localized_message("inspiration_complete", locale))
            except Exception as e:
                raise Exception(get_localized_message("inspiration_failed", locale) + f": {e}")

            # === Step 4: Generate Preliminary Plan ===
            db_log(get_localized_message("step4_plan", locale))
            task_logger.info("Step 4: Generating preliminary research plan")
            try:
                prompt = get_prompt("generate_research_plan", locale=locale, user_query=content, paper=paper, inspiration=inspiration)
                research_plan = client.get_response(prompt=prompt)
                task_logger.info(f"Preliminary plan generated (length: {len(research_plan)} chars)")
                db_log(get_localized_message("plan_complete", locale))
            except Exception as e:
                raise Exception(get_localized_message("plan_failed", locale) + f": {e}")

            # === Step 5: Critical Review ===
            db_log(get_localized_message("step5_review", locale))
            task_logger.info("Step 5: Conducting critical review")
            try:
                prompt = get_prompt("critic_research_plan", locale=locale, user_query=content, paper=paper, inspiration=inspiration, research_plan=research_plan)
                criticism = client.get_response(prompt=prompt)
                task_logger.info(f"Critical review completed (length: {len(criticism)} chars)")
                db_log(get_localized_message("review_complete", locale))
            except Exception as e:
                raise Exception(get_localized_message("review_failed", locale) + f": {e}")

            # === Step 6: Refine Plan ===
            db_log(get_localized_message("step6_finalize", locale))
            task_logger.info("Step 6: Refining research plan based on criticism")
            try:
                prompt = get_prompt("refine_research_plan", locale=locale, user_query=content, research_plan=research_plan, criticism=criticism)
                final_research_plan = client.get_response(prompt=prompt)
                task_logger.info(f"Final plan generated (length: {len(final_research_plan)} chars)")
                db_log(get_localized_message("finalize_complete", locale))
            except Exception as e:
                raise Exception(get_localized_message("finalize_failed", locale) + f": {e}")

            # === Update Message with Final Result ===
            db_log("🔄 保存最终研究计划...")
            task_logger.info("Saving final research plan to database")
            try:
                msg = db.scalar(select(ResearchChatMessage).where(ResearchChatMessage.id == message_id))
                if msg:
                    result_data_to_save = {
                        "response": final_research_plan,
            "generated_at": datetime.now().isoformat(),
                        "mode": "background-llm",
                        "intermediate_results": {
                            "keywords": response,
                            "query": query,
                            "papers_count": {
                                "newest": len(newest_paper),
                                "highly_cited": len(highly_cited_paper),
                                "relevant": len(relevence_paper)
                            },
                            "inspiration": inspiration,
                            "preliminary_plan": research_plan,
                            "criticism": criticism
                        }
                    }
                    msg.result_papers = result_data_to_save
                    msg.updated_at = datetime.now()
                    msg.extra_info = {"generation_complete": True}
                    db.commit()
                    task_logger.info("Final research plan saved to database successfully")
            except Exception as e:
                raise Exception(f"保存最终研究计划失败: {e}")

            db_log(get_localized_message("task_complete", locale), stage=CreationStatus.CREATED)
            task_logger.info("===== TASK COMPLETED SUCCESSFULLY =====")

        except Exception as e:
            # 对用户，只记录简洁的错误信息
            error_message_for_user = get_localized_message("task_failed", locale) + f": {str(e)}"
            db_log(error_message_for_user, stage=CreationStatus.FAILED)
            
            # 对开发者，使用 exception 记录完整的堆栈跟踪到日志文件
            task_logger.exception("A critical error caused the research task to fail. See traceback below.")
            task_logger.error("===== TASK FAILED =====")

    # 主要执行逻辑 - 仿照deepresearch的超时处理
    try:
        task_logger.info(f"Task starting with a timeout of {TASK_TIMEOUT_SECONDS} seconds.")
        
        # 使用threading.Timer来模拟超时处理（因为这是同步函数）
        import threading
        import signal
        
        def timeout_handler():
            raise TimeoutError(f"Task timed out after {TASK_TIMEOUT_SECONDS} seconds")
        
        # 设置超时定时器
        timer = threading.Timer(TASK_TIMEOUT_SECONDS, timeout_handler)
        timer.start()
        
        try:
            _execute_research()
        finally:
            timer.cancel()
            
    except TimeoutError as e:
        # 超时处理 - 仿照deepresearch的超时处理模式
        timeout_message = "❌ 任务执行失败: 运行超过1小时，已自动超时。"
        task_logger.error(f"Task timed out after {TASK_TIMEOUT_SECONDS} seconds. Marking as failed.")
        
        # 直接更新数据库状态为 failed
        try:
            proc = db.scalar(
                select(ResearchChatProcessInfo).where(ResearchChatProcessInfo.message_id == message_id)
            )
            if proc and proc.process_info and 'logs' in proc.process_info:
                logs_on_timeout = proc.process_info['logs']
            else:
                logs_on_timeout = []
            
            log_entry = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {timeout_message}"
            logs_on_timeout.append(log_entry)
            
            proc.process_info = {"logs": logs_on_timeout}
            proc.creation_status = CreationStatus.FAILED
            proc.updated_at = datetime.now()
            db.commit()
            
            task_logger.error("===== TASK FAILED DUE TO TIMEOUT =====")
        except Exception as e:
            task_logger.error(f"Failed to update timeout status: {e}")
            db.rollback()
        
    finally:
        # 任务结束时 (无论成功、失败还是超时)，都关闭并移除handler
        for handler in task_logger.handlers[:]:
            handler.close()
            task_logger.removeHandler(handler)
        db.close()

@router.get("/health")
async def health_check():
    """健康检查端点"""
    return ErrorResponse.success_response("健康检查通过", {
        "status": "healthy",
        "timestamp": datetime.now(UTC8).isoformat()
    })
