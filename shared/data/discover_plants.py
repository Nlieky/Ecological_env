#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 InfluxDB 自动发现所有厂(plant_id)，按 plant-hierarchy.yaml 合并出目录树。

发现靠数据（导新厂报表自动出现），分层靠配置（业务知识手写）。
没配置的厂自动落"未分组"，不会丢。
"""
from pathlib import Path
from typing import Dict, List
import sys

# 项目根(标记法：向上找含 shared/+workspace/ 的目录)
for _parent in Path(__file__).resolve().parents:
    if (_parent / "shared").is_dir() and (_parent / "workspace").is_dir():
        if str(_parent) not in sys.path:
            sys.path.insert(0, str(_parent))
        break

_DATA_DIR = Path(__file__).resolve().parent
_HIERARCHY_FILE = _DATA_DIR / "plant-hierarchy.yaml"


def discover_plants() -> List[Dict]:
    """InfluxDB group by plant_id，返回所有有数据的厂。

    返回: [{"plant_id": str, "data_types": ["influent",...],
            "latest_time": str, "point_count": int}]
    """
    from shared.data.influxdb_query import get_client_and_bucket, source_filter
    import json
    client, bucket = get_client_and_bucket()
    flux = (
        f'from(bucket: {json.dumps(bucket)}) '
        f'|> range(start: 0) '
        f'|> filter(fn: (r) => r._measurement == "wastewater"{source_filter(bucket)}) '
        f'|> last() '
        f'|> keep(columns: ["plant_id", "data_type", "_time"])'
        f'|> group(columns: ["plant_id", "data_type"]) '
        f'|> sort(columns: ["_time"]) |> last(column: "_time") '
    )
    try:
        tables = client.query_api().query(flux)
        plants: Dict[str, Dict] = {}
        for table in tables:
            for rec in table.records:
                pid = rec.values.get("plant_id") or "unknown"
                dtype = rec.values.get("data_type") or ""
                ts = str(rec.get_time())
                info = plants.setdefault(pid, {
                    "plant_id": pid, "data_types": [],
                    "latest_time": ts, "point_count": 0,
                })
                if dtype and dtype not in info["data_types"]:
                    info["data_types"].append(dtype)
                if ts > info["latest_time"]:
                    info["latest_time"] = ts
        return sorted(plants.values(), key=lambda p: p["plant_id"])
    finally:
        client.close()


def load_hierarchy() -> Dict:
    """读 plant-hierarchy.yaml，返回 {市: {厂区: [厂名]}}。文件缺失返回空 dict。"""
    if not _HIERARCHY_FILE.exists():
        return {}
    import yaml
    with open(_HIERARCHY_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_tree() -> Dict:
    """发现 ∩ 配置 → 目录树。

    返回: {
      "cities": [{"name": 市, "districts": [{"name": 厂区, "plants": [节点]}]}],
      "ungrouped": [节点]
    }
    节点: {"plant_id", "status": "online"|"offline",
           "data_types", "latest_time", "point_count}
    yaml 顶层保留键(report_name_map/plant_configs/plant_aliases)不参与层级遍历。
    """
    discovered = {p["plant_id"]: p for p in discover_plants()}
    hierarchy = load_hierarchy()
    # 配置型顶层键排除(report_name_map/plant_configs/plant_aliases 是映射不是层级)
    _RESERVED = {"report_name_map", "plant_configs", "plant_aliases"}
    hierarchy = {k: v for k, v in (hierarchy or {}).items() if k not in _RESERVED}

    cities = []
    assigned = set()
    for city, districts in (hierarchy or {}).items():
        if not isinstance(districts, dict):
            continue
        dist_nodes = []
        for dist, plant_names in (districts or {}).items():
            plant_nodes = []
            for name in (plant_names or []):
                assigned.add(name)
                plant_nodes.append(_make_node(name, discovered))
            dist_nodes.append({"name": dist, "plants": plant_nodes})
        cities.append({"name": city, "districts": dist_nodes})
    ungrouped = [_make_node(pid, discovered)
                 for pid in sorted(set(discovered) - assigned)]
    return {"cities": cities, "ungrouped": ungrouped}


def _make_node(pid: str, discovered: Dict[str, Dict]) -> Dict:
    p = discovered.get(pid)
    if p:
        return {**p, "status": "online"}
    return {"plant_id": pid, "status": "offline", "data_types": [],
            "latest_time": "", "point_count": 0}


if __name__ == "__main__":
    import json
    print(json.dumps(build_tree(), ensure_ascii=False, indent=2))
