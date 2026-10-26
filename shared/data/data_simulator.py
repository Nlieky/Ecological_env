#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""监测数据模拟器——往 InfluxDB 持续写入新监测点，让看板变成真·实时流。

场景: 现有数据是历史批次(截至导入时刻)，之后无新点进来，看板轮询永远拉到同一份。
本模拟器按"小时粒度、逐点推进"生成新数据:
  1. 起始 2026-01-01 00:00(与真实报表同一起点);
  2. 追赶阶段: 从起始点到"库内最新时间"这一段按 catchup 秒/点 快速补齐
     (写到与已有数据重合的时间戳会幂等覆盖,不产生冲突);
  3. 实时阶段: 之后每 tick 秒生成"下一个小时"的新点,曲线自然向右生长。

生成模型: 日内周期(早晚高峰) + 随机噪声 + 出水对进水的处理滞后回归。
进水基线取自真实报表均值(2026 上半年 4900+ 点统计),出水按去除率模型生成,
保证模拟数据量级/规律与真实数据一致,演示不穿帮。

用法:
  python shared/data/data_simulator.py                    # 默认: 起始2026-01-01, tick=60s
  python shared/data/data_simulator.py --tick 10          # 演示加速: 10秒一个新点
  python shared/data/data_simulator.py --start "2026-07-26T00:00:00"  # 从指定时间起(不追赶)

配置复用 import_to_influxdb 的 .env 约定(INFLUXDB_TOKEN/URL/ORG/BUCKET)。
Ctrl+C 停止;写入幂等,重启安全。
"""
from __future__ import annotations

import argparse
import math
import os
import random
import signal
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# 项目根(标记法)
for _p in Path(__file__).resolve().parents:
    if (_p / "shared").is_dir() and (_p / "workspace").is_dir():
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))
        break

PLANT_ID = "当阳市金桥污水处理厂一期"  # 与现有库内 plant_id 一致

# ── 生成参数(基线取自真实报表 2026 上半年均值) ──────────────────────────
# (进水基线, 出水基线, 日内振幅比例, 噪声σ比例)
PROFILE = {
    "pH":               (7.38, 7.25, 0.004, 0.004),
    "COD":              (102.86, 27.68, 0.18, 0.08),
    "TN":               (18.84, 7.04, 0.15, 0.08),
    "AN":               (4.26, 0.11, 0.20, 0.10),
    "TP":               (1.64, 0.19, 0.15, 0.10),
    "flow":             (408.23, 397.17, 0.22, 0.05),
    "suspended_solids": (None, 2.0, 0.15, 0.12),  # 仅出水
}
MASS_FIELDS = ["COD", "TN", "AN", "TP", "suspended_solids"]  # 排放量=浓度×流量换算


def _load_dotenv() -> None:
    env = Path(__file__).resolve().parents[2] / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=",1)
        os.environ.setdefault(k.strip(), v.strip())


def diurnal(t: datetime, amp: float) -> float:
    """日内周期: 早晚用水高峰(8点/20点峰值),凌晨低谷。返回 [-1,1] 系数。"""
    h = t.hour + t.minute / 60
    morning = math.exp(-((h - 8.5) ** 2) / 6)
    evening = math.exp(-((h - 20.5) ** 2) / 8)
    night = -0.6 * math.exp(-((h - 3.5) ** 2) / 10)
    return amp * (0.6 * morning + 0.5 * evening + night)


def gen_value(field: str, side: str, t: datetime, rng: random.Random) -> float | None:
    """生成单指标单侧单时刻的值。"""
    base_in, base_out, amp, noise = PROFILE[field]
    base = base_in if side == "influent" else base_out
    if base is None:
        return None
    v = base * (1 + diurnal(t, amp)) * (1 + rng.gauss(0, noise))
    if field == "pH":
        return round(min(max(v, 6.0), 9.0), 2)
    return round(max(v, 0.01), 2)


def build_points_at(t: datetime, rng: random.Random, plant: str = "", sides: tuple = ("influent", "effluent")) -> list[Point]:
    """生成 t 时刻指定厂、指定侧的全部字段点。

    plant: 厂(监测点)id;sides: 该厂实际有的数据侧(洗舱站只有 effluent)。
    """
    flow_in = gen_value("flow", "influent", t, rng)
    flow_out = gen_value("flow", "effluent", t, rng)
    pts: list[Point] = []
    for side in sides:
        p = Point("wastewater").tag("data_type", side).tag("plant_id", plant or PLANT_ID).tag('data_origin', 'simulated')
        p = p.field('_ingestion_method', 'simulator')
        for field in PROFILE:
            v = gen_value(field, side, t, rng)
            if v is not None:
                p = p.field(field, v)
        # 排放量字段(mass): 浓度 × 流量 / 1000 (g/h → kg/h 量级),与真实报表同构
        flow = flow_in if side == "influent" else flow_out
        for field in MASS_FIELDS:
            c = gen_value(field, side, t, rng)
            if c is not None and flow is not None:
                p = p.field(f"{field}_mass", round(c * flow / 1000, 4))
        if side == "influent":  # pH_mass 与真实报表同构存在
            ph = gen_value("pH", side, t, rng)
            if ph is not None:
                p = p.field("pH_mass", round(ph * (flow or 0) / 1000, 4))
        p = p.time(t)
        pts.append(p)
    return pts


def query_latest(client: InfluxDBClient, bucket: str, plant: str | None = None) -> datetime | None:
    """库内(某厂)最新数据时间。"""
    q = client.query_api()
    import json
    from shared.data.influxdb_query import source_filter
    pf = f'  and r.plant_id == {json.dumps(plant, ensure_ascii=False)} ' if plant else ""
    flux = (
        f'from(bucket: {json.dumps(bucket)}) |> range(start: 0) '
        f'|> filter(fn: (r) => r._measurement == "wastewater"{pf}{source_filter(bucket)}) '
        f'|> last() |> keep(columns: ["_time"]) '
        f'|> group() |> sort(columns: ["_time"]) |> last(column: "_time")'
    )
    tables = q.query(flux)
    for tb in tables:
        for rec in tb.records:
            return rec.get_time()
    return None


def discover_plants_sides(client: InfluxDBClient, bucket: str) -> dict[str, tuple]:
    """发现库内所有厂及其有的数据侧——模拟器据此分别为各厂续写。"""
    q = client.query_api()
    import json
    from shared.data.influxdb_query import source_filter
    flux = (
        f'from(bucket: {json.dumps(bucket)}) |> range(start: 0) '
        f'|> filter(fn: (r) => r._measurement == "wastewater"{source_filter(bucket)}) '
        f'|> last() |> keep(columns: ["plant_id", "data_type"]) '
        f'|> group(columns: ["plant_id", "data_type"]) |> limit(n: 1)'
    )
    out: dict[str, set] = {}
    for tb in q.query(flux):
        for rec in tb.records:
            pid = rec.values.get("plant_id") or "unknown"
            out.setdefault(pid, set()).add(rec.values.get("data_type") or "")
    return {pid: tuple(sorted(s)) for pid, s in out.items()}


def main() -> int:
    ap = argparse.ArgumentParser(description="废水监测数据模拟器")
    ap.add_argument("--start", default="2026-01-01T00:00:00",
                    help="模拟起始时间(小时粒度推进,默认 2026-01-01 00:00)")
    ap.add_argument("--tick", type=float, default=60.0,
                    help="实时阶段每点间隔秒(默认60;演示加速可设5-10)")
    ap.add_argument("--catchup-mps", type=float, default=50.0,
                    help="追赶阶段每秒写多少个点(默认50)")
    ap.add_argument("--plant", default="",
                    help="只模拟指定厂(空=库内全部厂各自续写,多厂通用)")
    args = ap.parse_args()

    _load_dotenv()
    token = os.environ.get("INFLUXDB_TOKEN")
    if not token:
        print("ERROR: INFLUXDB_TOKEN 未设置", file=sys.stderr)
        return 2
    url = os.environ.get("INFLUXDB_URL", "http://localhost:8086")
    org = os.environ.get("INFLUXDB_ORG", "ecological_env")
    from shared.data.source_context import simulation_bucket
    bucket = simulation_bucket()
    catalog_bucket = os.environ.get('INFLUXDB_REAL_BUCKET', 'monitoring-real')

    start = datetime.strptime(args.start, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    rng = random.Random(20260101)  # 固定种子,重启续跑不跳变
    running = True

    def _stop(*_):
        nonlocal running
        running = False
        print("\n[simulator] 收到停止信号,退出")
    signal.signal(signal.SIGINT, _stop)
    try:
        signal.signal(signal.SIGTERM, _stop)
    except (AttributeError, ValueError):
        pass  # Windows 下 SIGTERM 可能不可用

    client = InfluxDBClient(url=url, token=token, org=org)
    # InfluxDB 可能还没就绪(随系统启动顺序不定)——健康检查重试最多 60s 再继续
    for _ in range(30):
        try:
            client.health()
            break
        except Exception:
            print("[simulator] 等待 InfluxDB 就绪...", flush=True)
            time.sleep(2)
    if client.buckets_api().find_bucket_by_name(bucket) is None:
        client.buckets_api().create_bucket(bucket_name=bucket, org=org)
    write = client.write_api(write_options=SYNCHRONOUS)

    # ── 多厂:发现库内全部厂,各厂独立游标+各自的 sides(洗舱站只有 effluent) ──
    plants_sides = ({args.plant: ("influent", "effluent")}
                    if args.plant else discover_plants_sides(client, catalog_bucket))
    if not plants_sides:
        plants_sides = {PLANT_ID: ("influent", "effluent")}
    cursors: dict[str, datetime] = {}
    now0 = datetime.now(timezone.utc)
    for pid, sides in plants_sides.items():
        latest = query_latest(client, bucket, pid)
        cur = start
        if latest is not None and latest >= start:
            cur = max(latest + timedelta(hours=1), now0)
        elif latest is not None:
            cur = latest + timedelta(hours=1)
        cursors[pid] = cur
        print(f"[simulator] {pid}: sides={'+'.join(sides)} 库内至 {latest or '无'} → 续写起点 {cur:%m-%d %H:%M} UTC")

    # ── 追赶阶段: 各厂快进到当前时刻 ──
    now = datetime.now(timezone.utc)
    pending = {pid: c for pid, c in cursors.items() if c <= now}
    if pending:
        total = sum(int((now - c).total_seconds() // 3600) + 1 for c in pending.values())
        print(f"[simulator] 追赶: {len(pending)} 厂共 {total} 小时({args.catchup_mps} 点/秒)")
        while pending and running:
            batch_t0 = time.monotonic()
            for _ in range(int(args.catchup_mps)):
                if not pending:
                    break
                pid = next(iter(pending))
                sides = plants_sides[pid]
                write.write(bucket=bucket, org=org,
                            record=build_points_at(cursors[pid], rng, pid, sides))
                cursors[pid] += timedelta(hours=1)
                if cursors[pid] > now:
                    del pending[pid]
            elapsed = time.monotonic() - batch_t0
            if elapsed < 1:
                time.sleep(1 - elapsed)
        print(f"[simulator] 追赶完成,进入实时阶段(每 {args.tick}s 一个新点)")

    # ── 实时阶段: 每 tick 秒各厂推进一个小时的新点 ──
    while running:
        try:
            for pid, sides in plants_sides.items():
                write.write(bucket=bucket, org=org,
                            record=build_points_at(cursors[pid], rng, pid, sides))
                cursors[pid] += timedelta(hours=1)
            local = cursors[next(iter(plants_sides))] + timedelta(hours=8)  # 北京时间显示
            print(f"[simulator] 写入 {len(plants_sides)} 厂 → 北京 {local:%m-%d %H:%M} → 下一批 {args.tick}s 后", flush=True)
            time.sleep(args.tick)
        except KeyboardInterrupt:
            _stop()
        except Exception as e:
            print(f"[simulator] 写入异常(重试): {e}", file=sys.stderr)
            time.sleep(3)

    write.close()
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
