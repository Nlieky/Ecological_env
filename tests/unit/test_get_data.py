"""数据感知 get_data.py 单元测试。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
GD = ROOT / "subagents" / "multi-dimensional-data-perception-agent" / "skills" / "data-perception-core" / "scripts"
sys.path.insert(0, str(GD))


def test_hrt_constant():
    """脚本定义了 _HRT_HOURS=2。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("get_data", GD / "get_data.py")
    gd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gd)
    assert gd._HRT_HOURS == 2


def test_compute_missing_points_range():
    """range 模式：缺 01:00。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("get_data", GD / "get_data.py")
    gd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gd)
    records = [{"timestamp": "2026-07-14 00:00:00"}, {"timestamp": "2026-07-14 02:00:00"}]
    missing = gd._compute_missing_points(records, use_range=True, start="2026-07-14",
                                         end="2026-07-14 02:00:00", hours_back=0)
    assert "2026-07-14 01:00:00" in missing


def test_compute_missing_points_hours():
    """hours 模式：以最新时间往前 N 小时，缺 01:00。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("get_data", GD / "get_data.py")
    gd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gd)
    records = [{"timestamp": "2026-07-14 00:00:00"}, {"timestamp": "2026-07-14 02:00:00"}]
    missing = gd._compute_missing_points(records, use_range=False, start=None,
                                         end=None, hours_back=3)
    assert "2026-07-14 01:00:00" in missing
