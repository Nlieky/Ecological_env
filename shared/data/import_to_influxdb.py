#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 shared/data/real-time/*.xls 真实监测报表导入 InfluxDB。

链路: parse_report_xls.parse_xls_report 解析双行表头 xls → 字段映射 → 写入 InfluxDB。

配置（优先环境变量，其次项目根 .env，最后默认值）:
  INFLUXDB_TOKEN   InfluxDB all-access token   （必填）
  INFLUXDB_URL     默认 http://localhost:8086
  INFLUXDB_ORG     默认 ecological_env
  INFLUXDB_BUCKET  默认 monitoring-data

Schema:
  measurement = wastewater
  tags        = data_type (influent/effluent), plant_id
  fields      = pH, COD, TN, AN, TP, flow, discharge, suspended_solids
                + 各污染物排放量 *_mass (pH_mass/COD_mass/TN_mass/AN_mass/TP_mass/suspended_solids_mass)
  time        = 报表小时,按 DATA_TIMEZONE(默认北京时间)解释后转 UTC 写入

幂等: 同 measurement+tags+time+field 写入覆盖,可重复运行。
"""
from __future__ import annotations

import glob
import argparse
import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# parse_report_xls 与本脚本同目录
sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse_report_xls import parse_xls_report  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent / "real-time"
DATA_GLOB = str(DATA_DIR / "*.xls")

# parse_report_xls 字段 → InfluxDB field(对齐 monitoring_data_loader 契约键)
FIELD_MAP = {
    "pH": "pH", "COD": "COD", "TN": "TN", "NH3_N": "AN", "TP": "TP",
    "flow_rate": "flow", "discharge_volume": "discharge", "SS": "suspended_solids",
    "pH_mass": "pH_mass", "COD_mass": "COD_mass", "TN_mass": "TN_mass",
    "NH3_N_mass": "AN_mass", "TP_mass": "TP_mass", "SS_mass": "suspended_solids_mass",
}
BATCH = 1000


def _load_dotenv() -> None:
    """轻量加载项目根 .env(不覆盖已有环境变量;不依赖 python-dotenv)。"""
    env = Path(__file__).resolve().parents[2] / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def _to_utc(t_iso: str) -> datetime:
    """Naive report time is a local sampling time, not a UTC instant."""
    value = datetime.fromisoformat(t_iso)
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo(os.environ.get('DATA_TIMEZONE', 'Asia/Shanghai')))
    return value.astimezone(timezone.utc)


def build_points(path: str) -> tuple[str, str, list[Point]]:
    """解析一份 xls,返回 (data_type, plant_id, points)。"""
    plant, dtype, recs = parse_xls_report(path)
    source_hash = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    pts: list[Point] = []
    for r in recs:
        p = Point("wastewater").tag("data_type", dtype).tag("plant_id", plant or "unknown").tag('data_origin', 'real')
        p = p.field('_source_file', Path(path).name).field('_source_sha256', source_hash).field('_ingestion_method', 'file')
        p = p.field('_source_timezone', os.environ.get('DATA_TIMEZONE', 'Asia/Shanghai'))
        for src, dst in FIELD_MAP.items():
            v = r.get(src)
            if v is not None:
                p = p.field(dst, float(v))
        p = p.time(_to_utc(r["time"]))
        pts.append(p)
    return dtype, plant, pts


def main() -> int:
    _load_dotenv()
    parser = argparse.ArgumentParser(description='导入监管下载报表；默认独立真实 bucket，支持只读预检')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--create-bucket', action='store_true')
    parser.add_argument('--bucket', default=os.environ.get('INFLUXDB_REAL_BUCKET', 'monitoring-real'))
    args = parser.parse_args()
    token = os.environ.get("INFLUXDB_TOKEN")
    if not token and not args.dry_run:
        print("ERROR: INFLUXDB_TOKEN 未设置(环境变量或项目根 .env)", file=sys.stderr)
        return 2
    url = os.environ.get("INFLUXDB_URL", "http://localhost:8086")
    org = os.environ.get("INFLUXDB_ORG", "ecological_env")
    bucket = args.bucket
    if bucket == os.environ.get('INFLUXDB_SIMULATION_BUCKET', 'monitoring-simulation'):
        raise ValueError('不能把真实报表导入模拟 bucket')

    files = sorted(glob.glob(DATA_GLOB))
    if not files:
        print(f"ERROR: {DATA_GLOB} 下没有 .xls 文件", file=sys.stderr)
        return 2

    all_points: list[Point] = []
    for f in files:
        dtype, plant, pts = build_points(f)
        print(f"{Path(f).name}\n  data_type={dtype} plant_id={plant} points={len(pts)}")
        all_points.extend(pts)

    if args.dry_run:
        print(f'DRY RUN: {len(files)} files, {len(all_points)} points; timezone={os.environ.get("DATA_TIMEZONE", "Asia/Shanghai")}; target={bucket}; no database writes')
        return 0

    print(f"\n写入 {len(all_points)} points → bucket '{bucket}' (org={org}, url={url}) ...")
    client = InfluxDBClient(url=url, token=token, org=org, timeout=120000)  # 120s,默认10s写大批量会超时
    if args.create_bucket and client.buckets_api().find_bucket_by_name(bucket) is None:
        client.buckets_api().create_bucket(bucket_name=bucket, org=org)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    for i in range(0, len(all_points), BATCH):
        write_api.write(bucket=bucket, record=all_points[i:i + BATCH])
    write_api.close()

    # 验证:按 data_type 统计 COD 字段点数(应 ≈ 每侧小时记录数)
    q_api = client.query_api()
    flux = (
        f'from(bucket: "{bucket}") '
        f'|> range(start: 0) '
        f'|> filter(fn: (r) => r._measurement == "wastewater" and r._field == "COD") '
        f'|> group(columns: ["data_type"]) '
        f'|> count()'
    )
    print("\n验证(每侧 COD 字段点数):")
    for table in q_api.query(flux):
        for rec in table.records:
            print(f"  data_type={rec.values.get('data_type')}  count={rec.get_value()}")

    client.close()
    print("\nDONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
