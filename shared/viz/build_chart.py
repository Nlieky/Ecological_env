#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""报告可视化: 原始数据 + 异常点 → ECharts option 列表。

布局：按进出水分图（进水一张、出水一张），每张图含多个指标线（双 Y 轴解决量纲差异）。
pH 用左轴（0-14），其他浓度指标用右轴。
供 get_data.py(无异常)和 run_anomaly(带异常)调用。
"""
from typing import List, Dict, Any, Optional

# 指标 → 中文名
_INDICATOR_TITLE = {
    "pH": "pH", "COD": "COD", "TN": "总氮", "NH3-N": "氨氮",
    "TP": "总磷", "SS": "悬浮物",
    "flow_rate": "流量", "discharge_volume": "排放量",
}

# 水质指标（默认只画这些）
_WATER_QUALITY_INDICATORS = ["pH", "COD", "TN", "NH3-N", "TP", "SS"]

# 线条颜色（按指标分配）
_INDICATOR_COLORS = {
    "pH": "#6366f1", "COD": "#f59e0b", "TN": "#10b981",
    "NH3-N": "#ef4444", "TP": "#8b5cf6", "SS": "#06b6d4",
}
_DEFAULT_COLOR = "#6b7280"


def build_chart_data(records: dict, indicators: Optional[List[str]] = None,
                     anomalies: Optional[List[dict]] = None) -> List[Dict[str, Any]]:
    """records = {influent: [{timestamp, pH, COD,...}], effluent: [...]}
    返回 [{"title": "进水水质趋势", "option": <ECharts option>}, {"title": "出水水质趋势", ...}]

    布局：按进出水分图（对比性强），每张图含多个指标线。
    indicators 不传时默认画水质 6 项；传了就只画指定的。
    """
    infl = records.get("influent") or []
    effl = records.get("effluent") or []

    if indicators is None:
        sample = (infl or effl or [{}])[0]
        indicators = [k for k in _WATER_QUALITY_INDICATORS if k in sample]
    else:
        sample = (infl or effl or [{}])[0]
        indicators = [k for k in indicators if k in sample]

    xs = [r.get("timestamp", "")[5:16] for r in infl] or [r.get("timestamp", "")[5:16] for r in effl]

    # 按进出水分图，每张图含多个指标
    charts = []
    for side_key, side_label, rows in [("influent", "进水", infl), ("effluent", "出水", effl)]:
        if not rows:
            continue

        title = f"{side_label}水质趋势"
        has_ph = "pH" in indicators
        series = []
        for ind in indicators:
            cn = _INDICATOR_TITLE.get(ind, ind)
            color = _INDICATOR_COLORS.get(ind, _DEFAULT_COLOR)
            s = {
                "name": cn,
                "type": "line",
                "smooth": True,
                "symbol": "none",          # 不显示数据点（hover 时 tooltip 显示值）
                "sampling": "lttb",        # 降采样，减少渲染负担
                "data": [_num(r.get(ind)) for r in rows],
                "lineStyle": {"width": 2, "color": color},
                "itemStyle": {"color": color},
            }
            if has_ph and ind == "pH":
                s["yAxisIndex"] = 0   # pH 用左轴
            else:
                s["yAxisIndex"] = 1   # 浓度用右轴

            # 异常 markPoint
            if anomalies:
                pts = [{"name": (a.get("features") or ["异常"])[0],
                        "xAxis": (a.get("timestamp", "")[5:16]),
                        "yAxis": _num(_val_at(records, side_key, ind, a.get("timestamp")))}
                       for a in anomalies
                       if a.get("indicator") in (ind, _to_cn(ind)) and a.get("data_type") == side_key]
                if pts:
                    s["markPoint"] = {"data": pts, "symbolSize": 45}

            series.append(s)

        option = {
            "title": {"text": title, "left": "center", "textStyle": {"fontSize": 14, "fontWeight": "bold"}},
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}},
            "legend": {"data": [_INDICATOR_TITLE.get(i, i) for i in indicators], "top": 26, "textStyle": {"fontSize": 11}},
            "grid": {"top": 55, "left": 55, "right": has_ph and len(indicators) > 1 and 55 or 20, "bottom": 35},
            "xAxis": {"type": "category", "data": xs, "axisLabel": {"fontSize": 10}},
            "yAxis": [],
            "series": series,
        }

        # 双 Y 轴：左 pH(0-14)，右浓度(mg/L)
        if has_ph and len(indicators) > 1:
            option["yAxis"] = [
                {"type": "value", "name": "pH", "position": "left", "min": 0, "max": 14,
                 "axisLabel": {"fontSize": 10}, "nameTextStyle": {"fontSize": 11}},
                {"type": "value", "name": "mg/L", "position": "right",
                 "axisLabel": {"fontSize": 10}, "nameTextStyle": {"fontSize": 11}},
            ]
        else:
            unit = "pH" if indicators == ["pH"] else "mg/L"
            option["yAxis"] = [{"type": "value", "name": unit, "axisLabel": {"fontSize": 10}}]

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
