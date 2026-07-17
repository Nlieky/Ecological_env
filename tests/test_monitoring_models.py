"""监控数据模型测试"""

import pytest
from backend.models.monitoring import (
    MonitoringData,
    DataQualityMetric,
    SystemHealth,
    Alert
)


def test_monitoring_data_model():
    """测试监测数据模型"""
    data = MonitoringData(
        timestamp="2026-07-17T15:30:00Z",
        influent={"pH": 7.2, "COD": 150.5},
        effluent={"pH": 6.8, "COD": 35.2},
        flow_rate=125.5,
        quality_score=0.95
    )
    assert data.timestamp == "2026-07-17T15:30:00Z"
    assert data.influent["pH"] == 7.2
    assert data.influent["COD"] == 150.5
    assert data.effluent["pH"] == 6.8
    assert data.effluent["COD"] == 35.2
    assert data.flow_rate == 125.5
    assert data.quality_score == 0.95


def test_data_quality_metric_model():
    """测试数据质量指标模型"""
    metric = DataQualityMetric(
        completeness_rate=0.98,
        missing_data_count=15,
        anomaly_count=3,
        last_update="2026-07-17T15:30:00Z"
    )
    assert metric.completeness_rate == 0.98
    assert metric.missing_data_count == 15
    assert metric.anomaly_count == 3
    assert metric.last_update == "2026-07-17T15:30:00Z"


def test_system_health_model():
    """测试系统健康状态模型"""
    health = SystemHealth(
        overall_status="healthy",
        components={
            "database": {"status": "healthy", "latency_ms": 5},
            "llm_service": {"status": "healthy", "latency_ms": 150}
        },
        uptime_seconds=86400
    )
    assert health.overall_status == "healthy"
    assert health.components["database"]["status"] == "healthy"
    assert health.uptime_seconds == 86400


def test_alert_model():
    """测试告警模型"""
    alert = Alert(
        id="alert-001",
        severity="high",
        type="anomaly",
        message="检测到异常数据模式",
        timestamp="2026-07-17T15:30:00Z"
    )
    assert alert.id == "alert-001"
    assert alert.severity == "high"
    assert alert.type == "anomaly"
    assert alert.message == "检测到异常数据模式"
    assert alert.timestamp == "2026-07-17T15:30:00Z"
    assert alert.acknowledged is False  # 默认值


def test_alert_with_acknowledged():
    """测试已确认告警模型"""
    alert = Alert(
        id="alert-002",
        severity="medium",
        type="quality",
        message="数据质量下降",
        timestamp="2026-07-17T15:30:00Z",
        acknowledged=True
    )
    assert alert.acknowledged is True


def test_monitoring_data_validation():
    """测试监测数据验证"""
    # 测试缺少必需字段时应该失败
    with pytest.raises(Exception):
        MonitoringData(
            timestamp="2026-07-17T15:30:00Z"
            # 缺少必需字段: influent, effluent, flow_rate, quality_score
        )


def test_data_quality_metric_validation():
    """测试数据质量指标验证"""
    # 测试 completeness_rate 范围验证
    with pytest.raises(Exception):
        DataQualityMetric(
            completeness_rate=1.5,  # 超过范围
            missing_data_count=0,
            anomaly_count=0,
            last_update="2026-07-17T15:30:00Z"
        )

    # 测试负数验证
    with pytest.raises(Exception):
        DataQualityMetric(
            completeness_rate=0.9,
            missing_data_count=-5,  # 负数
            anomaly_count=0,
            last_update="2026-07-17T15:30:00Z"
        )
