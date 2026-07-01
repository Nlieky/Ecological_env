"""
查询接口 - Hermes 智能体核心接口

直接调用 Hermes AIAgent，无需额外的 HTTP API Server
"""
import os
import sys
import logging
import time
from pathlib import Path
from fastapi import APIRouter, HTTPException
from backend.models.query import QueryRequest, QueryResponse
from backend.utils.loggers import generate_session_id, log_master_decision

# 添加 Hermes 到路径
HERMES_PATH = Path("D:/Hermes/hermes-agent")
if str(HERMES_PATH) not in sys.path:
    sys.path.insert(0, str(HERMES_PATH))

# 导入 AIAgent
from run_agent import AIAgent

logger = logging.getLogger(__name__)
router = APIRouter()

# 项目目录
PROJECT_DIR = Path("E:/project/Ecological_env").resolve()

# 缓存 agent 实例
_agent_cache = {}


def get_agent(session_id: str = None) -> AIAgent:
    """
    获取或创建 AIAgent 实例

    Args:
        session_id: 会话ID（可选）

    Returns:
        AIAgent 实例
    """
    if session_id and session_id in _agent_cache:
        return _agent_cache[session_id]

    # 确保在项目目录
    current_cwd = os.getcwd()
    if current_cwd != str(PROJECT_DIR):
        logger.info(f"切换目录: {current_cwd} -> {PROJECT_DIR}")
        os.chdir(PROJECT_DIR)

    # 读取环境变量
    base_url = os.environ.get("LLM_BASE_URL", "http://172.16.12.41:30000/v1")
    model = os.environ.get("LLM_MODEL", "ctgu-vlm")
    provider = os.environ.get("LLM_PROVIDER", "custom")
    api_key = os.environ.get("LLM_API_KEY", "")

    # 创建 AIAgent
    agent = AIAgent(
        base_url=base_url,
        api_key=api_key,
        model=model,
        provider=provider,
        load_soul_identity=True,      # 加载 workspace/SOUL.md
        skip_context_files=False,     # 加载 AGENTS.md、MEMORY.md
        max_iterations=10,
        quiet_mode=True,
        session_id=session_id,
    )

    if session_id:
        _agent_cache[session_id] = agent

    logger.info(f"创建 AIAgent 实例: session_id={session_id}")
    return agent


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

    # 生成或使用提供的 session_id
    session_id = request.session_id or generate_session_id()

    try:
        logger.info(f"收到查询: {request.query[:50]}...")

        # 获取 agent（自动加载身份文件）
        agent = get_agent(session_id)

        # 直接调用 AIAgent
        response = agent.run_conversation(
            user_message=request.query,
            conversation_history=None,  # 可选：实现历史记录管理
        )

        # AIAgent 返回字符串响应
        content = str(response) if response else ""

        # 解析决策路径
        decision_path = parse_decision_path(content)

        # 提取子智能体调用列表
        subagents_called = []
        for step in decision_path:
            if "action" in step and "调用" in step["action"]:
                agent_name = step["action"].replace("调用 ", "")
                subagents_called.append(agent_name)

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
                reasoning_summary=f"查询完成，返回 {len(content)} 字符",
                total_latency_ms=total_latency_ms
            )
        except Exception as log_error:
            logger.warning(f"Failed to log master decision: {log_error}")

        # 构建响应
        query_response = QueryResponse(
            content=content,
            session_id=session_id,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            decision_path=decision_path,
            sub_agent_calls=[],  # TODO: 从 AIAgent 响应元数据提取
            data_sources=[],      # TODO: 从 AIAgent 响应元数据提取
            reasoning={
                "intent": "通过 AIAgent 直接调用，无需 HTTP API",
                "model": os.environ.get("LLM_MODEL", "ctgu-vlm")
            },
            metadata={
                "model": os.environ.get("LLM_MODEL", "ctgu-vlm"),
                "base_url": os.environ.get("LLM_BASE_URL", ""),
                "load_soul_identity": True,
                "skip_context_files": False
            }
        )

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
                "error": "HermesQueryError",
                "message": "AIAgent 调用失败",
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
            "method": "Direct AIAgent Call",
            "description": "直接调用 Hermes AIAgent，无需 HTTP API Server",
            "identity_files_loaded": [
                "workspace/SOUL.md",
                "workspace/AGENTS.md",
                "workspace/MEMORY.md"
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
