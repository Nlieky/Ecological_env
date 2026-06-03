# tests/subagents/test_data_cleaning.py
import pytest
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "subagents" / "multi-dimensional-data-perception-agent" / "skills" / "data-perception-core" / "scripts"))

from data_cleaning import DataCleaningModule
from standardization import StandardizationModule


def test_data_cleaning():
    """测试数据清洗"""
    module = DataCleaningModule()

    dirty_data = [
        {"pH值": 7.5, "化学需氧量浓度（毫克/升）": None},  # 缺失值
        {"pH值": 15.0, "化学需氧量浓度（毫克/升）": 45},  # pH异常
        {"pH值": 7.2, "化学需氧量浓度（毫克/升）": -10}  # 负值异常
    ]

    result = module.clean_water_quality_data(dirty_data)

    assert "cleaned_data" in result
    assert "quality_report" in result
    assert result["quality_report"]["completeness"] < 1.0


def test_standardization():
    """测试标准化"""
    module = StandardizationModule()

    input_data = {
        "influent": [
            {"pH值": 7.5, "COD": 45}  # 旧字段名
        ],
        "effluent": [
            {"pH值": 7.8, "COD": 50}
        ]
    }

    result = module.standardize_water_quality(input_data)

    assert "water_quality" in result
    assert result["water_quality"]["influent"][0]["pH"] == 7.5
