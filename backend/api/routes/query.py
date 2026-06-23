"""
查询接口 - Hermes 智能体核心接口

通过 Hermes API Server 调用主智能体，展示完整的决策过程
"""
import logging
import time
from fastapi import APIRouter, HTTPException
from backend.models.query import QueryRequest, QueryResponse
from backend.api.client import get_hermes_client

logger = logging.getLogger(__name__)
router = APIRouter()


def parse_decision_path(content: str) -> list:
    """
    从响应内容解析决策路径

    Hermes 主智能体会根据决策树执行，
    我们可以通过分析响应内容推断走了哪些分支。
    """
    # 示例：检测关键词推断决策路径
    # 实际实现可能需要 Hermes API 返回更详细的元数据
    path = []

    # 检测数据获取
    if any(keyword in content for keyword in ["数据", "指标", "进水", "出水", "pH", "COD"]):
        path.append({
            "step_number": 1,
            "step_name": "需要数据吗？",
            "decision": "YES",
            "action": "调用 multi-dimensional-data-perception"
        })
    else:
        path.append({
            "step_number": 1,
            "step_name": "需要数据吗？",
            "decision": "NO",
            "action": "跳过数据分析"
        })

    # 检测异常检测
    if any(keyword in content for keyword in ["异常", "突变", "检测"]):
        path.append({
            "step_number": 2,
            "step_name": "需要异常检测吗？",
            "decision": "YES",
            "action": "调用 anomaly-detection"
        })
        path.append({
            "step_number": 3,
            "step_name": "需要违规判定吗？",
            "decision": "NO",
            "action": "跳过"
        })
    else:
        path.append({
            "step_number": 2,
            "step_name": "需要异常检测吗？",
            "decision": "NO",
            "action": "跳过"
        })

    # 整合结果
    path.append({
        "step_number": 5,
        "step_name": "整合结果",
        "decision": "YES",
        "action": "生成自然语言回答"
    })

    return path


@router.post("/query", response_model=QueryResponse, tags=["查询"])
async def execute_query(request: QueryRequest):
    """
    执行自然语言查询 - 展示 Hermes 智能体的完整决策过程

    **Hermes 主智能体决策树**：
    1. 需要数据吗？ -> data-perception
    2. 需要异常检测吗？ -> anomaly-detection
    3. 需要违规判定吗？ -> rule-reasoning
    4. 需要预警/工单吗？ -> disposition-execution
    5. 整合结果

    **返回的响应包含**：
    - content: LLM 生成的最终回答
    - decision_path: 决策树的执行路径
    - sub_agent_calls: 子智能体调用链
    - data_sources: 数据溯源
    """
    start_time = time.time()

    try:
        logger.info(f"收到查询: {request.query[:50]}...")

        # 调用 Hermes API Server
        client = get_hermes_client()

        messages = [{"role": "user", "content": request.query}]
        hermes_response = await client.chat_completion(
            messages=messages,
            session_id=request.session_id
        )

        # 解析 Hermes 响应
        # OpenAI 兼容格式: response["choices"][0]["message"]["content"]
        content = hermes_response.get("choices", [{}])[0].get("message", {}).get("content", "")
        session_id = hermes_response.get("session_id", "unknown")

        # 解析决策路径
        decision_path = parse_decision_path(content)

        # 构建响应
        response = QueryResponse(
            content=content,
            session_id=session_id,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            decision_path=decision_path,
            sub_agent_calls=[],  # TODO: 从 Hermes 响应元数据提取
            data_sources=[],      # TODO: 从 Hermes 响应元数据提取
            reasoning={
                "intent": "通过分析内容推断",
                "model": hermes_response.get("model", "unknown")
            },
            metadata={
                "model": hermes_response.get("model", "unknown"),
                "usage": hermes_response.get("usage", {})
            }
        )

        logger.info(f"查询完成: session={session_id}, 耗时={time.time() - start_time:.2f}s")

        return response

    except Exception as e:
        logger.error(f"查询失败: {str(e)}")

        raise HTTPException(
            status_code=500,
            detail={
                "error": "HermesQueryError",
                "message": "Hermes API Server 调用失败",
                "detail": str(e)
            }
        )


@router.get("/query/capabilities", tags=["查询"])
async def get_hermes_capabilities():
    """
    获取 Hermes 智能体能力说明

    Returns:
        Hermes 智能体的完整决策树和能力描述
    """
    return {
        "master_agent": {
            "name": "废水监测主智能体",
            "role": "全局协调、智能决策、用户桥梁",
            "location": "workspace/SOUL.md"
        },
        "decision_tree": [
            {
                "step": 1,
                "question": "需要数据吗？",
                "condition": "提到'数据'、'指标'、'监测'、'进水'、'出水'",
                "yes_action": "调用 data-perception",
                "no_action": "跳过数据分析"
            },
            {
                "step": 2,
                "question": "需要异常检测吗？",
                "condition": "提到'异常'、'突变'、'是否正常'",
                "yes_action": "调用 anomaly-detection",
                "no_action": "跳过异常检测"
            },
            {
                "step": 3,
                "question": "需要违规判定吗？",
                "condition": "提到'违规'、'超标'、'违反标准'",
                "yes_action": "调用 rule-reasoning",
                "no_action": "跳过违规判定"
            },
            {
                "step": 4,
                "question": "需要预警/工单吗？",
                "condition": "提到'预警'、'工单'、'通知'",
                "yes_action": "调用 disposition-execution",
                "no_action": "跳过处置执行"
            },
            {
                "step": 5,
                "question": "整合结果",
                "action": "生成自然语言回答"
            }
        ],
        "sub_agents": [
            {
                "name": "multi-dimensional-data-perception",
                "role": "多维数据感知",
                "location": "subagents/multi-dimensional-data-perception-agent/skills/"
            },
            {
                "name": "anomaly-detection",
                "role": "异常检测",
                "location": "subagents/anomaly-detection-agent/skills/"
            },
            {
                "name": "rule-reasoning",
                "role": "规则推理",
                "location": "subagents/rule-reasoning-agent/skills/"
            },
            {
                "name": "disposition-execution",
                "role": "研判处置",
                "location": "subagents/disposition-execution-agent/skills/"
            }
        ],
        "examples": [
            {
                "query": "最近24小时出水COD异常吗？",
                "path": ["[1] YES -> data-perception", "[2] YES -> anomaly-detection", "[3] NO", "[4] NO", "[5] 整合"]
            },
            {
                "query": "最近24小时出水是否超标？",
                "path": ["[1] YES -> data-perception", "[2] YES -> anomaly-detection", "[3] YES -> rule-reasoning", "[4] NO", "[5] 整合"]
            },
            {
                "query": "生成今天的异常预警工单",
                "path": ["[1] YES -> data-perception", "[2] YES -> anomaly-detection", "[3] YES -> rule-reasoning", "[4] YES -> disposition-execution", "[5] 整合"]
            }
        ]
    }
