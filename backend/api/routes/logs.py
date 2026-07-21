from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from typing import Optional, List, Any
from datetime import datetime
import enum
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


def _safe(v: Any) -> Any:
    """把 SQLAlchemy 列值转成 JSON 可序列化的标量。"""
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, enum.Enum):
        return v.value
    return v


def _details(log: Any) -> dict:
    """日志行的全字段字典（JSON 安全）。"""
    return {c.name: _safe(getattr(log, c.name)) for c in log.__table__.columns}


def _summary(log_type: str, log: Any) -> str:
    """按日志类型生成可读摘要（替代旧的 str(log) 内存地址）。"""
    try:
        if log_type == 'api':
            return f"{log.method} {log.path} → {log.response_status} ({(log.latency_ms or 0):.0f}ms)"
        if log_type == 'master':
            q = (log.user_query or '').replace('\n', ' ').strip()[:60]
            return f"意图={log.intent or '—'} | {q}"
        if log_type == 'subagent':
            return f"{log.subagent_name}: {log.status}"
        if log_type == 'operator':
            return f"{log.operator_name} ({log.category}): {log.status}"
        if log_type == 'llm':
            return f"{log.provider}/{log.model} · {log.purpose} · {log.total_tokens or 0} tokens"
        if log_type == 'error':
            return f"[{log.level}] {log.error_type}: {(log.error_message or '')[:80]}"
    except Exception:
        pass
    return f"{log_type}#{getattr(log, 'id', '?')}"



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
            content=_summary(log_type, log),
            details=_details(log),
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
