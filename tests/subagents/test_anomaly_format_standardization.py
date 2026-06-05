from pathlib import Path
import sys

# Add the parent package to path for proper imports
subagent_scripts = Path(__file__).parent.parent.parent.parent / "subagents/anomaly-detection-agent/skills/anomaly-detection-core"
sys.path.insert(0, str(subagent_scripts))

# Import using importlib to handle the package structure properly
import importlib.util

# Load the module as a script to avoid relative import issues
spec = importlib.util.spec_from_file_location(
    "anomaly_detection_scripts",
    subagent_scripts / "scripts" / "__init__.py"
)
module = importlib.util.module_from_spec(spec)

# Execute the module - this will define standardize_anomaly_output
spec.loader.exec_module(module)

# Get the function we need
standardize_anomaly_output = module.standardize_anomaly_output

def test_standardize_anomaly_output():
    """测试异常输出标准化"""
    # 模拟原始输出
    raw_output = {
        "anomalies": [
            {
                "indicator": "pH值",
                "timestamp": "2024-01-01 12:00",
                "score": 0.9,
                "type": "constant"
            },
            {
                "indicator": "COD",
                "time": "2024-01-01 13:00",
                "anomaly_score": 0.7,
                "pattern": "spike"
            }
        ],
        "patterns": {"constant": 1, "spike": 1},
        "violations": []
    }

    standardized = standardize_anomaly_output(raw_output)

    # 验证：anomalies列表存在
    assert "anomalies" in standardized
    assert len(standardized["anomalies"]) == 2

    # 验证：第一个异常的格式
    anom1 = standardized["anomalies"][0]
    assert anom1["indicator"] == "effluent_pH"  # 格式化为 source_indicator
    assert anom1["times"] == "2024-01-01 12:00"
    assert anom1["score"] == 0.9
    assert anom1["pattern"] == "constant"
    assert anom1["severity"] == "high"  # 基于score=0.9判定

    # 验证：第二个异常的格式
    anom2 = standardized["anomalies"][1]
    assert anom2["indicator"] == "effluent_COD"
    assert anom2["pattern"] == "spike"  # type字段被映射到pattern

def test_empty_input():
    """测试空输入"""
    result = standardize_anomaly_output(None)
    assert result["anomalies"] == []
    assert result["status"] == "error"

def test_nested_path_extraction():
    """测试嵌套路径提取"""
    nested_output = {
        "result": {
            "anomalies": [
                {"indicator": "pH", "score": 0.8, "type": "trend"}
            ]
        }
    }

    standardized = standardize_anomaly_output(nested_output)
    assert len(standardized["anomalies"]) == 1
    assert standardized["anomalies"][0]["severity"] == "high"

def test_invalid_score_conversion():
    """测试无效分数值转换"""
    invalid_output = {
        "anomalies": [
            {"indicator": "pH", "score": "invalid_value"}  # 非数字字符串
        ]
    }
    result = standardize_anomaly_output(invalid_output)
    # 应该使用默认值0.5
    assert result["anomalies"][0]["score"] == 0.5
    assert result["anomalies"][0]["severity"] == "medium"

def test_boundary_severity_scores():
    """测试边界严重程度分数"""
    test_cases = [
        (0.8, "high"),    # 高边界
        (0.79, "medium"), # 低于高边界
        (0.5, "medium"),  # 中等边界
        (0.49, "low"),    # 低于中等边界
        (0.0, "low"),     # 最低
        (1.0, "high"),    # 最高
    ]

    for score, expected_severity in test_cases:
        output = {"anomalies": [{"indicator": "pH", "score": score}]}
        result = standardize_anomaly_output(output)
        actual_severity = result["anomalies"][0]["severity"]
        assert actual_severity == expected_severity, f"Score {score} should be {expected_severity}, got {actual_severity}"

def run_tests():
    """运行所有测试"""
    test_standardize_anomaly_output()
    print("✅ test_standardize_anomaly_output passed")

    test_empty_input()
    print("✅ test_empty_input passed")

    test_nested_path_extraction()
    print("✅ test_nested_path_extraction passed")

    test_invalid_score_conversion()
    print("✅ test_invalid_score_conversion passed")

    test_boundary_severity_scores()
    print("✅ test_boundary_severity_scores passed")

    print("\n所有测试通过!")

if __name__ == "__main__":
    run_tests()
