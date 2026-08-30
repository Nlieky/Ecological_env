#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""污染源在线监测平台导出报表(.xls 实为 xlsx)解析器。

平台(博安达 wryzx)导出的"数据报表"是【双行复合表头】:
  第1行: 监测时间 | 流量(升/秒) | 排放量(吨) | pH值 | · | 化学需氧量 | · | 总氮 | · | 氨氮 | · | 总磷 | ·
  第2行: · | · | · | 浓度(mg/L) | 污染物排放量(kg) | 浓度 | 排放量 | ...   (每指标占两列:浓度+排放量)
  第3行起: 数据(逐小时)

本解析器把它拍平成标准记录，供写入 InfluxDB / 转 CSV:
  {time, plant_id, data_type, flow_rate, discharge_volume,
   pH, COD, TN, NH3_N, TP, <各>_mass}

文件名约定：<厂名><点位>  数据报表.xls
  - 含"进水口" → data_type=influent
  - 含"废水总排口/总排口/排污口/排水口/出水口" → data_type=effluent
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Any

import pandas as pd

# 指标中文名 → 标准英文键
INDICATOR_MAP = {
    "pH值": "pH", "pH": "pH",
    "化学需氧量": "COD",
    "总氮": "TN",
    "氨氮": "NH3_N",
    "总磷": "TP",
    "悬浮物": "SS",
}


def _plant_and_type_from_filename(path) -> Tuple[str, str]:
    """从文件名解析 厂名 + 数据类型(进水/出水)。

    多厂通用规则(按优先级):
    1. plant-hierarchy.yaml 的 report_name_map 显式映射(文件名主体→plant_id)——
       命名不规范的厂在这里登记,最可靠;
    2. 默认启发式:剥掉进出水关键词取前缀(金桥式 "<厂名>废水总排口-沮河")。
       监测点名本身含"排放口"的厂(洗舱站污水排放口)会被剥残,必须走映射表。
    """
    name = Path(path).stem
    name = re.sub(r"\s*数据报表\s*$", "", name).strip()
    # 显式映射表
    mapping = _load_report_name_map()
    if name in mapping:
        pid = mapping[name]
        m_inf = re.search(r"进水口", name)
        m_eff = re.search(r"废水总排口|总排口|排污口|排放口|排水口|出水口", name)
        return pid, ("influent" if m_inf else "effluent" if m_eff else "unknown")
    # 默认启发式
    m_inf = re.search(r"进水口", name)
    m_eff = re.search(r"废水总排口|总排口|排污口|排放口|排水口|出水口", name)
    if m_inf:
        return name[:m_inf.start()].strip().rstrip("-—－· "), "influent"
    if m_eff:
        return name[:m_eff.start()].strip().rstrip("-—－· "), "effluent"
    return name, "unknown"


def _load_report_name_map() -> dict:
    """plant-hierarchy.yaml 的 report_name_map: {报表文件名主体: plant_id}。"""
    p = Path(__file__).resolve().parent / "plant-hierarchy.yaml"
    if not p.exists():
        return {}
    try:
        import yaml
        with open(p, encoding="utf-8") as f:
            return (yaml.safe_load(f) or {}).get("report_name_map", {}) or {}
    except Exception:
        return {}


def _build_columns(header_top, header_sub) -> List[str]:
    """把双行表头拍平成单行列名。指标名按第1行 forward-fill 到第2行的浓度/排放量子列。"""
    cols: List[str] = []
    cur_indicator = None  # 当前指标中文名(pH值/化学需氧量/...)
    for top, sub in zip(header_top, header_sub):
        top_s = "" if pd.isna(top) else str(top).strip()
        sub_s = "" if pd.isna(sub) else str(sub).strip()
        if top_s == "监测时间":
            cols.append("time")
        elif "流量" in top_s:
            cols.append("flow_rate")
        elif "排放量" in top_s and "污染物" not in top_s:
            cols.append("discharge_volume")  # 顶上的"排放量（吨）"=水量
        else:
            # 指标块：top 非空时更新当前指标，sub 决定是浓度还是排放量
            if top_s:
                cur_indicator = top_s
            key = INDICATOR_MAP.get(cur_indicator, cur_indicator or "unknown")
            if "浓度" in sub_s:
                cols.append(key)
            elif "排放量" in sub_s:  # 子行"污染物排放量（千克）"=该指标质量
                cols.append(f"{key}_mass")
            else:
                cols.append(f"col_{len(cols)}")
    return cols


def _parse_time(val) -> str | None:
    """时间 '2026-01-01 00' → ISO '2026-01-01T00:00:00'；解析失败(如'累计值')返回 None。"""
    if pd.isna(val):
        return None
    s = str(val).strip()
    for fmt in ("%Y-%m-%d %H", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            continue
    return None  # '累计值' 等非时间行 → None（调用方跳过）


def parse_xls_report(path) -> Tuple[str, str, List[Dict[str, Any]]]:
    """解析一份 .xls 报表。

    Returns:
        (plant_id, data_type, records) 其中 records 是逐小时的字典列表。
    """
    plant, data_type = _plant_and_type_from_filename(path)
    raw = pd.read_excel(path, sheet_name="数据报表", header=None)
    cols = _build_columns(raw.iloc[0].tolist(), raw.iloc[1].tolist())
    data = raw.iloc[2:].copy()
    data.columns = cols[: len(data.columns)] if len(data.columns) < len(cols) else cols
    data = data.reset_index(drop=True)

    records: List[Dict[str, Any]] = []
    for _, row in data.iterrows():
        t_iso = _parse_time(row.get("time"))
        if not t_iso:
            continue  # 空行 或 '累计值' 汇总行（非时序数据）
        rec: Dict[str, Any] = {"time": t_iso, "plant_id": plant, "data_type": data_type}
        for c in cols:
            if c in ("time",):
                continue
            v = row.get(c)
            if pd.isna(v):
                rec[c] = None
            else:
                try:
                    rec[c] = float(v)
                except (ValueError, TypeError):
                    rec[c] = None  # '/' 等非数值占位符（缺失/无效）→ None
        records.append(rec)
    return plant, data_type, records


def records_to_dataframe(records: List[Dict[str, Any]]) -> pd.DataFrame:
    """记录列表转 DataFrame（便于转 CSV 或核对）。"""
    return pd.DataFrame(records)


if __name__ == "__main__":
    import glob, json

    files = sorted(glob.glob("shared/data/real-time/*.xls"))
    if not files:
        print("shared/data/real-time/ 下没有 .xls，无法测试")
    for f in files:
        plant, dtype, recs = parse_xls_report(f)
        print(f"\n=== {Path(f).name} ===")
        print(f"  plant_id = {plant}")
        print(f"  data_type = {dtype}")
        print(f"  记录数 = {len(recs)}")
        if recs:
            print(f"  时间范围: {recs[0]['time']}  ~  {recs[-1]['time']}")
            print(f"  首条样本: {json.dumps(recs[0], ensure_ascii=False)}")
            print(f"  末条样本: {json.dumps(recs[-1], ensure_ascii=False)}")
