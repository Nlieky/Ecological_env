"""
查询接口 - 使用 AgentService 封装的智能体调用

重构后：通过 AgentService 调用自定义 AIAgent (shared/framework/hermes_agent)
不再依赖 HermesAPIClient 或 Hermes API Server
"""
import logging
import time
from fastapi import APIRouter, HTTPException
from backend.models.query import QueryRequest, QueryResponse
from backend.services.agent_service import AgentService
from backend.utils.loggers import generate_session_id, log_master_decision

logger = logging.getLogger(__name__)
router = APIRouter()


def parse_decision_path(content: str) -> list:
    """
    从响应内容解析决策路径

    Hermes 主智能体会根据决策树执行，
    我们可以通过分析响应内容推断走了哪些分支。
    """
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


@router.post("/query", tags=["查询"])
async def execute_query(request: QueryRequest):
    """
    执行自然语言查询 - 使用 AgentService

    **架构**：
    FastAPI → AgentService → AIAgent (shared/framework/hermes_agent)

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

    # 生成或使用提供的 session_id
    session_id = request.session_id or generate_session_id()

    try:
        logger.info(f"收到查询: {request.query[:50]}...")

        # 使用 AgentService 处理查询
        service = AgentService()
        query_response = service.process_query(
            query=request.query,
            session_id=session_id
        )

        # 解析决策路径（可选）
        decision_path = parse_decision_path(query_response.content)

        # 提取子智能体调用列表
        subagents_called = []
        for step in decision_path:
            if "action" in step and "调用" in step["action"]:
                agent_name = step["action"].replace("调用 ", "")
                subagents_called.append(agent_name)

        # 直接返回字典，避免 Pydantic 模型问题
        return {
            "content": query_response.content,
            "session_id": query_response.session_id,
            "timestamp": query_response.timestamp,
            "chartData": query_response.chartData,
            "decision_path": decision_path,
            "sub_agent_calls": [],
            "data_sources": [],
            "reasoning": query_response.reasoning,
            "metadata": query_response.metadata
        }

        # 计算耗时
        total_latency_ms = (time.time() - start_time) * 1000

        # 记录主智能体决策
        try:
            log_master_decision(
                session_id=session_id,
                user_query=request.query,
                intent="query",
                decision_path=[step.get("step_name", "") for step in decision_path],
                subagents_called=subagents_called,
                reasoning_summary=f"查询完成，返回 {len(query_response.content)} 字符",
                total_latency_ms=total_latency_ms
            )
        except Exception as log_error:
            logger.warning(f"Failed to log master decision: {log_error}")

        logger.info(f"查询完成: session={session_id}, 耗时={time.time() - start_time:.2f}s")

        return query_response

    except Exception as e:
        logger.error(f"查询失败: {str(e)}")
        import traceback
        traceback.print_exc()

        # 记录失败的决策
        try:
            total_latency_ms = (time.time() - start_time) * 1000
            log_master_decision(
                session_id=session_id,
                user_query=request.query,
                intent="error",
                decision_path=[],
                subagents_called=[],
                reasoning_summary=str(e),
                total_latency_ms=total_latency_ms
            )
        except Exception as log_error:
            logger.warning(f"Failed to log error: {log_error}")

        raise HTTPException(
            status_code=500,
            detail={
                "error": "QueryError",
                "message": "智能体调用失败",
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
        "implementation": {
            "method": "AgentService + Custom AIAgent",
            "description": "通过 AgentService 调用自定义 AIAgent (shared/framework/hermes_agent)",
            "identity_files_loaded": [
                "workspace/IDENTITY.md",
                "workspace/SOUL.md",
                "workspace/AGENTS.md",
                "workspace/MEMORY.md",
                "workspace/USER.md",
                "workspace/TOOLS.md",
                "workspace/HEARTBEAT.md"
            ]
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
