"""历史数据API端点测试"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app


def test_history_endpoint():
    """测试历史数据端点"""
    client = TestClient(app)
    response = client.get("/api/v1/data/history?time_range=24h")
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "data" in data


def test_aggregated_endpoint():
    """测试聚合数据端点"""
    client = TestClient(app)
    response = client.get("/api/v1/data/aggregated?period=daily")
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "data" in data


def test_history_endpoint_with_pagination():
    """测试历史数据端点分页功能"""
    client = TestClient(app)
    response = client.get("/api/v1/data/history?time_range=24h&page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "metadata" in data
    assert data["metadata"]["page"] == 1
    assert data["metadata"]["page_size"] == 10


def test_history_endpoint_with_indicators():
    """测试历史数据端点指标筛选功能"""
    client = TestClient(app)
    response = client.get("/api/v1/data/history?time_range=24h&indicators=pH,COD")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_aggregated_endpoint_with_metrics():
    """测试聚合数据端点指标选择功能"""
    client = TestClient(app)
    response = client.get("/api/v1/data/aggregated?period=daily&metrics=avg,max")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
