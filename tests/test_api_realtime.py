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


def test_realtime_timestamp_timezone():
    """测试实时数据端点返回带时区的时间戳"""
    client = TestClient(app)
    response = client.get("/api/v1/monitoring/realtime")
    assert response.status_code == 200
    data = response.json()

    # 验证时间戳格式符合 ISO 8601 且包含时区信息
    timestamp = data["data"]["timestamp"]
    assert isinstance(timestamp, str)

    # ISO 8601 时间戳应该以 'Z' (UTC) 或包含时区偏移 (+/-HH:MM)
    assert timestamp.endswith("Z") or "+" in timestamp or "-" in timestamp.split("T")[-1]

    # 验证基本格式 (YYYY-MM-DDTHH:MM:SS)
    assert "T" in timestamp
    parts = timestamp.split("T")
    assert len(parts) == 2
    date_part = parts[0]
    assert len(date_part) == 10  # YYYY-MM-DD
    assert date_part[4] == "-" and date_part[7] == "-"


def test_quality_timestamp_timezone():
    """测试数据质量端点返回带时区的时间戳"""
    client = TestClient(app)
    response = client.get("/api/v1/monitoring/quality")
    assert response.status_code == 200
    data = response.json()

    # 验证 last_update 时间戳包含时区信息
    last_update = data["data"]["last_update"]
    assert isinstance(last_update, str)

    # ISO 8601 时间戳应该以 'Z' (UTC) 或包含时区偏移
    assert last_update.endswith("Z") or "+" in last_update or "-" in last_update.split("T")[-1]


def test_quality_time_range_parameter():
    """测试数据质量端点的 time_range 参数"""
    client = TestClient(app)

    # 测试默认值
    response = client.get("/api/v1/monitoring/quality")
    assert response.status_code == 200

    # 测试不同的时间范围参数
    for time_range in ["1h", "24h", "7d", "30d"]:
        response = client.get(f"/api/v1/monitoring/quality?time_range={time_range}")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
