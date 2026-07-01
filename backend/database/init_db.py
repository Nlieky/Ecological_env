"""
初始化日志数据库
运行此脚本创建所有日志表
"""
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from backend.database.base import engine, Base
from backend.models.logging import (
    APICallLog,
    MasterAgentDecisionLog,
    SubAgentExecutionLog,
    OperatorCallLog,
    LLMCallLog,
    SystemErrorLog
)


def init_db():
    """创建所有日志表"""
    print("正在初始化日志数据库...")

    # 创建所有表
    Base.metadata.create_all(bind=engine)

    print(f"[OK] 日志数据库初始化完成: {engine.url}")
    print("已创建以下表:")
    print("  - api_call_logs")
    print("  - master_agent_decision_logs")
    print("  - sub_agent_execution_logs")
    print("  - operator_call_logs")
    print("  - llm_call_logs")
    print("  - system_error_logs")


if __name__ == "__main__":
    init_db()
