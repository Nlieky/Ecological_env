from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, Float, Enum as SQLEnum
from sqlalchemy.sql import func
from backend.database.base import Base
import enum


class LogLevel(enum.Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class APICallLog(Base):
    """API 调用日志"""
    __tablename__ = 'api_call_logs'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=func.now(), index=True)
    method = Column(String(10))  # GET/POST/PUT/DELETE
    path = Column(String(255), index=True)  # /api/query
    user_id = Column(String(64), index=True)  # 用户ID
    request_params = Column(JSON)  # 请求参数
    response_status = Column(Integer)  # 200/400/500
    latency_ms = Column(Float)  # 耗时
    error_message = Column(Text, nullable=True)


class MasterAgentDecisionLog(Base):
    """主智能体决策日志"""
    __tablename__ = 'master_agent_decision_logs'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=func.now(), index=True)
    session_id = Column(String(64), index=True)  # 会话ID
    user_query = Column(Text)  # 用户查询
    intent = Column(String(64))  # 意图识别结果
    decision_path = Column(JSON)  # 决策路径
    subagents_called = Column(JSON)  # 调用的子智能体列表
    reasoning_summary = Column(Text)  # 推理摘要
    total_latency_ms = Column(Float)  # 总耗时


class SubAgentExecutionLog(Base):
    """子智能体执行日志"""
    __tablename__ = 'sub_agent_execution_logs'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=func.now(), index=True)
    session_id = Column(String(64), index=True)
    subagent_name = Column(String(64), index=True)  # 子智能体名称
    input_params = Column(JSON)  # 输入参数
    output_result = Column(JSON)  # 输出结果
    execution_time_ms = Column(Float)  # 执行耗时
    status = Column(String(20))  # success/failed
    error_message = Column(Text, nullable=True)


class OperatorCallLog(Base):
    """算子调用日志"""
    __tablename__ = 'operator_call_logs'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=func.now(), index=True)
    session_id = Column(String(64), index=True)
    subagent_name = Column(String(64))  # 调用该算子的子智能体
    operator_name = Column(String(128), index=True)  # 算子名称
    category = Column(String(32))  # statistical/ml/deep_learning
    input_params = Column(JSON)  # 输入参数
    output_result = Column(JSON)  # 输出结果
    execution_time_ms = Column(Float)
    status = Column(String(20))


class LLMCallLog(Base):
    """LLM 调用日志"""
    __tablename__ = 'llm_call_logs'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=func.now(), index=True)
    session_id = Column(String(64), index=True)
    provider = Column(String(64))  # ctgu-vlm
    model = Column(String(64))  # 具体模型名
    purpose = Column(String(32))  # intent_planning/response_formatting
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    total_tokens = Column(Integer)
    estimated_cost = Column(Float, nullable=True)  # 预估成本
    latency_ms = Column(Float)
    request_summary = Column(JSON)  # 简化的请求内容
    status = Column(String(20))


class SystemErrorLog(Base):
    """系统错误日志"""
    __tablename__ = 'system_error_logs'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=func.now(), index=True)
    level = Column(String(20), index=True)  # ERROR/CRITICAL/WARNING
    module = Column(String(64), index=True)  # backend/api/subagent_xxx
    error_type = Column(String(64))  # Exception类型
    error_message = Column(Text)
    stack_trace = Column(Text)
    context = Column(JSON)  # 额外上下文
