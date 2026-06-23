"""
健康检查接口
"""
from fastapi import APIRouter
from backend import __version__
from backend.api.client import get_hermes_client

router = APIRouter()


@router.get("/health", tags=["健康检查"])
async def health_check():
    """
    健康检查接口

    Returns:
        系统健康状态，包括 Hermes API Server 连接状态
    """
    try:
        client = get_hermes_client()
        hermes_health = await client.health_check()
        hermes_status = "connected" if hermes_health.get("status") == "ok" else "disconnected"
    except Exception as e:
        hermes_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "version": __version__,
        "components": {
            "hermes_api_server": {
                "status": hermes_status,
                "url": "http://localhost:8642"
            }
        }
    }
