"""
完整的 FastAPI 后端集成测试
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestFullAPI:
    """完整 API 测试"""

    @pytest.fixture
    def client(self):
        from backend.main import app
        return TestClient(app)

    def test_health_check(self, client):
        """测试健康检查"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data

    def test_hermes_system_info(self, client):
        """测试 Hermes 系统信息"""
        response = client.get("/api/hermes/system")
        assert response.status_code == 200
        data = response.json()
        assert "master_agent" in data
        assert "decision_tree" in data
        assert "sub_agents" in data
        assert len(data["sub_agents"]) == 4

    def test_hermes_capabilities(self, client):
        """测试 Hermes 能力接口"""
        response = client.get("/api/query/capabilities")
        assert response.status_code == 200
        data = response.json()
        assert "decision_tree" in data
        assert len(data["decision_tree"]) == 5  # 5 个步骤

    def test_query_endpoint_structure(self, client):
        """测试查询接口结构"""
        # 测试无效请求（空查询）
        response = client.post("/api/query", json={"query": ""})
        assert response.status_code == 422  # 验证错误

    @pytest.mark.skipif(
        True,  # 需要 Hermes API Server 运行
        reason="Requires Hermes API Server"
    )
    def test_query_with_hermes(self, client):
        """测试真实 Hermes 查询"""
        response = client.post(
            "/api/query",
            json={"query": "你好"}
        )
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert "content" in data
            assert "decision_path" in data
            assert "session_id" in data
