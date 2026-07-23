"""
查询接口 - 转发到独立的Agent服务

重构后：通过HTTP请求转发到Agent服务(localhost:8642)
不再直接创建AIAgent实例，Agent服务独立运行
"""
import logging
import time
import requests
from fastapi import APIRouter, HTTPException
from backend.models.query import QueryRequest, QueryResponse
from backend.utils.loggers import generate_session_id, log_master_decision
from backend.core.config import settings
from backend.services.conversation_service import ConversationService

logger = logging.getLogger(__name__)
router = APIRouter()

# Agent服务配置（从settings读取）
AGENT_SERVICE_URL = settings.AGENT_SERVICE_URL
AGENT_TIMEOUT = settings.AGENT_TIMEOUT

# 对话历史服务：把 /api/query 的真实问答落入 conversations 表
conversation_service = ConversationService()


def check_agent_service() -> bool:
    """检查Agent服务是否可用"""
    try:
        response = requests.get(f"{AGENT_SERVICE_URL}/health", timeout=5)
        return response.status_code == 200
    except Exception as e:
        logger.warning(f"Agent服务不可用: {e}")
        return False


@router.post("/query", tags=["查询"])
def execute_query(request: QueryRequest):
    """
    执行自然语言查询 - 转发到Agent服务

    **架构**：
    FastAPI → HTTP转发 → Agent服务(localhost:8642) → AIAgent(主智能体)

    说明：用 sync def（而非 async def）。内部 requests.post 转发是阻塞的（完整
    pipeline ~30-60s）。async def 直接调会冻住后端事件循环，导致 /api/health、
    /metrics、/api/logs 等全部卡住。sync def 由 FastAPI 自动丢进线程池，事件循环畅通。

    **Agent服务处理**：
    1. 主智能体通过LLM理解意图
    2. 根据需要调用子智能体（通过orchestrator-core工具）
    3. 整合结果并返回
    """
    start_time = time.time()

    # 生成或使用提供的 session_id
    session_id = request.session_id or generate_session_id()

    try:
        logger.info(f"收到查询: {request.query[:50]}...")

        # 检查Agent服务是否可用
        if not check_agent_service():
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "ServiceUnavailable",
                    "message": "Agent服务不可用，请确保Agent服务已启动"
                }
            )

        # 转发请求到Agent服务
        agent_response = requests.post(
            f"{AGENT_SERVICE_URL}/query",
            json={
                "query": request.query,
                "session_id": session_id
            },
            timeout=AGENT_TIMEOUT
        )

        if agent_response.status_code != 200:
            raise HTTPException(
                status_code=agent_response.status_code,
                detail={
                    "error": "AgentError",
                    "message": f"Agent服务返回错误: {agent_response.status_code}"
                }
            )

        # 解析Agent服务响应
        agent_data = agent_response.json()

        if not agent_data.get("success"):
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "QueryFailed",
                    "message": agent_data.get("error", "查询失败")
                }
            )

        # 提取响应内容与最终 session_id（前端可据此回查对话历史）
        content = agent_data.get("content", "")
        final_session_id = agent_data.get("session_id", session_id)

        # 计算耗时
        total_latency_ms = (time.time() - start_time) * 1000

        # 记录主智能体决策
        try:
            log_master_decision(
                session_id=final_session_id,
                user_query=request.query,
                intent="query",
                decision_path=["Agent转发"],
                subagents_called=[],
                reasoning_summary=f"查询完成，返回 {len(content)} 字符",
                total_latency_ms=total_latency_ms
            )
        except Exception as log_error:
            logger.warning(f"Failed to log master decision: {log_error}")

        # 把真实问答写入对话历史表，使 /api/v1/conversations 能展示本次问答。
        # 用 final_session_id 作为 conversation_id：同一 session 的多轮问答
        # 追加到同一条对话。持久化失败不影响查询结果返回（仅记录告警）。
        try:
            conversation_service.record_exchange(
                conversation_id=final_session_id,
                user_query=request.query,
                assistant_response=content,
                tool_call_info={
                    "source": "agent_service",
                    "forwarded": True,
                    "latency_ms": total_latency_ms,
                },
            )
        except Exception as persist_error:
            logger.warning(f"Failed to persist conversation exchange: {persist_error}")

        logger.info(f"查询完成: session={final_session_id}, 耗时={time.time() - start_time:.2f}s")

        # 返回标准格式的响应
        return QueryResponse(
            content=content,
            session_id=final_session_id,
            timestamp=agent_data.get("timestamp", ""),
            chartData=None,
            decision_path=[],
            sub_agent_calls=[],
            data_sources=[],
            reasoning={"agent_service": True, "latency_ms": total_latency_ms},
            metadata={"forwarded": True, "agent_service_url": AGENT_SERVICE_URL}
        )

    except HTTPException:
        raise
    except requests.Timeout:
        raise HTTPException(
            status_code=504,
            detail={
                "error": "Timeout",
                "message": "Agent服务响应超时"
            }
        )
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
                "message": "查询处理失败",
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
