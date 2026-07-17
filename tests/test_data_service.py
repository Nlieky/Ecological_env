"""数据服务层测试"""

import pytest
from backend.services.data_service import DataService
from backend.services.monitoring_data_loader import RESPONSE_INDICATORS


def _is_num_or_none(v):
    return v is None or isinstance(v, (int, float))


def test_data_service_init():
    """测试数据服务初始化"""
    service = DataService()
    assert service is not None


def test_get_realtime_data():
    """测试获取实时数据（真实数据）"""
    service = DataService()
    result = service.get_realtime_data()
    assert "timestamp" in result
    assert "influent" in result
    assert "effluent" in result

    # 时间戳带时区（Z）
    assert result["timestamp"].endswith("Z")
    # 指标集合为 {pH, COD, TN, TP}
    assert set(result["influent"].keys()) == set(RESPONSE_INDICATORS)
    assert set(result["effluent"].keys()) == set(RESPONSE_INDICATORS)
    # pH 取值合理（0~14 或 None）
    for side in ("influent", "effluent"):
        ph = result[side]["pH"]
        assert ph is None or 0 <= ph <= 14
    # flow_rate、quality_score 类型与范围
    assert isinstance(result["flow_rate"], (int, float))
    assert 0 <= result["quality_score"] <= 1


def test_get_data_quality():
    """测试获取数据质量（真实数据）"""
    service = DataService()
    result = service.get_data_quality()
    assert "completeness_rate" in result
    assert "missing_data_count" in result
    assert "anomaly_count" in result
    assert "last_update" in result
    assert 0 <= result["completeness_rate"] <= 1
    assert isinstance(result["missing_data_count"], int)
    assert isinstance(result["anomaly_count"], int)
    assert result["last_update"].endswith("Z")


def test_get_data_quality_window_monotonic():
    """更长时间窗口的缺失/异常计数应不少于短窗口"""
    service = DataService()
    short = service.get_data_quality("24h")
    long = service.get_data_quality("7d")
    assert long["missing_data_count"] >= short["missing_data_count"]
    assert long["anomaly_count"] >= short["anomaly_count"]


def test_invalid_time_range_falls_back():
    """无效 time_range 应回退到 24h（不报错）"""
    service = DataService()
    result = service.get_data_quality("garbage")
    assert 0 <= result["completeness_rate"] <= 1


def test_query_history_data_basic():
    """历史查询：记录非空，含 influent/effluent 子结构"""
    service = DataService()
    result = service.query_history_data("24h", None, "raw", 1, 50)
    assert result["total_count"] > 0
    assert len(result["records"]) > 0
    rec = result["records"][0]
    assert "timestamp" in rec and rec["timestamp"].endswith("Z")
    assert "influent" in rec and "effluent" in rec
    assert result["page"] == 1 and result["page_size"] == 50


def test_query_history_pagination():
    """分页：page_size 限制返回条数，total_count 反映全量"""
    service = DataService()
    result = service.query_history_data("24h", None, "raw", 1, 5)
    assert result["page_size"] == 5
    assert len(result["records"]) <= 5
    assert result["total_count"] >= len(result["records"])


def test_query_history_daily_aggregation():
    """daily 聚合：记录数 == 窗口内天数"""
    service = DataService()
    result = service.query_history_data("7d", None, "daily", 1, 100)
    # 7d 窗口含端点共 8 天
    assert result["total_count"] == 8


def test_query_history_indicator_filter():
    """指标筛选：记录子结构只包含请求的指标"""
    service = DataService()
    result = service.query_history_data("24h", "pH,COD", "raw", 1, 5)
    rec = result["records"][0]
    assert set(rec["influent"].keys()) == {"pH", "COD"}


def test_get_aggregated_data():
    """聚合统计：周期回显，metrics 为列表，data 含 influent/effluent 系列"""
    service = DataService()
    result = service.get_aggregated_data("daily", "avg,max,min")
    assert result["period"] == "daily"
    assert result["metrics"] == ["avg", "max", "min"]
    assert "influent" in result["data"] and "effluent" in result["data"]
    assert len(result["data"]["influent"]) > 0
    # 任一非空桶应含 pH_avg / COD_max 形式的键
    bucket = next(b for b in result["data"]["influent"].values() if b)
    assert any(k.startswith("pH_") for k in bucket)
    assert any(k.endswith("_max") for k in bucket)


def test_get_aggregated_data_unknown_metrics_dropped():
    """未知 metric token 被丢弃，但不破坏结构"""
    service = DataService()
    result = service.get_aggregated_data("daily", "avg,bogus,min")
    assert result["metrics"] == ["avg", "min"]
