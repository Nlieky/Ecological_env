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


def test_history_records_have_influent_effluent():
    """历史记录含 influent/effluent 子结构"""
    client = TestClient(app)
    data = client.get("/api/v1/data/history?time_range=24h&page=1&page_size=5").json()["data"]
    assert data["total_count"] > 0
    rec = data["records"][0]
    assert "timestamp" in rec and rec["timestamp"].endswith("Z")
    assert "influent" in rec and "effluent" in rec


def test_history_daily_aggregation_count():
    """daily 聚合：7d 窗口为 8 个日桶"""
    client = TestClient(app)
    data = client.get("/api/v1/data/history?time_range=7d&aggregation=daily&page=1&page_size=100").json()["data"]
    assert data["total_count"] == 8


def test_aggregated_has_series():
    """聚合数据含 influent 与 effluent 两个系列"""
    client = TestClient(app)
    data = client.get("/api/v1/data/aggregated?period=daily&metrics=avg,max,min").json()["data"]
    assert "influent" in data["data"] and "effluent" in data["data"]
    assert len(data["data"]["influent"]) > 0
    bucket = next(b for b in data["data"]["influent"].values() if b)
    assert any(k.startswith("pH_") for k in bucket)
