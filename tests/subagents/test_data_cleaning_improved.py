from pathlib import Path
import sys

# Add subagent scripts to path
subagent_scripts = Path(__file__).parent.parent.parent.parent / "subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts"
sys.path.insert(0, str(subagent_scripts))

from data_cleaning import DataCleaningModule

def test_partial_anomaly_fields():
    """测试部分字段异常时，其他有效字段被保留"""
    cleaner = DataCleaningModule()

    data = [
        {"pH值": 7.5, "COD": 45, "TN": 15},  # 正常
        {"pH值": 25, "COD": 45, "TN": 15},  # pH异常
        {"pH值": 7.5, "COD": 1500, "TN": 15},  # COD异常
        {"pH值": 7.5, "COD": 45, "TN": 150},  # TN异常
        {"pH值": 25, "COD": 1500, "TN": 150},  # 全部异常
    ]

    result = cleaner.clean_water_quality_data(data)

    # 验证：所有记录都被保留
    assert result["quality_report"]["cleaned_count"] == 5

    # 验证：第二条记录的异常字段被标记
    assert "_anomaly_fields" in result["cleaned_data"][1]
    assert "pH值" in result["cleaned_data"][1]["_anomaly_fields"]

    # 验证：第二条记录的有效字段被保留（值已转换为float）
    assert result["cleaned_data"][1]["COD"] == 45.0
    assert result["cleaned_data"][1]["TN"] == 15.0

    # 验证：质量报告包含字段异常统计
    assert "anomaly_fields_summary" in result["quality_report"]
    assert result["quality_report"]["anomaly_fields_summary"]["pH值"] == 2  # pH异常2次

def test_anomaly_field_preservation():
    """测试异常值被保留并标记"""
    cleaner = DataCleaningModule()

    data = [{"pH值": 25, "COD": 45}]

    result = cleaner.clean_water_quality_data(data)

    # 异常值应该被保留（而不是设为None）
    assert result["cleaned_data"][0]["pH值"] == 25
    # 但被标记为异常
    assert "pH值" in result["cleaned_data"][0]["_anomaly_fields"]

def run_tests():
    """运行所有测试"""
    test_partial_anomaly_fields()
    print("[PASS] test_partial_anomaly_fields passed")

    test_anomaly_field_preservation()
    print("[PASS] test_anomaly_field_preservation passed")

    print("\nAll tests passed!")

if __name__ == "__main__":
    run_tests()
