# tests/subagents/test_data_decomposition.py
import pytest
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "subagents" / "multi-dimensional-data-perception-agent" / "skills" / "data-perception-core" / "scripts"))

from data_decomposition import DataDecompositionModule
from time_alignment import TimeAlignmentModule


def test_data_decomposition():
    """测试数据分解"""
    module = DataDecompositionModule()

    input_data = {
        "influent": [
            {"监测时间": "2024-01-01 00:00", "pH值": 7.5, "化学需氧量浓度（毫克/升）": 45}
        ],
        "effluent": [
            {"监测时间": "2024-01-01 02:00", "pH值": 7.8, "化学需氧量浓度（毫克/升）": 50}
        ]
    }

    result = module.decompose_multi_dimensional(input_data)

    assert "water_quality" in result
    assert "influent" in result["water_quality"]
    assert "effluent" in result["water_quality"]


def test_time_alignment():
    """测试时序对齐"""
    module = TimeAlignmentModule()

    influent = [{"监测时间": "2024-01-01 00:00", "pH值": 7.5}]
    effluent = [{"监测时间": "2024-01-01 02:00", "pH值": 7.8}]

    result = module.align_with_lag(
        influent=influent,
        effluent=effluent,
        lag_hours=2
    )

    assert "aligned" in result
    assert result["alignment_method"] == "time_lag"
