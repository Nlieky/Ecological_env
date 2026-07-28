"""算子单元测试。"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import pandas as pd
import numpy as np


def test_constant_detector_no_violation_type():
    """恒定检测器只输出特征(平稳),不判违规模式。"""
    from shared.operators.specialized.constant_detector import ConstantDetector
    d = ConstantDetector()
    data = pd.Series([7.0] * 20)
    mask, details = d.detect(data)
    assert details.get("is_constant") is True
    assert "score" in details
    assert "violation_type" not in details, "算子不该判违规模式(交规则推理)"


def test_constant_detector_normal_data():
    """正常波动数据不报平稳。"""
    from shared.operators.specialized.constant_detector import ConstantDetector
    d = ConstantDetector()
    data = pd.Series(np.random.RandomState(42).randn(20) + 7)
    mask, details = d.detect(data)
    assert details.get("is_constant") is False
