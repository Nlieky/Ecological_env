from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from backend.database.session import get_db
from backend.models.logging import (
    APICallLog,
    MasterAgentDecisionLog,
    SubAgentExecutionLog,
    OperatorCallLog,
    LLMCallLog,
    SystemErrorLog
)
from backend.models.log_query import LogQueryParams, LogListResponse, LogEntry, SessionTraceResponse
import json

router = APIRouter()


@router.get("/logs", response_model=LogListResponse)
async def query_logs(
    log_type: str = Query(..., pattern="^(api|master|subagent|operator|llm|error)$"),
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """统一日志查询接口"""

    # 选择表
    table_map = {
        "api": APICallLog,
        "master": MasterAgentDecisionLog,
        "subagent": SubAgentExecutionLog,
        "operator": OperatorCallLog,
        "llm": LLMCallLog,
        "error": SystemErrorLog
    }
    model = table_map[log_type]

    # 构建查询
    query = db.query(model)

    # 时间过滤
    if start_time:
        query = query.filter(model.timestamp >= datetime.fromisoformat(start_time))
    if end_time:
        query = query.filter(model.timestamp <= datetime.fromisoformat(end_time))

    # 获取总数
    total = query.count()

    # 分页
    offset = (page - 1) * page_size
    logs = query.order_by(model.timestamp.desc()).offset(offset).limit(page_size).all()

    # 转换为响应格式
    data = []
    for log in logs:
        entry = LogEntry(
            id=log.id,
            timestamp=log.timestamp.isoformat(),
            module=log_type,
            content=str(log),
            details=None,
            latency_ms=getattr(log, 'latency_ms', None) or getattr(log, 'execution_time_ms', None)
        )
        data.append(entry)

    return LogListResponse(data=data, total=total)


@router.get("/logs/trace/{session_id}", response_model=SessionTraceResponse)
async def get_session_trace(session_id: str, db: Session = Depends(get_db)):
    """获取完整会话的证据链"""

    # 查询主智能体决策
    master_log = db.query(MasterAgentDecisionLog).filter(
        MasterAgentDecisionLog.session_id == session_id
    ).first()

    # 查询子智能体执行
    subagent_logs = db.query(SubAgentExecutionLog).filter(
        SubAgentExecutionLog.session_id == session_id
    ).all()

    # 查询算子调用
    operator_logs = db.query(OperatorCallLog).filter(
        OperatorCallLog.session_id == session_id
    ).all()

    # 查询 LLM 调用
    llm_logs = db.query(LLMCallLog).filter(
        LLMCallLog.session_id == session_id
    ).all()

    return SessionTraceResponse(
        session_id=session_id,
        api_call=None,
        master_decision={c.name: getattr(master_log, c.name) for c in master_log.__table__.columns} if master_log else None,
        subagent_executions=[{c.name: getattr(log, c.name) for c in log.__table__.columns} for log in subagent_logs],
        operator_calls=[{c.name: getattr(log, c.name) for c in log.__table__.columns} for log in operator_logs],
        llm_calls=[{c.name: getattr(log, c.name) for c in log.__table__.columns} for log in llm_logs]
    )


@router.get("/logs/export")
async def export_logs(
    log_type: str = Query(..., pattern="^(api|master|subagent|operator|llm|error)$"),
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    format: str = Query("json", pattern="^(json|xlsx)$"),
    db: Session = Depends(get_db)
):
    """导出日志"""
    # TODO: 实现导出功能
    from fastapi.responses import Response
    return Response(content="Export feature coming soon", media_type="text/plain")
