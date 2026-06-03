# tests/subagents/test_report_generator.py
import pytest
from pathlib import Path
import sys

# Get the project root (Ecological_env directory)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "subagents" / "disposition-execution-agent" / "skills" / "disposition-execution-core" / "scripts"))

from report_generator import AlertReport, SummaryReport, TrendReport


def test_alert_report_creation():
    """测试 AlertReport 创建"""
    report = AlertReport(
        report_id="RPT-001",
        generated_at="2026-06-01T10:00:00",
        alert_level="serious",
        violation_type="稀释排放",
        confidence=0.92,
        data_traceback={},
        inspection_points=[],
        legal_references=[],
        recommended_actions=[]
    )

    assert report.report_id == "RPT-001"
    assert report.alert_level == "serious"
    assert report.confidence == 0.92


def test_summary_report_creation():
    """测试 SummaryReport 创建"""
    report = SummaryReport(
        report_id="SUM-001",
        generated_at="2026-06-01T10:00:00",
        time_range=("2026-06-01 00:00:00", "2026-06-01 23:59:59"),
        total_alerts=10,
        by_level={"general": 5, "moderate": 3, "serious": 2},
        by_type={"插瓶干扰": 3, "稀释排放": 4, "人工拟合": 3},
        top_enterprises=[]
    )

    assert report.total_alerts == 10
    assert report.by_level["serious"] == 2


def test_trend_report_creation():
    """测试 TrendReport 创建"""
    report = TrendReport(
        report_id="TREND-001",
        generated_at="2026-06-01T10:00:00",
        time_range=("2026-06-01 00:00:00", "2026-06-01 23:59:59"),
        indicators=["COD", "TN", "TP"],
        trend_data={},
        analysis="无明显趋势",
        anomalies=[]
    )

    assert len(report.indicators) == 3
    assert report.analysis == "无明显趋势"


def test_generate_alert_report():
    """测试生成预警报告"""
    from report_generator import ReportGenerator

    generator = ReportGenerator()

    work_order = {
        "id": "WO-20260601-001",
        "alert_level": "serious",
        "violation_type": "稀释排放",
        "confidence": 0.92,
        "data_traceback": {
            "time_range": {"start": "2026-06-01 02:00", "end": "2026-06-01 04:00"},
            "affected_indicators": ["COD", "TN", "TP"]
        },
        "inspection_points": [
            {"location": "废水排放口", "action": "采集出水样品"}
        ],
        "legal_references": ["《水污染防治法》第XX条"],
        "recommended_actions": ["立即启动执法程序"]
    }

    context = {
        "enterprise_name": "测试企业"
    }

    report = generator.generate_alert_report(work_order, context)

    assert isinstance(report, AlertReport)
    assert report.report_id.startswith("ALERT-")
    assert report.alert_level == "serious"
    assert report.violation_type == "稀释排放"
    assert len(report.legal_references) > 0


def test_generate_summary_report():
    """测试生成汇总报告"""
    from report_generator import ReportGenerator

    generator = ReportGenerator()

    work_orders = [
        {"alert_level": "general", "violation_type": "插瓶干扰", "confidence": 0.5},
        {"alert_level": "moderate", "violation_type": "稀释排放", "confidence": 0.7},
        {"alert_level": "serious", "violation_type": "人工拟合", "confidence": 0.9},
        {"alert_level": "serious", "violation_type": "稀释排放", "confidence": 0.85}
    ]

    time_range = ("2026-06-01 00:00:00", "2026-06-01 23:59:59")

    report = generator.generate_summary_report(work_orders, time_range)

    assert isinstance(report, SummaryReport)
    assert report.total_alerts == 4
    assert report.by_level["general"] == 1
    assert report.by_level["serious"] == 2
    assert report.by_type["稀释排放"] == 2
    assert report.report_id.startswith("SUMMARY-")


def test_generate_trend_report():
    """测试生成趋势报告"""
    from report_generator import ReportGenerator

    generator = ReportGenerator()

    # 模拟历史数据
    historical_data = [
        {"监测时间": "2026-06-01 00:00", "COD": 45, "TN": 15, "TP": 3},
        {"监测时间": "2026-06-01 06:00", "COD": 50, "TN": 18, "TP": 4},
        {"监测时间": "2026-06-01 12:00", "COD": 48, "TN": 16, "TP": 3.5},
        {"监测时间": "2026-06-01 18:00", "COD": 52, "TN": 20, "TP": 5}
    ]

    indicators = ["COD", "TN"]
    time_range = ("2026-06-01 00:00:00", "2026-06-01 23:59:59")

    report = generator.generate_trend_report(historical_data, indicators, time_range)

    assert isinstance(report, TrendReport)
    assert report.report_id.startswith("TREND-")
    assert len(report.indicators) == 2
    assert "COD" in report.trend_data
    assert "TN" in report.trend_data
    assert report.analysis != ""
    assert isinstance(report.anomalies, list)
