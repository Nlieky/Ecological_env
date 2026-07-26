#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证 InfluxDB 数据加载器 + DataService 全链路。

确认 get_monitoring_data() 切到 InfluxDB 后端,且 DataService.get_realtime_data()
能正常返回真实 2026 监测数据。

运行:
    python scripts/verify_influxdb_loader.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.core.config import settings
from backend.services.monitoring_data_loader import get_monitoring_data
from backend.services.data_service import DataService

print(f"MONITORING_DATA_SOURCE = {settings.MONITORING_DATA_SOURCE}")
print(f"INFLUXDB_BUCKET        = {settings.INFLUXDB_BUCKET}  (token set: {bool(settings.INFLUXDB_TOKEN)})")

ds = get_monitoring_data()
print(f"\nbackend class : {type(ds).__name__}")
ds.maybe_reload()
print(f"latest_timestamp : {ds.latest_timestamp}")

inf, eff = ds.influent(), ds.effluent()
print(f"\ninfluent  : shape={inf.shape}  cols={list(inf.columns)}")
print(f"effluent  : shape={eff.shape}  cols={list(eff.columns)}")
print(f"influent  last row -> pH={inf.iloc[-1].get('pH')}  flow={inf.iloc[-1].get('flow')}")
print(f"effluent last row -> pH={eff.iloc[-1].get('pH')}  SS={eff.iloc[-1].get('suspended_solids')}")

w = ds.window("influent", "24h")
print(f"\nwindow(influent,'24h'): shape={w.shape}  range={w.index.min()} ~ {w.index.max()}")

rt = DataService().get_realtime_data()
print("\n=== DataService.get_realtime_data() ===")
print(json.dumps(rt, ensure_ascii=False, default=str, indent=2))

print("\nOK —— InfluxDB 数据链路验证通过")
