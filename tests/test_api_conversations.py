"""对话历史API端点测试"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app


def test_list_conversations():
    """测试对话列表端点"""
    client = TestClient(app)
    response = client.get("/api/v1/conversations")
    assert response.status_code == 200
    data = response.json()
    assert "success" in data


def test_create_conversation():
    """测试创建对话端点"""
    client = TestClient(app)
    response = client.post("/api/v1/conversations", json={
        "title": "测试对话"
    })
    assert response.status_code == 200


def test_get_conversation_detail():
    """测试获取对话详情端点"""
    client = TestClient(app)
    # 先创建一个对话
    create_response = client.post("/api/v1/conversations", json={
        "title": "测试对话"
    })
    conv_id = create_response.json()["data"]["id"]

    # 获取详情
    response = client.get(f"/api/v1/conversations/{conv_id}")
    assert response.status_code == 200
