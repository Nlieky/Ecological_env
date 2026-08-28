#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""新监测点接入向导：检查报表名→查 plant-hierarchy.yaml 现状→输出待补配置清单。
参数：--report-name "洗舱站数据报表"  --plant-id 洗舱站污水排放口"""
import argparse
import json
import sys
from pathlib import Path

import yaml

# 注: parents[4] 对应模板库位置层级; 安装到主智能体(skills/<n>/...)改 parents[3]; 安装到子智能体(subagents/<x>/skills/...)改 parents[5]
ROOT = Path(__file__).resolve().parents[4]
YAML_PATH = ROOT / "shared" / "data" / "plant-hierarchy.yaml"


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-name", required=True, help="报表文件名主体")
    ap.add_argument("--plant-id", required=True, help="目标 plant_id（与 InfluxDB 一致的全称）")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    cfg = {}
    if YAML_PATH.exists():
        cfg = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8")) or {}
    plants = []
    for zones in (cfg.get("hierarchy") or cfg).values() if isinstance(cfg, dict) else []:
        if isinstance(zones, dict):
            for plist in zones.values():
                if isinstance(plist, list):
                    plants.extend(plist)
    checks = {
        "层级已含该厂": args.plant_id in plants,
        "别名表已配": args.plant_id in (cfg.get("plant_aliases") or {}),
        "报表映射已配": args.report_name in (cfg.get("report_name_map") or {}),
        "单厂配置已配": args.plant_id in (cfg.get("plant_configs") or {}),
    }
    todo = [k for k, ok in checks.items() if not ok]
    print(json.dumps({
        "summary": f"接入检查完成：{len(checks) - len(todo)}/{len(checks)} 项已就绪" +
                   (f"，待补：{'、'.join(todo)}" if todo else "，可导入数据"),
        "checks": checks, "todo": todo,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
