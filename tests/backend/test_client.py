"""Hermes API Client 测试"""
import pytest
from backend.api.client import HermesAPIClient


@pytest.mark.integration
class TestHermesAPIClient:
    """Hermes API Client 测试"""

    @pytest.fixture
    def client(self):
        return HermesAPIClient()

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """测试健康检查"""
        response = await client.health_check()
        assert "status" in response

    @pytest.mark.asyncio
    async def test_list_skills(self, client):
        """测试技能列表"""
        skills = await client.list_skills()
        assert isinstance(skills, list)
