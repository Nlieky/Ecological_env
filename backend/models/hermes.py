"""
Hermes 系统模型
"""
from pydantic import BaseModel
from typing import List, Dict, Any


class SkillInfo(BaseModel):
    """技能信息（子智能体）"""
    name: str
    description: str
    location: str


class DecisionTreeNode(BaseModel):
    """决策树节点"""
    step: int
    question: str
    decision: str
    action: str


class HermesSystemInfo(BaseModel):
    """Hermes 系统信息"""
    name: str = "废水监测系统"
    version: str = "2.0.0"
    description: str = "基于 Hermes Agent 框架的废水监测智能体系统"

    # 主智能体
    master_agent: Dict[str, Any]

    # 决策树
    decision_tree: List[DecisionTreeNode]

    # 子智能体
    sub_agents: List[SkillInfo]

    # 三库一体
    shared_resources: Dict[str, str]
