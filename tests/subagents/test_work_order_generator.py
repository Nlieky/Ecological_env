# tests/subagents/test_work_order_generator.py
import pytest
from pathlib import Path
import sys

# Get the project root (Ecological_env directory)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "subagents" / "disposition-execution-agent" / "skills" / "disposition-execution-core" / "scripts"))

from work_order_generator import WorkOrderGenerator


def test_generate_work_order():
    """测试工单生成"""
    generator = WorkOrderGenerator()

    alert_info = {
        "level": "serious",
        "violation_type": "稀释排放",
        "fused_confidence": 0.92
    }

    data_context = {
        "anomaly_time_range": ["2024-05-29 02:00", "2024-05-29 04:00"],
        "anomaly_indicators": ["COD", "TN", "TP"]
    }

    work_order = generator.generate_work_order(alert_info, data_context)

    assert "id" in work_order
    assert "data_traceback" in work_order
    assert "inspection_points" in work_order
    assert "legal_references" in work_order
    assert "recommended_actions" in work_order
