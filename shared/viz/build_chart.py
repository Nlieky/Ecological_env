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

# 英文指标 → 全中文（异常检测算子用的中文列名，见 run_anomaly_detection_simple._RESULT_FIELD_CN）。
# 异常对象的 indicator 字段可能是英文/短中文/全中文任一种，markPoint 匹配时要都覆盖。
_INDICATOR_CN_FULL = {
    "pH": "pH值", "COD": "化学需氧量浓度（毫克/升）", "TN": "总氮浓度（毫克/升）",
    "NH3-N": "氨氮浓度（毫克/升）", "TP": "总磷浓度（毫克/升）", "SS": "悬浮物浓度（毫克/升）",
    "flow_rate": "流量（升/秒）", "discharge_volume": "排放量（吨）",
}


def build_chart_data(records: dict, indicators: Optional[List[str]] = None,
                     anomalies: Optional[List[dict]] = None,
                     plant: str = "") -> List[Dict[str, Any]]:
    """records = {influent: [{timestamp, pH, COD,...}], effluent: [...]}
    返回 [{"title": "进水水质趋势", "option": <ECharts option>}, ...]
    plant 传了就进 title（多厂对话里图必须标明是哪个厂的数据）。

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

    xs = [_xlab(r.get("timestamp", "")) for r in infl] or [_xlab(r.get("timestamp", "")) for r in effl]

    # 按进出水分图，每张图含多个指标
    plant_prefix = f"{plant} · " if plant else ""
    charts = []
    for side_key, side_label, rows in [("influent", "进水", infl), ("effluent", "出水", effl)]:
        if not rows:
            continue

        title = f"{plant_prefix}{side_label}水质趋势"
        has_ph = "pH" in indicators
        dual_axis = has_ph and len(indicators) > 1   # 真·双轴(pH+浓度)才建两根 yAxis
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
            if dual_axis:
                # 双轴:pH 左(0),浓度右(1)。单轴时不设 yAxisIndex——
                # 之前无条件设 1,单指标(如只画COD)时 yAxis 只有 0 号,前端 "yAxis 1 not found" 全图崩白
                s["yAxisIndex"] = 0 if ind == "pH" else 1

            series.append(s)

        # 异常标注：竖直 markLine（比 markPoint 稳——不受双轴 yAxis 归属、边缘裁切影响）。
        # 在该图(进/出水)的每个异常时刻画一条红色虚线，顶部标异常特征。只标本图所画指标的异常。
        if anomalies and series:
            allowed = {(i, _to_cn(i), _INDICATOR_CN_FULL.get(i, i)) for i in indicators}
            allowed = set().union(*allowed)
            side_anoms = [a for a in anomalies
                          if a.get("data_type") == side_key and a.get("indicator") in allowed]
            if side_anoms:
                ml_data = [{"xAxis": _xlab(a.get("timestamp", "")),
                            "label": {"show": True, "position": "insideEndTop",
                                      "formatter": (a.get("features") or ["异常"])[0]}}
                           for a in side_anoms]
                series[0]["markLine"] = {
                    "symbol": "none",
                    "lineStyle": {"type": "dashed", "color": "#ef4444", "width": 2},
                    "label": {"color": "#ef4444", "fontSize": 10},
                    "data": ml_data,
                }

        option = {
            "title": {"text": title, "left": "center", "textStyle": {"fontSize": 14, "fontWeight": "bold"}},
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}},
            "legend": {"data": [_INDICATOR_TITLE.get(i, i) for i in indicators], "top": 26, "textStyle": {"fontSize": 11}},
            "grid": {"top": 55, "left": 55, "right": dual_axis and 55 or 20, "bottom": 35},
            "xAxis": {"type": "category", "data": xs, "axisLabel": {"fontSize": 10}},
            "yAxis": [],
            "series": series,
        }

        # 双 Y 轴：左 pH(0-14)，右浓度(mg/L)。只在 dual_axis 时两根,否则单轴
        if dual_axis:
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


def _xlab(ts) -> str:
    """时间戳 → x 轴标签 'MM-DD HH:MM'。
    归一化 ISO 的 'T' 分隔（异常时间戳常是 2026-07-25T12:00:00，records 是空格分隔），
    否则 markPoint 的 xAxis 类别对不上曲线 category，标注点定位失败不显示。
    """
    return str(ts).replace("T", " ")[5:16]


def _to_cn(ind):
    return {"NH3-N": "氨氮", "TP": "总磷", "SS": "悬浮物"}.get(ind, ind)
