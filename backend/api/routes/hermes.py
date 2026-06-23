"""
Hermes 系统信息接口
"""
from fastapi import APIRouter
from backend.models.hermes import HermesSystemInfo
from backend.core.config import settings
from backend.api.client import get_hermes_client

router = APIRouter()


@router.get("/hermes/system", response_model=HermesSystemInfo, tags=["Hermes"])
async def get_hermes_system_info():
    """
    获取 Hermes 系统完整信息

    Returns:
        Hermes 系统的结构、决策树、子智能体信息
    """
    return HermesSystemInfo(
        name="废水监测系统",
        version="2.0.0",
        description="基于 Hermes Agent 框架的废水监测智能体系统",
        master_agent={
            "name": "废水监测主智能体",
            "location": "workspace/SOUL.md",
            "role": "全局协调、智能决策、用户桥梁",
            "capabilities": [
                "意图识别",
                "决策树执行",
                "子智能体调度",
                "结果聚合"
            ]
        },
        decision_tree=[
            {
                "step": 1,
                "question": "需要数据吗？",
                "decision": "YES → data-perception, NO → 跳过"
            },
            {
                "step": 2,
                "question": "需要异常检测吗？",
                "decision": "YES → anomaly-detection, NO → 跳过"
            },
            {
                "step": 3,
                "question": "需要违规判定吗？",
                "decision": "YES → rule-reasoning, NO → 跳过"
            },
            {
                "step": 4,
                "question": "需要预警/工单吗？",
                "decision": "YES → disposition-execution, NO → 跳过"
            },
            {
                "step": 5,
                "question": "整合结果",
                "decision": "生成自然语言回答"
            }
        ],
        sub_agents=[
            {
                "name": "multi-dimensional-data-perception",
                "description": "多维数据感知",
                "location": "subagents/multi-dimensional-data-perception-agent/skills/"
            },
            {
                "name": "anomaly-detection",
                "description": "异常检测",
                "location": "subagents/anomaly-detection-agent/skills/"
            },
            {
                "name": "rule-reasoning",
                "description": "规则推理",
                "location": "subagents/rule-reasoning-agent/skills/"
            },
            {
                "name": "disposition-execution",
                "description": "研判处置",
                "location": "subagents/disposition-execution-agent/skills/"
            }
        ],
        shared_resources={
            "operators": "shared/operators/",
            "data": "shared/data/",
            "knowledge": "shared/knowledge/"
        }
    )


@router.get("/hermes/skills", tags=["Hermes"])
async def get_hermes_skills():
    """
    获取 Hermes 加载的技能列表（子智能体）

    Returns:
        Hermes API Server 加载的技能列表
    """
    try:
        client = get_hermes_client()
        skills = await client.list_skills()
        return {"skills": skills}
    except Exception as e:
        return {
            "error": str(e),
            "configured_skills": [
                "subagents/multi-dimensional-data-perception-agent/skills",
                "subagents/anomaly-detection-agent/skills",
                "subagents/rule-reasoning-agent/skills",
                "subagents/disposition-execution-agent/skills"
            ]
        }
