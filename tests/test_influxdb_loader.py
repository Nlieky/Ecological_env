"""InfluxDBMonitoringDataset 单测(mock InfluxDB client,不依赖真实 InfluxDB)。

验证:InfluxDB 查询 → 契约字段 DataFrame → latest_timestamp / influent / effluent / window,
以及空数据时抛 DataUnavailableException(不静默)。
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd

# 项目根加到 sys.path(供 import backend)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _fake_pivoted_df():
    """模拟 query_data_frame pivot 后的返回(故意带 result/table 元数据列,测过滤)。"""
    return pd.DataFrame({
        "_time": pd.to_datetime(["2026-07-25 12:00:00", "2026-07-25 13:00:00"]).tz_localize("UTC"),
        "result": ["_result", "_result"],
        "table": [0, 0],
        "pH": [7.40, 7.45],
        "COD": [100.0, 89.29],
        "TN": [16.0, 17.06],
        "AN": [2.0, 1.54],
        "TP": [1.5, 1.45],
        "flow": [500.0, 503.2],
        "discharge": [1800.0, 1810.0],
        "suspended_solids": [3.0, 2.99],
    })


def _make_dataset(mock_cls):
    """构造一个喂了假数据的 InfluxDBMonitoringDataset。"""
    from backend.services.influxdb_data_loader import InfluxDBMonitoringDataset
    mock_client = MagicMock()
    mock_client.query_api.return_value.query_data_frame.return_value = _fake_pivoted_df()
    mock_cls.return_value = mock_client
    return InfluxDBMonitoringDataset("http://x", "tok", "org", "bucket")


@patch("backend.services.influxdb_data_loader.InfluxDBClient")
def test_influent_effluent_shape_and_columns(mock_cls):
    ds = _make_dataset(mock_cls)
    inf = ds.influent()
    eff = ds.effluent()
    assert len(inf) == 2 and len(eff) == 2
    # 契约字段(英文键)存在
    for col in ("pH", "COD", "TN", "AN", "TP", "flow", "discharge"):
        assert col in inf.columns, f"influent 缺 {col}"
    assert "suspended_solids" in eff.columns  # 出水独有
    # 元数据列 result/table 被过滤掉
    assert "result" not in inf.columns
    assert "table" not in inf.columns


@patch("backend.services.influxdb_data_loader.InfluxDBClient")
def test_latest_timestamp_and_window(mock_cls):
    ds = _make_dataset(mock_cls)
    latest = ds.latest_timestamp
    assert str(latest).startswith("2026-07-25 13"), latest  # 两侧行最新

    w = ds.window("influent", "24h")
    assert len(w) >= 1
    # window 含 latest,且起点 ≈ latest - 24h
    assert w.index.max() == latest
    assert (latest - w.index.min()) <= pd.Timedelta("25h")


@patch("backend.services.influxdb_data_loader.InfluxDBClient")
def test_empty_bucket_raises_data_unavailable(mock_cls):
    """两侧都无数据时,首次访问抛 DataUnavailableException(不静默返回空)。"""
    from backend.exceptions import DataUnavailableException
    mock_client = MagicMock()
    mock_client.query_api.return_value.query_data_frame.return_value = pd.DataFrame()  # 空
    mock_cls.return_value = mock_client

    from backend.services.influxdb_data_loader import InfluxDBMonitoringDataset
    ds = InfluxDBMonitoringDataset("http://x", "tok", "org", "bucket")
    try:
        ds.influent()
        assert False, "空数据应抛 DataUnavailableException"
    except DataUnavailableException:
        pass


@patch("backend.services.influxdb_data_loader.InfluxDBClient")
def test_values_match_influxdb_canonical_fields(mock_cls):
    """数值与 InfluxDB 契约字段对齐(防 AN/NH3-N 类命名漂移)。"""
    ds = _make_dataset(mock_cls)
    inf = ds.influent()
    last = inf.iloc[-1]
    assert last["pH"] == 7.45
    assert last["COD"] == 89.29
    assert last["AN"] == 1.54  # 氨氮键是 AN(契约),不是 NH3-N
