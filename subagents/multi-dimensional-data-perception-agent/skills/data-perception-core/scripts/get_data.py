#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用数据获取脚本 - 从 InfluxDB 取真实监测数据(2026 真实报表)。

数据源: InfluxDB ``monitoring-data`` bucket (measurement=wastewater)
  - 进水 data_type=influent / 出水 data_type=effluent
  - 由 shared/data/import_to_influxdb.py 从 real-time/*.xls 真实报表导入
  (当阳市金桥污水处理厂, 2026-01-01 ~ 07-25 逐小时)

接口与输出格式与旧 CSV 版完全一致(NH3-N/flow_rate/discharge_volume/SS 字段名不变),
下游异常检测/规则推理零改动。

使用方法:
    python get_data.py --hours 24
    python get_data.py --days 7
    python get_data.py --start "2026-07-20" --end "2026-07-25"
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 项目根(subagents/.../scripts/ 上 5 层),供 import shared.data.influxdb_query
sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

import pandas as pd
from influxdb_client import InfluxDBClient

_MEASUREMENT = "wastewater"

# InfluxDB 契约字段 → 本脚本输出字段(对齐旧 CSV 版字段名,下游零改动)
# pH/COD/TN/TP 名字不变;氨氮/流量/排放量/悬浮物需重命名
_FIELD_RENAME = {
    "AN": "NH3-N",
    "flow": "flow_rate",
    "discharge": "discharge_volume",
    "suspended_solids": "SS",
}
_KEEP_FIELDS = ["pH", "COD", "TN", "AN", "TP", "flow", "discharge", "suspended_solids"]

# 当前工艺的水力停留时间(小时)。标注进 metadata,供下游按需做进水出水时间对齐。
# 数据感知本身不做对齐(零分析)。
_HRT_HOURS = 2


def _load_env() -> None:
    """轻量加载项目根 .env(不覆盖已有环境变量)。"""
    env = Path(__file__).resolve().parents[5] / ".env"  # scripts -> ... -> 项目根
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def _fetch_df(client, bucket: str, data_type: str) -> pd.DataFrame:
    """查一侧数据(委托共享模块)+ 重命名为旧 CSV 键名,下游零改动。"""
    from shared.data.influxdb_query import fetch_wastewater_df, CANONICAL_FIELDS
    df = fetch_wastewater_df(client, bucket, data_type, CANONICAL_FIELDS)
    return df.rename(columns=_FIELD_RENAME)


def _df_to_records(df: pd.DataFrame) -> list:
    """DataFrame → 字典列表(与旧 CSV 版记录形状一致)。"""
    if df is None or df.empty:
        return []
    records = []
    for ts, row in df.iterrows():
        rec = {"timestamp": ts.strftime("%Y-%m-%d %H:%M:%S")}
        for col in row.index:
            v = row[col]
            if pd.isna(v):
                rec[col] = None
            else:
                try:
                    rec[col] = round(float(v), 2)
                except (ValueError, TypeError):
                    rec[col] = None
        records.append(rec)
    return records


def get_data_by_hours(client, bucket, data_type, hours_back=24):
    """最近 N 小时(按数据集最新时间往回取 N 条,1 条/小时)。"""
    df = _fetch_df(client, bucket, data_type)
    return _df_to_records(df.tail(hours_back))


def get_data_by_range(client, bucket, data_type, start_time, end_time):
    """指定时间范围 [start, end]。"""
    df = _fetch_df(client, bucket, data_type)
    if df.empty:
        return []
    start_dt = pd.to_datetime(start_time)
    end_dt = pd.to_datetime(end_time)
    mask = (df.index >= start_dt) & (df.index <= end_dt)
    return _df_to_records(df.loc[mask])


def _compute_missing_points(records, use_range, start, end, hours_back):
    """计算缺失的时间点(期望每小时一条,实际记录里没有的)。

    数据感知只标记缺失(客观事实),不补齐(缺失是异常信号,交下游)。
    """
    if not records:
        return []
    timestamps = [r.get("timestamp") for r in records if r.get("timestamp")]
    if not timestamps:
        return []
    ts = pd.to_datetime(timestamps)
    actual = set(ts)
    if use_range and start and end:
        start_dt = pd.to_datetime(start)
        end_dt = pd.to_datetime(end)
        expected = pd.date_range(start_dt, end_dt, freq="H")
    else:
        latest = ts.max()
        expected = pd.date_range(latest - pd.Timedelta(hours=max(hours_back - 1, 0)),
                                 latest, freq="H")
    missing = [t for t in expected if t not in actual]
    return [t.strftime("%Y-%m-%d %H:%M:%S") for t in missing]


def main():
    _load_env()
    url = os.environ.get("INFLUXDB_URL", "http://localhost:8086")
    token = os.environ.get("INFLUXDB_TOKEN")
    org = os.environ.get("INFLUXDB_ORG", "ecological_env")
    bucket = os.environ.get("INFLUXDB_BUCKET", "monitoring-data")
    if not token:
        print("[ERROR] INFLUXDB_TOKEN 未设置(环境变量或项目根 .env)", file=sys.stderr)
        return 2

    parser = argparse.ArgumentParser(description="获取监测数据(InfluxDB 真实数据)")
    parser.add_argument("--hours", type=int, help="最近N小时")
    parser.add_argument("--days", type=int, help="最近N天")
    parser.add_argument("--start", type=str, help="开始时间 (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="结束时间 (YYYY-MM-DD)")
    args = parser.parse_args()

    task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    hours_back = args.hours or (args.days * 24 if args.days else 24)
    use_range = bool(args.start and args.end)

    client = InfluxDBClient(url=url, token=token, org=org, timeout=30_000)

    def _get(data_type):
        if use_range:
            return get_data_by_range(client, bucket, data_type, args.start, args.end)
        return get_data_by_hours(client, bucket, data_type, hours_back)

    label = f"{args.start} 至 {args.end}" if use_range else f"最近{hours_back}小时"
    print(f"获取 {label} 的数据 (InfluxDB bucket={bucket}) ...")
    influent_data = _get("influent")
    effluent_data = _get("effluent")
    client.close()

    time_range_str = label
    result = {
        "task_id": task_id,
        "status": "completed" if (influent_data or effluent_data) else "failed",
        "result": {
            "influent": influent_data,
            "effluent": effluent_data,
            "metadata": {
                "time_range": time_range_str,
                "indicators": ["pH", "COD", "TN", "NH3-N", "TP", "SS", "flow_rate", "discharge_volume"],
                "hrt_hours": _HRT_HOURS,
                "missing_points": _compute_missing_points(
                    influent_data or effluent_data or [],
                    use_range, args.start if use_range else None,
                    args.end if use_range else None, hours_back),
                "data_source": "influxdb",
            },
        },
        "metadata": {
            "subagent": "multi-dimensional-data-perception-agent",
            "timestamp": datetime.now().isoformat(),
            "llm_driven": True,
        },
    }

    # 保存到会话目录(优先)或子智能体目录(与旧版默认路径一致)
    session_dir = os.environ.get("SESSION_DIR")
    if session_dir:
        output_file = Path(session_dir) / "data_result.json"
    else:
        # parents[3] = subagents/multi-dimensional-data-perception-agent
        output_file = Path(__file__).resolve().parents[3] / "data_result.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 报告可视化: 构造 chartData(无异常标注, 纯数据曲线)
    try:
        from shared.viz.build_chart import build_chart_data
        result["result"]["chartData"] = build_chart_data(
            {"influent": influent_data, "effluent": effluent_data})
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"build_chart 失败(忽略,不影响取数): {e}") if 'logger' in dir() else None

    print(f"\n=== 数据统计 ===")
    if influent_data:
        print(f"进水数据：{len(influent_data)} 条")
        print(f"  时间范围：{influent_data[0]['timestamp']} 至 {influent_data[-1]['timestamp']}")
    else:
        print("进水数据：无")
    if effluent_data:
        print(f"出水数据：{len(effluent_data)} 条")
        print(f"  时间范围：{effluent_data[0]['timestamp']} 至 {effluent_data[-1]['timestamp']}")
    else:
        print("出水数据：无")
    print(f"\n结果已保存到：{output_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
