# backend/models/agent_config.py
"""智能体运行参数表（配置中心可在线改的参数真相源之一）。
key/value 字符串存储，读取方经 agent_params.get_param 按类型转换。"""
from sqlalchemy import Boolean, Column, String, Text, TIMESTAMP
from sqlalchemy.sql import func
from backend.database.base import Base


class AgentRuntimeParam(Base):
    __tablename__ = "agent_runtime_params"
    key = Column(String(64), primary_key=True)
    value = Column(Text, nullable=False, default="")
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())


class AgentStrategy(Base):
    """智能体执行策略（编排/守卫/风格/动作通道/默认供应商）。key/value 字符串存储，
    读取方经 agent_strategy.get_strategy 按类型转换；无行=用内置默认。"""
    __tablename__ = "agent_strategy"
    key = Column(String(64), primary_key=True)
    value = Column(Text, nullable=False, default="")
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())


class LLMProvider(Base):
    """外部 LLM 供应商配置。default_llm_provider 策略引用 name（仅 tested_ok 可设）。"""
    __tablename__ = "llm_providers"
    name = Column(String(64), primary_key=True)
    base_url = Column(String(256), nullable=False, default="")
    api_key = Column(Text, nullable=False, default="")
    model = Column(String(128), nullable=False, default="")
    enabled = Column(Boolean, nullable=False, default=True)
    tested_ok = Column(Boolean, nullable=False, default=False)
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())
