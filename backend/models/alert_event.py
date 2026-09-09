"""预警事件表——处置子智能体研判结果的采集落地（事件中心/告警中心真数据源）。"""
import enum
from datetime import datetime
from sqlalchemy import Column, String, TIMESTAMP, Float, JSON, Enum as SQLEnum

from backend.database.base import Base


class EventSeverity(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class EventStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    resolved = "resolved"
    ignored = "ignored"


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id = Column(String(50), primary_key=True)                # evt_<uuid12>
    timestamp = Column(TIMESTAMP, nullable=False)            # 研判完成时刻
    session_id = Column(String(64), unique=True, index=True) # 溯源+幂等键
    conversation_id = Column(String(50), nullable=True)
    plant_id = Column(String(100), nullable=False, default="unknown")
    violation_types = Column(JSON, default=list)             # ["插瓶干扰", ...]
    severity = Column(SQLEnum(EventSeverity), nullable=False)
    action = Column(String(100), default="")
    confidence = Column(Float, nullable=True)
    evidence = Column(JSON, default=list)                    # evidence_points 原文
    work_order = Column(JSON, nullable=True)
    status = Column(SQLEnum(EventStatus), default=EventStatus.pending, nullable=False)
    # 列级 default/onupdate：Task2 的状态更新(PUT status)只改 status 字段即可，updated_at 自动维护
    created_at = Column(TIMESTAMP, default=datetime.now, nullable=False)
    updated_at = Column(TIMESTAMP, default=datetime.now, onupdate=datetime.now, nullable=False)
