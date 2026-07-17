"""测试 v1 API 实时数据端点"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app


def test_realtime_endpoint():
    """测试实时数据端点"""
    client = TestClient(app)
    response = client.get("/api/v1/monitoring/realtime")
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "data" in data


def test_quality_endpoint():
    """测试数据质量端点"""
    client = TestClient(app)
    response = client.get("/api/v1/monitoring/quality")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
