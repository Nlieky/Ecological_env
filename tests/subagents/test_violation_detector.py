"""
Tests for ViolationDetector
TDD: Tests written first, implementation follows
"""
import pytest
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "subagents" / "rule-reasoning-agent" / "skills" / "rule-reasoning-core" / "scripts"))

from violation_detector import ViolationDetector


def test_detect_bottle_interference():
    """测试插瓶干扰检测"""
    detector = ViolationDetector(rule_config_path="shared/configs/rule_config.yaml")

    anomaly_data = {
        "type": "平稳异常",
        "indicator": "COD",
        "duration": "2h",
        "std_dev": 0.05
    }

    context = {
        "equipment_status": "running",
        "in_maintenance": False
    }

    result = detector.detect_violation(anomaly_data, context)

    assert result["violation_type"] == "插瓶干扰"
    assert result["suspicion_level"] == "high"


def test_filter_false_positive():
    """测试误报过滤"""
    detector = ViolationDetector(rule_config_path="shared/configs/rule_config.yaml")

    anomaly_data = {
        "type": "突变异常",
        "indicator": "COD"
    }

    context = {
        "equipment_status": "shutdown",
        "maintenance_record": True
    }

    result = detector.detect_violation(anomaly_data, context)

    assert result.get("filtered") == True
    assert result.get("filter_reason") == "设备依法停运检修"


def test_no_violation_matched():
    """测试无匹配违规的情况"""
    detector = ViolationDetector(rule_config_path="shared/configs/rule_config.yaml")

    anomaly_data = {
        "type": "未知异常类型",
        "indicator": "COD"
    }

    context = {
        "equipment_status": "running",
        "in_maintenance": False
    }

    result = detector.detect_violation(anomaly_data, context)

    assert result["violation_type"] is None
    assert result["confidence"] == 0.0


def test_confidence_calculation():
    """测试置信度计算"""
    detector = ViolationDetector(rule_config_path="shared/configs/rule_config.yaml")

    anomaly_data = {
        "type": "平稳异常",
        "indicator": "COD",
        "duration": "5h",
        "std_dev": 0.05
    }

    context = {
        "equipment_status": "running",
        "in_maintenance": False
    }

    result = detector.detect_violation(anomaly_data, context)

    assert "confidence" in result
    assert 0.0 <= result["confidence"] <= 1.0
    # Longer duration should increase confidence
    assert result["confidence"] > 0.85
