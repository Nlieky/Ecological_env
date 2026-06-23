"""
Hermes API Client - 调用 Hermes API Server

Hermes API Server 提供 OpenAI 兼容的对话接口
"""
import httpx
import logging
from typing import List, Dict, Any, Optional
from backend.core.config import settings

logger = logging.getLogger(__name__)


class HermesAPIClient:
    """Hermes API 客户端"""

    def __init__(self):
        self.base_url = settings.HERMES_API_URL.rstrip("/")
        self.api_key = settings.HERMES_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()

    async def list_skills(self) -> List[Dict[str, Any]]:
        """获取技能列表（子智能体）"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v1/skills",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        调用对话接口（OpenAI 兼容）

        Args:
            messages: 消息列表
            session_id: 会话ID（可选）

        Returns:
            完整的 Hermes 响应
        """
        payload = {
            "model": settings.LLM_MODEL,
            "messages": messages
        }

        if session_id:
            payload["session_id"] = session_id

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()

    async def get_agent_status(self) -> Dict[str, Any]:
        """获取智能体状态"""
        # 通过健康检查和技能列表综合判断
        health = await self.health_check()
        skills = await self.list_skills()

        return {
            "hermes_api_server": {
                "status": "healthy" if health.get("status") == "ok" else "unhealthy",
                "url": self.base_url
            },
            "loaded_skills": skills
        }


# 全局实例
_hermes_client: Optional[HermesAPIClient] = None


def get_hermes_client() -> HermesAPIClient:
    """获取 Hermes API 客户端实例"""
    global _hermes_client
    if _hermes_client is None:
        _hermes_client = HermesAPIClient()
    return _hermes_client
