#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导出监测数据 CSV。参数与 get_data 同款：--plant 全称 --start/--end 或 --hours"""
import argparse
import csv
import json
import sys
from pathlib import Path

# 注: parents[4] 对应模板库位置层级; 安装到主智能体(skills/<n>/...)改 parents[3]; 安装到子智能体(subagents/<x>/skills/...)改 parents[5]
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from shared.data.influxdb_query import fetch_wastewater_df  # noqa: E402


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plant", default="当阳市金桥污水处理厂一期")
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--hours", type=int, default=24)
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    if args.start and args.end:
        df = fetch_wastewater_df(plant_id=args.plant, start=args.start, end=args.end)
    else:
        df = fetch_wastewater_df(plant_id=args.plant, hours=args.hours)
    out = Path(__file__).resolve().parents[2] / f"export_{args.plant[:8]}_{len(df)}.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(json.dumps({"summary": f"已导出 {len(df)} 行 → {out.name}"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
