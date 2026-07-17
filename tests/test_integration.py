"""集成测试"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.conversation_service import ConversationService


@pytest.fixture
def client():
    """FastAPI 测试客户端"""
    return TestClient(app)


def test_full_conversation_flow(client):
    """测试完整的对话流程"""
    # 1. 创建对话
    response = client.post("/api/v1/conversations", json={
        "title": "集成测试对话"
    })
    assert response.status_code == 200
    conv_data = response.json()["data"]
    conv_id = conv_data["id"]

    # 2. 获取对话列表
    response = client.get("/api/v1/conversations")
    assert response.status_code == 200
    conv_list = response.json()["data"]["conversations"]
    assert any(c["id"] == conv_id for c in conv_list)

    # 3. 获取对话详情
    response = client.get(f"/api/v1/conversations/{conv_id}")
    assert response.status_code == 200
    conv_detail = response.json()["data"]
    assert conv_detail["id"] == conv_id

    # 4. 测试实时数据
    response = client.get("/api/v1/monitoring/realtime")
    assert response.status_code == 200
    realtime_data = response.json()["data"]
    assert "influent" in realtime_data

    # 5. 测试历史数据
    response = client.get("/api/v1/data/history?time_range=24h")
    assert response.status_code == 200
    history_data = response.json()["data"]
    assert "records" in history_data


def test_api_error_handling(client):
    """测试API错误处理"""
    # 测试不存在的对话
    response = client.get("/api/v1/conversations/nonexistent_id")
    assert response.status_code == 200
    assert response.json()["success"] is False
