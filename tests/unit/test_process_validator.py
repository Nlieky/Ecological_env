"""规则推理 process_validator 单元测试。"""
import sys
import importlib.util
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import pandas as pd
import numpy as np

PV_PATH = ROOT / "subagents" / "rule-reasoning-agent" / "skills" / "rule-reasoning-core" / "scripts" / "process_validator.py"


def _load_pv():
    spec = importlib.util.spec_from_file_location("process_validator", PV_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.ProcessValidator


def test_ph_cod_bottle_interference():
    """pH std=0 + COD std=0 + 平稳异常 → 插瓶。"""
    PV = _load_pv()
    v = PV()
    effluent = pd.DataFrame({"pH值": [7.0]*20, "化学需氧量浓度（毫克/升）": [50.0]*20})
    anomalies = [{"features": ["平稳"], "indicator": "pH"}, {"features": ["平稳"], "indicator": "COD"}]
    result = v.validate(anomalies, {}, {}, data=effluent)
    types = [str(p.get("pattern")) for p in result.get("matched_patterns", [])]
    assert any("插瓶" in t for t in types), f"expected 插瓶, got {types}"


def test_multi_indicator_dilution():
    """2+ 污染物同步突降 >50% + 突变 → 稀释。"""
    PV = _load_pv()
    v = PV()
    effluent = pd.DataFrame({
        "化学需氧量浓度（毫克/升）": [100]*10 + [40]*10,
        "氨氮浓度（毫克/升）": [5]*10 + [2]*10,
    })
    anomalies = [{"features": ["突变"], "indicator": "COD"}, {"features": ["突变"], "indicator": "氨氮"}]
    result = v.validate(anomalies, {}, {}, data=effluent)
    types = [str(p.get("pattern")) for p in result.get("matched_patterns", [])]
    assert any("稀释" in t for t in types), f"expected 稀释, got {types}"
