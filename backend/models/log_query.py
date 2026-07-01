from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class LogQueryParams(BaseModel):
    """日志查询参数"""
    log_type: str  # api/master/subagent/operator/llm/error
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    page: int = 1
    page_size: int = 50


class LogEntry(BaseModel):
    """日志条目"""
    id: int
    timestamp: str
    module: str
    content: str
    details: Optional[dict] = None
    latency_ms: Optional[float] = None


class LogListResponse(BaseModel):
    """日志列表响应"""
    data: List[LogEntry]
    total: int


class SessionTraceResponse(BaseModel):
    """会话证据链响应"""
    session_id: str
    api_call: Optional[dict] = None
    master_decision: Optional[dict] = None
    subagent_executions: List[dict] = []
    operator_calls: List[dict] = []
    llm_calls: List[dict] = []
