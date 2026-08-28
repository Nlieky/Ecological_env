#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TODO: 技能脚本说明。参数示例：main.py --plant 当阳市金桥污水处理厂一期 --hours 24"""
import argparse
import json
import sys
from pathlib import Path

RESULT_FILE = Path(__file__).resolve().parents[2] / "skill_result.json"


def parse_args():
    ap = argparse.ArgumentParser(description="TODO")
    ap.add_argument("--plant", default="", help="厂区 plant_id（全称）")
    ap.add_argument("--hours", type=int, default=24, help="时间窗（小时）")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    result = {"status": "completed", "params": vars(args), "data": {}}
    RESULT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"summary": "完成"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
