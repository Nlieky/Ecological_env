"""build_chart 单元测试。"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def test_build_chart_no_anomalies():
    from shared.viz.build_chart import build_chart_data
    records = {
        "influent": [{"timestamp": "2026-07-14 00:00:00", "pH": 7.4, "COD": 68.0},
                     {"timestamp": "2026-07-14 01:00:00", "pH": 7.5, "COD": 70.0}],
        "effluent": [{"timestamp": "2026-07-14 00:00:00", "pH": 7.3, "COD": 33.0},
                     {"timestamp": "2026-07-14 01:00:00", "pH": 7.35, "COD": 34.0}],
    }
    charts = build_chart_data(records, indicators=["pH", "COD"])
    assert len(charts) == 2
    assert charts[0]["title"] == "pH 趋势"
    opt = charts[0]["option"]
    assert len(opt["series"]) == 2


def test_build_chart_with_anomalies_markpoint():
    from shared.viz.build_chart import build_chart_data
    records = {
        "influent": [{"timestamp": "2026-07-14 00:00:00", "pH": 7.4},
                     {"timestamp": "2026-07-14 01:00:00", "pH": 9.5}],
        "effluent": [],
    }
    anomalies = [{"indicator": "pH", "data_type": "influent",
                  "timestamp": "2026-07-14 01:00:00", "features": ["突变"]}]
    charts = build_chart_data(records, indicators=["pH"], anomalies=anomalies)
    infl_series = charts[0]["option"]["series"][0]
    assert "markPoint" in infl_series
    assert len(infl_series["markPoint"]["data"]) >= 1
