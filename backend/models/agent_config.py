# backend/models/agent_config.py
"""智能体运行参数表（配置中心可在线改的参数真相源之一）。
key/value 字符串存储，读取方经 agent_params.get_param 按类型转换。"""
from sqlalchemy import Column, String, Text, TIMESTAMP
from sqlalchemy.sql import func
from backend.database.base import Base


class AgentRuntimeParam(Base):
    __tablename__ = "agent_runtime_params"
    key = Column(String(64), primary_key=True)
    value = Column(Text, nullable=False, default="")
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())
