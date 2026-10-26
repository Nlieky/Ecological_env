#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""共享 InfluxDB 监测数据查询(供 backend loader + 子智能体 canonical 脚本复用)。

消除三处重复的 Flux pivot 查询逻辑:
  - backend/services/influxdb_data_loader.py
  - subagents/multi-dimensional-data-perception-agent/.../get_data.py
  - subagents/anomaly-detection-agent/.../run_anomaly_detection_simple.py

约定:本模块返回【英文契约字段】的 DataFrame(timestamp 索引 +
pH/COD/TN/AN/TP/flow/discharge/suspended_solids);调用方按需 rename:
  - backend loader 直接用
  - get_data → NH3-N / flow_rate / discharge_volume / SS
  - 异常检测  → 中文列名(对齐老 CSV)
"""
from __future__ import annotations

import os
import json
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd
from influxdb_client import InfluxDBClient

_MEASUREMENT = "wastewater"
# InfluxDB 中存储的契约字段(英文键)
CANONICAL_FIELDS: List[str] = ["pH", "COD", "TN", "AN", "TP", "flow", "discharge", "suspended_solids"]


def load_influx_env() -> None:
    """轻量加载项目根 .env(不覆盖已有环境变量)。项目根 = shared/data/ 上两层。"""
    env = Path(__file__).resolve().parents[2] / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def get_client_and_bucket() -> Tuple[InfluxDBClient, str]:
    """从环境变量构造 (InfluxDBClient, bucket)。token 缺失抛 RuntimeError。"""
    load_influx_env()
    url = os.environ.get("INFLUXDB_URL", "http://localhost:8086")
    token = os.environ.get("INFLUXDB_TOKEN")
    org = os.environ.get("INFLUXDB_ORG", "ecological_env")
    bucket = os.environ.get("INFLUXDB_BUCKET", "monitoring-data")
    if not token:
        raise RuntimeError("INFLUXDB_TOKEN 未设置(环境变量或项目根 .env)")
    return InfluxDBClient(url=url, token=token, org=org, timeout=30_000), bucket


def source_filter(bucket: str) -> str:
    """Declared buckets only admit explicitly tagged records; legacy stays unverified."""
    origin = None
    if bucket == os.environ.get('INFLUXDB_REAL_BUCKET', 'monitoring-real'):
        origin = 'real'
    elif bucket == os.environ.get('INFLUXDB_SIMULATION_BUCKET', 'monitoring-simulation'):
        origin = 'simulated'
    return f' and exists r.data_origin and r.data_origin == "{origin}"' if origin else ''


def fetch_wastewater_df(client: InfluxDBClient, bucket: str, data_type: str,
                        fields: Optional[List[str]] = None,
                        plant_id: Optional[str] = None,
                        include_all_fields: bool = False) -> pd.DataFrame:
    """查一侧(进水/出水)数据,pivot 成宽表。

    返回:timestamp 为 DATA_TIMEZONE 本地采样时间的 naive 索引，按时间升序。
    自动丢弃 query_data_frame 附带的 result/table 元数据列;缺失字段自动跳过。

    Args:
        client: InfluxDBClient
        bucket: 桶名
        data_type: "influent" 或 "effluent"
        fields: 要保留的字段(默认 CANONICAL_FIELDS)
        plant_id: 必须显式选择厂(监测点)，不允许混合全库。
    """
    if not plant_id or not plant_id.strip():
        raise ValueError('plant_id must be explicitly selected')
    fields = fields or CANONICAL_FIELDS
    keep = ", ".join(json.dumps(f) for f in fields)
    plant_filter = f'  and r.plant_id == {json.dumps(plant_id, ensure_ascii=False)} '
    flux = (
        f'from(bucket: {json.dumps(bucket)}) '
        f'|> range(start: 0) '
        f'|> filter(fn: (r) => r._measurement == "{_MEASUREMENT}" '
        f'  and r.data_type == {json.dumps(data_type)}{plant_filter}{source_filter(bucket)}) '
        f'|> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value") '
        + ('' if include_all_fields else f'|> keep(columns: ["_time", {keep}])')
    )
    df = client.query_api().query_data_frame(flux)
    if isinstance(df, list):
        tables = [d for d in df if not d.empty]
        df = pd.concat(tables, ignore_index=True) if tables else pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    from shared.data.source_context import data_timezone
    df["_time"] = pd.to_datetime(df["_time"], utc=True).dt.tz_convert(data_timezone()).dt.tz_localize(None)
    df = df.rename(columns={"_time": "timestamp"}).set_index("timestamp").sort_index()
    if include_all_fields:
        excluded = {'result', 'table', 'data_origin', 'data_type', 'plant_id'}
        columns = [c for c in df.columns if not c.startswith('_') and c not in excluded
                   and pd.to_numeric(df[c], errors='coerce').notna().any()]
        return df[columns].apply(pd.to_numeric, errors='coerce')
    return df[[c for c in fields if c in df.columns]]
