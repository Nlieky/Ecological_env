"""build_chart 单元测试。"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def test_build_chart_no_anomalies():
    """无异常时，按进出水分图（进水一张、出水一张），每张含多指标线。"""
    from shared.viz.build_chart import build_chart_data
    records = {
        "influent": [{"timestamp": "2026-07-14 00:00:00", "pH": 7.4, "COD": 68.0},
                     {"timestamp": "2026-07-14 01:00:00", "pH": 7.5, "COD": 70.0}],
        "effluent": [{"timestamp": "2026-07-14 00:00:00", "pH": 7.3, "COD": 33.0},
                     {"timestamp": "2026-07-14 01:00:00", "pH": 7.35, "COD": 34.0}],
    }
    charts = build_chart_data(records, indicators=["pH", "COD"])
    # 应该有 2 个图：进水水质趋势 + 出水水质趋势
    assert len(charts) == 2
    titles = [c["title"] for c in charts]
    assert "进水水质趋势" in titles
    assert "出水水质趋势" in titles
    # 每张图有 2 条线（pH + COD）
    opt = charts[0]["option"]
    assert len(opt["series"]) == 2


def test_build_chart_with_anomalies_markpoint():
    """有异常时，对应指标的线含 markPoint。"""
    from shared.viz.build_chart import build_chart_data
    records = {
        "influent": [{"timestamp": "2026-07-14 00:00:00", "pH": 7.4},
                     {"timestamp": "2026-07-14 01:00:00", "pH": 9.5}],
        "effluent": [],
    }
    anomalies = [{"indicator": "pH", "data_type": "influent",
                  "timestamp": "2026-07-14 01:00:00", "features": ["突变"]}]
    charts = build_chart_data(records, indicators=["pH"], anomalies=anomalies)
    # 进水图有 pH 线，含 markPoint
    infl_chart = [c for c in charts if "进水" in c["title"]][0]
    ph_series = [s for s in infl_chart["option"]["series"] if s["name"] == "pH"][0]
    assert "markPoint" in ph_series
    assert len(ph_series["markPoint"]["data"]) >= 1
