"""
查询接口数据模型 - 展示 Hermes 决策树和调用链
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class DecisionPath(BaseModel):
    """决策路径（主智能体决策树的分支）"""
    step_number: int = Field(..., description="步骤编号")
    step_name: str = Field(..., description="步骤名称")
    decision: str = Field(..., description="决策结果（YES/NO）")
    action: str = Field(..., description="执行的操作")


class SubAgentCall(BaseModel):
    """子智能体调用信息"""
    agent_name: str = Field(..., description="子智能体名称")
    agent_role: str = Field(..., description="子智能体角色")
    call_time: float = Field(..., description="调用耗时（秒）")
    result_summary: str = Field(..., description="结果摘要")
    status: str = Field(..., description="调用状态")


class DataSource(BaseModel):
    """数据溯源信息"""
    source: str = Field(..., description="数据来源")
    time_range: str = Field(..., description="时间范围")
    records_count: int = Field(..., description="记录数量")


class QueryRequest(BaseModel):
    """查询请求"""
    query: str = Field(..., description="用户查询内容", min_length=1)
    session_id: Optional[str] = Field(None, description="会话ID")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "最近24小时出水COD异常吗？",
                "session_id": None
            }
        }


class QueryResponse(BaseModel):
    """查询响应 - 完整展示 Hermes 决策过程"""

    # 基础信息
    content: str = Field(..., description="LLM 生成的最终回答")
    session_id: str = Field(..., description="会话ID")
    timestamp: str = Field(..., description="响应时间戳")

    # 决策树路径（展示主智能体走了哪些分支）
    decision_path: List[DecisionPath] = Field(
        default_factory=list,
        description="主智能体决策树的执行路径"
    )

    # 子智能体调用链
    sub_agent_calls: List[SubAgentCall] = Field(
        default_factory=list,
        description="本次查询调用的子智能体列表"
    )

    # 数据溯源
    data_sources: List[DataSource] = Field(
        default_factory=list,
        description="本次查询使用的数据来源"
    )

    # LLM 推理过程
    reasoning: Optional[Dict[str, Any]] = Field(None, description="LLM 推理过程")

    # 元数据
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="其他元数据"
    )
