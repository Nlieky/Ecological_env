# tests/subagents/test_data_acquisition.py
import pytest
from pathlib import Path
import sys

# Add the scripts directory to path
scripts_dir = Path(__file__).parent.parent / "subagents" / "multi-dimensional-data-perception-agent" / "skills" / "data-perception-core" / "scripts"
sys.path.insert(0, str(scripts_dir))

from data_acquisition import DataAcquisitionModule


def test_acquire_from_csv():
    """测试从CSV文件获取数据"""
    module = DataAcquisitionModule()

    result = module.acquire_from_csv(
        influent_path="data/pollution_water_in.csv",
        effluent_path="data/pollution_water_out.csv"
    )

    assert "influent" in result
    assert "effluent" in result
    assert len(result["influent"]) > 0


def test_acquire_multi_dimensional():
    """测试获取多维数据"""
    module = DataAcquisitionModule()

    result = module.acquire_multi_dimensional({
        "water_quality": {"path": "data/pollution_water_in.csv"},
        "flow": {"path": "data/flow_data.csv"}
    })

    assert "water_quality" in result
    assert "flow" in result
