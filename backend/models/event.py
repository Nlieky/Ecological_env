"""事件 API schema（真数据源版）——对齐 alert_events 表与处置输出结构。"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AlertEvent(BaseModel):
    id: str
    timestamp: str
    sessionId: str = ""
    conversationId: Optional[str] = None
    plantId: str = ""
    violationTypes: List[str] = []
    severity: str
    action: str = ""
    confidence: Optional[float] = None
    evidence: List[Dict[str, Any]] = []
    workOrder: Optional[Dict[str, Any]] = None
    status: str
    createdAt: str = ""
    updatedAt: str = ""


class EventListResponse(BaseModel):
    data: List[AlertEvent]
    total: int


class EventStatusUpdate(BaseModel):
    status: str
