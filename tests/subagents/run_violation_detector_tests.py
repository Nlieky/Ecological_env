"""
Simple test runner for ViolationDetector tests
"""
import sys
from pathlib import Path

# Add the scripts directory to the path
project_root = Path(__file__).parent.parent.parent.absolute()
scripts_path = project_root / "subagents" / "rule-reasoning-agent" / "skills" / "rule-reasoning-core" / "scripts"
sys.path.insert(0, str(scripts_path))

from violation_detector import ViolationDetector


def test_detect_bottle_interference():
    """测试插瓶干扰检测"""
    print("Testing bottle interference detection...")
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

    assert result["violation_type"] == "插瓶干扰", f"Expected '插瓶干扰', got {result['violation_type']}"
    assert result["suspicion_level"] == "high", f"Expected 'high', got {result['suspicion_level']}"
    print("✓ test_detect_bottle_interference PASSED")


def test_filter_false_positive():
    """测试误报过滤"""
    print("Testing false positive filter...")
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

    assert result.get("filtered") == True, f"Expected filtered=True, got {result.get('filtered')}"
    assert result.get("filter_reason") == "设备依法停运检修", f"Expected '设备依法停运检修', got {result.get('filter_reason')}"
    print("✓ test_filter_false_positive PASSED")


def test_no_violation_matched():
    """测试无匹配违规的情况"""
    print("Testing no violation matched...")
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

    assert result["violation_type"] is None, f"Expected None, got {result['violation_type']}"
    assert result["confidence"] == 0.0, f"Expected 0.0, got {result['confidence']}"
    print("✓ test_no_violation_matched PASSED")


def test_confidence_calculation():
    """测试置信度计算"""
    print("Testing confidence calculation...")
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

    assert "confidence" in result, "Expected 'confidence' in result"
    assert 0.0 <= result["confidence"] <= 1.0, f"Expected confidence between 0.0 and 1.0, got {result['confidence']}"
    # Longer duration should increase confidence
    assert result["confidence"] > 0.85, f"Expected confidence > 0.85, got {result['confidence']}"
    print("✓ test_confidence_calculation PASSED")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Running ViolationDetector Tests")
    print("=" * 60)

    tests = [
        test_detect_bottle_interference,
        test_filter_false_positive,
        test_no_violation_matched,
        test_confidence_calculation
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} ERROR: {e}")
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
