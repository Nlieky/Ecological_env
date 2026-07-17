"""
健康检查接口
"""
import os
import logging
import requests
from fastapi import APIRouter
from backend import __version__
from backend.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# 探测 Agent 服务时的短超时（connect, read），避免健康检查接口阻塞过久。
# 注意：Windows 上连接未监听的本地端口会挂起而非立即拒绝，
# 因此 connect 超时必须设得很短。
_AGENT_PROBE_TIMEOUT = (0.75, 1.5)


@router.get("/health", tags=["健康检查"])
async def health_check():
    """
    健康检查接口

    后端定位为**数据服务层**，`/api/query` 通过 HTTP 转发到独立运行的 Agent 服务
    （默认 :8642）。本接口返回后端自身状态，并探活 Agent 服务的可达性。
    """
    # 探活 Agent 服务（查询转发的下游）。
    # 将 localhost 归一化为 127.0.0.1，避免 IPv6(::1)/IPv4 双重解析导致超时翻倍。
    probe_url = f"{settings.AGENT_SERVICE_URL}/health".replace(
        "://localhost", "://127.0.0.1"
    )
    agent_reachable = False
    agent_initialized = None
    try:
        resp = requests.get(probe_url, timeout=_AGENT_PROBE_TIMEOUT)
        if resp.status_code == 200:
            agent_reachable = True
            agent_initialized = resp.json().get("agent_initialized")
    except Exception as e:
        logger.debug(f"Agent service probe failed: {e}")

    # LLM 配置（由 Agent 服务使用，后端仅作展示）
    env_configured = all([
        os.environ.get("LLM_BASE_URL"),
        os.environ.get("LLM_MODEL"),
    ])

    return {
        "status": "healthy",
        "version": __version__,
        "implementation": "Data Service Layer (forwards /api/query to independent Agent service)",
        "agent_service": {
            "url": settings.AGENT_SERVICE_URL,
            "reachable": agent_reachable,
            "status": "reachable" if agent_reachable else "unreachable",
            "agent_initialized": agent_initialized,
        },
        "environment_config": {
            "status": "configured" if env_configured else "missing",
            "llm_base_url": os.environ.get("LLM_BASE_URL", "not_set"),
            "llm_model": os.environ.get("LLM_MODEL", "not_set"),
        },
    }
