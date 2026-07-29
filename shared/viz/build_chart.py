#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""报告可视化: 原始数据 + 异常点 → ECharts option 列表(每指标一个子图)。

每图: 进水/出水双线 + 异常 markPoint(按指标+时间匹配)。
供 get_data.py(无异常)和 run_anomaly(带异常)调用,构造 chartData。
"""
from typing import List, Dict, Any, Optional

_INDICATOR_TITLE = {"pH": "pH", "COD": "COD", "TN": "TN", "NH3-N": "氨氮",
                    "TP": "总磷", "SS": "悬浮物"}


def build_chart_data(records: dict, indicators: Optional[List[str]] = None,
                     anomalies: Optional[List[dict]] = None) -> List[Dict[str, Any]]:
    """records = {influent: [{timestamp, pH, COD,...}], effluent: [...]}
    返回 [{"title": "pH 趋势", "option": <ECharts option>}, ...]
    """
    if indicators is None:
        sample = (records.get("influent") or records.get("effluent") or [{}])[0]
        indicators = [k for k in sample if k != "timestamp"]

    infl = records.get("influent") or []
    effl = records.get("effluent") or []
    xs_in = [r.get("timestamp", "")[5:16] for r in infl]
    xs_out = [r.get("timestamp", "")[5:16] for r in effl]

    charts = []
    for ind in indicators:
        title = f"{_INDICATOR_TITLE.get(ind, ind)} 趋势"
        series_in = {"name": "进水", "type": "line", "smooth": True,
                     "data": [_num(r.get(ind)) for r in infl]}
        series_out = {"name": "出水", "type": "line", "smooth": True,
                      "data": [_num(r.get(ind)) for r in effl]}

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
            "title": {"text": title, "left": "center", "textStyle": {"fontSize": 12}},
            "tooltip": {"trigger": "axis"},
            "legend": {"data": ["进水", "出水"], "top": 18},
            "xAxis": {"type": "category", "data": xs_in or xs_out},
            "yAxis": {"type": "value"},
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
