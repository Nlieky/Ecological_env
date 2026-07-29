#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""报告可视化: 原始数据 + 异常点 → ECharts option 列表(每指标一个子图)。

每图: 进水/出水双线 + 异常 markPoint(按指标+时间匹配)。
供 get_data.py(无异常)和 run_anomaly(带异常)调用,构造 chartData。
"""
from typing import List, Dict, Any, Optional

# 指标 → 中文名（含运行参数）
_INDICATOR_TITLE = {
    "pH": "pH", "COD": "COD", "TN": "总氮", "NH3-N": "氨氮",
    "TP": "总磷", "SS": "悬浮物",
    "flow_rate": "流量", "discharge_volume": "排放量",
}

# 水质指标（默认只画这些，不含流量/排放量等运行参数）
_WATER_QUALITY_INDICATORS = ["pH", "COD", "TN", "NH3-N", "TP", "SS"]


def build_chart_data(records: dict, indicators: Optional[List[str]] = None,
                     anomalies: Optional[List[dict]] = None) -> List[Dict[str, Any]]:
    """records = {influent: [{timestamp, pH, COD,...}], effluent: [...]}
    返回 [{"title": "pH 趋势", "option": <ECharts option>}, ...]

    indicators 不传时，默认只画水质指标(pH/COD/TN/氨氮/TP/SS)，不画流量/排放量。
    """
    infl = records.get("influent") or []
    effl = records.get("effluent") or []

    if indicators is None:
        # 默认只画水质指标（不是运行参数）
        sample = (infl or effl or [{}])[0]
        indicators = [k for k in _WATER_QUALITY_INDICATORS if k in sample]
    else:
        # 调用方指定了指标，用调用方的（但过滤掉不存在的）
        sample = (infl or effl or [{}])[0]
        indicators = [k for k in indicators if k in sample]

    xs_in = [r.get("timestamp", "")[5:16] for r in infl]
    xs_out = [r.get("timestamp", "")[5:16] for r in effl]

    charts = []
    for ind in indicators:
        cn_name = _INDICATOR_TITLE.get(ind, ind)
        title = f"{cn_name} 趋势"
        series_in = {
            "name": f"进水{cn_name}", "type": "line", "smooth": True,
            "data": [_num(r.get(ind)) for r in infl],
            "itemStyle": {"color": "#6366f1"},
        }
        series_out = {
            "name": f"出水{cn_name}", "type": "line", "smooth": True,
            "data": [_num(r.get(ind)) for r in effl],
            "itemStyle": {"color": "#10b981"},
        }

        if anomalies:
            for side, series in (("influent", series_in), ("effluent", series_out)):
                pts = [{"name": (a.get("features") or ["异常"])[0],
                        "xAxis": (a.get("timestamp", "")[5:16]),
                        "yAxis": _num(_val_at(records, side, ind, a.get("timestamp")))}
                       for a in anomalies
                       if a.get("indicator") in (ind, _to_cn(ind)) and a.get("data_type") == side]
                if pts:
                    series["markPoint"] = {"data": pts}

        option = {
            "title": {"text": title, "left": "center", "textStyle": {"fontSize": 14, "fontWeight": "bold"}},
            "tooltip": {"trigger": "axis"},
            "legend": {"data": [f"进水{cn_name}", f"出水{cn_name}"], "top": 24, "textStyle": {"fontSize": 12}},
            "grid": {"top": 50, "left": 50, "right": 20, "bottom": 30},
            "xAxis": {"type": "category", "data": xs_in or xs_out, "axisLabel": {"fontSize": 10}},
            "yAxis": {"type": "value", "name": cn_name, "axisLabel": {"fontSize": 10}},
            "series": [series_in, series_out],
        }
        charts.append({"title": title, "option": option})
    return charts


def _num(v):
    try:
        return None if v is None else round(float(v), 2)
    except (TypeError, ValueError):
        return None


def _val_at(records, side, ind, ts):
    for r in records.get(side, []):
        if r.get("timestamp") == ts:
            return r.get(ind, r.get(_to_en(ind)))
    return None


def _to_cn(ind):
    return {"NH3-N": "氨氮", "TP": "总磷", "SS": "悬浮物"}.get(ind, ind)


def _to_en(ind_cn):
    return {"氨氮": "NH3-N", "总磷": "TP", "悬浮物": "SS"}.get(ind_cn, ind_cn)
