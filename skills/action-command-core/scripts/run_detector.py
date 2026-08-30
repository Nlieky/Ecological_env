#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""动作指令算法执行脚本——主智能体 run_detector 工具直接 subprocess 调用。

不经 LLM：取数(InfluxDB) + 跑算子 + 输出结果与 actionData，1-3 秒。
用法:
    python run_detector.py --algorithm constant --indicator pH --start 2026-07-14 --end 2026-07-14
输出(stdout, JSON):
    {"status":"completed","anomalies":[...],"summary":{...},
     "actionData":{"cmd":"run_detector","annotations":[...]}}
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# 项目根：向上找含 shared/+workspace/ 的目录(标记法，位置无关)。
# 之前 parents[4] 多退一层到 E:\project 导致 .env 和 shared/ 都找不到。
def _find_project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "shared").is_dir() and (parent / "workspace").is_dir():
            return parent
    return Path(__file__).resolve().parents[3]  # 兜底

_root = _find_project_root()
sys.path.insert(0, str(_root))
if str(Path.cwd()) not in sys.path:
    sys.path.insert(0, str(Path.cwd()))

# 指标名映射:data_result 键名(前端/算子用) ↔ InfluxDB 契约字段
INDICATOR_FIELDS = {"pH": "pH", "COD": "COD", "TN": "TN",
                    "NH3-N": "AN", "TP": "TP", "SS": "suspended_solids"}


def resolve_plant(client, bucket: str, name: str) -> str | None:
    """厂名解析:精确命中→原样;简称→包含匹配唯一命中;歧义/未中→原样(查不到数据自然报错)。"""
    q = client.query_api()
    flux = (f'from(bucket: "{bucket}") |> range(start: 0) '
            f'|> filter(fn: (r) => r._measurement == "wastewater") '
            f'|> group(columns: ["plant_id"]) |> last() |> keep(columns: ["plant_id"])')
    plants = []
    for tb in q.query(flux):
        for rec in tb.records:
            pid = rec.values.get("plant_id")
            if pid and pid not in plants:
                plants.append(pid)
    if name in plants:
        return name
    hits = [p for p in plants if name in p or p in name]
    if len(hits) == 1:
        return hits[0]
    return name  # 0 或多个命中:原样返回,让查询自然失败并提示


def load_series(indicator: str, start: str, end: str, side: str = "effluent",
                plant: str | None = None) -> pd.Series:
    """从 InfluxDB 取指定指标、时间范围的序列。

    side: effluent(默认,大屏各面板主展示侧)/influent/all(进+出拼接)
    plant: 厂(监测点)过滤——多厂库必传,否则混库;洗舱站等无某侧数据的厂自动为空。
    时间语义与看板一致:按 start/end 过滤;fetch 全量后切窗。
    """
    from dotenv import load_dotenv
    load_dotenv(_root / ".env")

    from influxdb_client import InfluxDBClient
    from shared.data.influxdb_query import fetch_wastewater_df

    url = os.environ.get("INFLUXDB_URL", "http://localhost:8086")
    token = os.environ.get("INFLUXDB_TOKEN")
    org = os.environ.get("INFLUXDB_ORG", "ecological_env")
    bucket = os.environ.get("INFLUXDB_BUCKET", "monitoring-data")
    field = INDICATOR_FIELDS.get(indicator, indicator)

    client = InfluxDBClient(url=url, token=token, org=org, timeout=30_000)
    try:
        if plant:
            plant = resolve_plant(client, bucket, plant)  # 简称→全名
        sides = ("influent", "effluent") if side == "all" else (side,)
        frames = []
        for s_side in sides:
            df = fetch_wastewater_df(client, bucket, s_side, [field], plant_id=plant)
            if df is not None and not df.empty and field in df.columns:
                s = df[field].dropna()
                s.index.name = "timestamp"
                frames.append(s)
        if not frames:
            return pd.Series(dtype=float)
        full = pd.concat(frames).sort_index()
        start_dt = pd.to_datetime(start)
        end_dt = pd.to_datetime(end)
        if end_dt == end_dt.normalize():  # end 只给日期 → 补到当天 23:59:59
            end_dt = end_dt + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        return full[(full.index >= start_dt) & (full.index <= end_dt)]
    finally:
        client.close()


def run_algorithm(algorithm: str, series: pd.Series) -> list:
    """跑指定算子,返回异常点列表 [{timestamp,value,type,segment}]。"""
    if algorithm == "constant":
        from shared.operators.specialized.constant_detector import ConstantDetector
        mask, _ = ConstantDetector().detect(series)
        types = ["平稳"]
    elif algorithm == "changepoint":
        from shared.operators.specialized.change_point_detector import ChangePointDetector
        mask, _ = ChangePointDetector().detect(series)
        types = ["突变"]
    elif algorithm == "iforest":
        from sklearn.ensemble import IsolationForest
        vals = series.values.reshape(-1, 1)
        iso = IsolationForest(contamination=0.1, random_state=42).fit(vals)
        mask = iso.predict(vals) == -1
        types = ["离群"]
    else:
        raise ValueError(f"未知算法: {algorithm}")

    out = []
    for idx in np.where(mask)[0]:
        ts = series.index[idx]
        out.append({
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "value": round(float(series.iloc[idx]), 2),
            "type": types[0],
            "segment": "unknown",
        })
    return out


def resolve_window(start: str, end: str) -> tuple[str, str]:
    """锚定数据最新点:start/end 是'now'或空时,取库内最新时间,窗口=最新点往前24h。

    与看板窗口语义一致(现有数据是模拟器持续写入的流,锚当前时刻会拿不到
    最新段;锚数据最新点保证检测的与看板看到的是同一段)。
    """
    if start not in ("now", "", "latest") and end not in ("now", "", "latest"):
        return start, end
    from dotenv import load_dotenv
    load_dotenv(_root / ".env")
    from influxdb_client import InfluxDBClient
    url = os.environ.get("INFLUXDB_URL", "http://localhost:8086")
    token = os.environ.get("INFLUXDB_TOKEN")
    org = os.environ.get("INFLUXDB_ORG", "ecological_env")
    bucket = os.environ.get("INFLUXDB_BUCKET", "monitoring-data")
    client = InfluxDBClient(url=url, token=token, org=org, timeout=30_000)
    try:
        q = client.query_api()
        flux = (f'from(bucket: "{bucket}") |> range(start: 0) '
                f'|> filter(fn: (r) => r._measurement == "wastewater") '
                f'|> group() |> last() |> keep(columns: ["_time"])')
        latest = None
        for tb in q.query(flux):
            for rec in tb.records:
                latest = rec.get_time()
                break
            if latest:
                break
    finally:
        client.close()
    if latest is None:
        return start, end
    s = (latest - pd.Timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    e = latest.strftime("%Y-%m-%d %H:%M:%S")
    return s, e


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--algorithm", required=True,
                        choices=["constant", "changepoint", "iforest"])
    parser.add_argument("--indicator", required=True,
                        help="pH/COD/TN/NH3-N/TP/SS")
    parser.add_argument("--start", default="now", help="开始时间;'now'=锚定数据最新点自动24h")
    parser.add_argument("--end", default="now", help="结束时间;'now'=锚定数据最新点自动24h")
    parser.add_argument("--side", default="effluent", choices=["influent", "effluent", "all"],
                        help="检测侧(默认出水,与大屏面板一致)")
    parser.add_argument("--plant", default=None,
                        help="厂(监测点)过滤;不传=全库混合(单厂遗留);环境变量 DETECTOR_PLANT 兜底")
    args = parser.parse_args()

    try:
        # 环境变量兜底:start/end 是 now/空且带 DETECTOR_START/END(大屏观看窗口)时用之
        # (覆盖 LLM 绕过 handler 直接 terminal 跑脚本的场景)
        if (not args.start or args.start == "now") and os.environ.get("DETECTOR_START"):
            args.start = os.environ["DETECTOR_START"]
        if (not args.end or args.end == "now") and os.environ.get("DETECTOR_END"):
            args.end = os.environ["DETECTOR_END"]
        if not args.plant and os.environ.get("DETECTOR_PLANT"):
            args.plant = os.environ["DETECTOR_PLANT"]
        start, end = resolve_window(args.start, args.end)
        series = load_series(args.indicator, start, end, args.side, plant=args.plant)
        if series.empty or len(series) < 10:
            print(json.dumps({"status": "failed",
                              "error": f"数据不足({len(series)}条),无法检测",
                              "hint": f"窗口 {start} ~ {end} side={args.side}"},
                             ensure_ascii=False))
            return 1

        anomalies = run_algorithm(args.algorithm, series)
        result = {
            "status": "completed",
            "anomalies": anomalies,
            "summary": {"algorithm": args.algorithm,
                        "indicator": args.indicator,
                        "total": len(anomalies),
                        "time_range": f"{start} 至 {end}",
                        "side": args.side,
                        "plant": args.plant or "(全库)"},
            "actionData": {
                "cmd": "run_detector",
                "indicator": args.indicator,
                "side": args.side,
                "plant": args.plant or "",
                "time_range": f"{start}~{end}",
                "annotations": anomalies,
            },
        }
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as e:
        print(json.dumps({"status": "failed", "error": str(e)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
