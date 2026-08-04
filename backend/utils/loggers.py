"""
日志记录工具函数
用于在系统中各个位置记录结构化日志
"""
import time
import uuid
import traceback
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from backend.database.session import SessionLocal
from backend.models.logging import (
    APICallLog,
    MasterAgentDecisionLog,
    SubAgentExecutionLog,
    OperatorCallLog,
    LLMCallLog,
    SystemErrorLog
)


def log_api_call(
    method: str,
    path: str,
    user_id: str,
    request_params: Dict,
    response_status: int,
    latency_ms: float,
    error_message: Optional[str] = None
):
    """记录 API 调用"""
    db = SessionLocal()
    try:
        log = APICallLog(
            method=method,
            path=path,
            user_id=user_id,
            request_params=request_params,
            response_status=response_status,
            latency_ms=latency_ms,
            error_message=error_message
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to log API call: {e}")
    finally:
        db.close()


def log_master_decision(
    session_id: str,
    user_query: str,
    intent: str,
    decision_path: List[str],
    subagents_called: List[str],
    reasoning_summary: str,
    total_latency_ms: float,
    turn_id: Optional[str] = None
):
    """记录主智能体决策"""
    db = SessionLocal()
    try:
        log = MasterAgentDecisionLog(
            session_id=session_id,
            turn_id=turn_id,
            user_query=user_query,
            intent=intent,
            decision_path=decision_path,
            subagents_called=subagents_called,
            reasoning_summary=reasoning_summary,
            total_latency_ms=total_latency_ms
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to log master decision: {e}")
    finally:
        db.close()


def log_subagent_execution(
    session_id: str,
    subagent_name: str,
    input_params: Dict,
    output_result: Dict,
    execution_time_ms: float,
    status: str,
    error_message: Optional[str] = None,
    turn_id: Optional[str] = None
):
    """记录子智能体执行"""
    db = SessionLocal()
    try:
        log = SubAgentExecutionLog(
            session_id=session_id,
            turn_id=turn_id,
            subagent_name=subagent_name,
            input_params=input_params,
            output_result=output_result,
            execution_time_ms=execution_time_ms,
            status=status,
            error_message=error_message
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to log subagent execution: {e}")
    finally:
        db.close()


def log_operator_call(
    session_id: str,
    subagent_name: str,
    operator_name: str,
    category: str,
    input_params: Dict,
    output_result: Dict,
    execution_time_ms: float,
    status: str
):
    """记录算子调用"""
    db = SessionLocal()
    try:
        log = OperatorCallLog(
            session_id=session_id,
            subagent_name=subagent_name,
            operator_name=operator_name,
            category=category,
            input_params=input_params,
            output_result=output_result,
            execution_time_ms=execution_time_ms,
            status=status
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to log operator call: {e}")
    finally:
        db.close()


def log_llm_call(
    session_id: str,
    provider: str,
    model: str,
    purpose: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    estimated_cost: Optional[float],
    latency_ms: float,
    request_summary: Dict,
    status: str
):
    """记录 LLM 调用"""
    db = SessionLocal()
    try:
        log = LLMCallLog(
            session_id=session_id,
            provider=provider,
            model=model,
            purpose=purpose,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost=estimated_cost,
            latency_ms=latency_ms,
            request_summary=request_summary,
            status=status
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to log LLM call: {e}")
    finally:
        db.close()


def log_system_error(
    level: str,
    module: str,
    error_type: str,
    error_message: str,
    stack_trace: str,
    context: Optional[Dict] = None
):
    """记录系统错误"""
    db = SessionLocal()
    try:
        log = SystemErrorLog(
            level=level,
            module=module,
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            context=context or {}
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to log system error: {e}")
    finally:
        db.close()


def generate_session_id() -> str:
    """生成唯一会话 ID"""
    return str(uuid.uuid4())
