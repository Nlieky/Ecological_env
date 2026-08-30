"""系统态势 API——部署系统运维状态监控 + 态势历史。

参考 aiops.hgdz.cn 的「系统态势/态势历史」两个一级入口：
- /system/status  : 当前态势快照（各厂数据新鲜度、服务健康、累计处理量/告警量）
- /system/history : 按天聚合的历史态势（点数、进/出水均值、超标次数）
"""
from fastapi import APIRouter
from datetime import datetime

router = APIRouter(tags=["系统态势"])

# 出水超标限值（与 plants dashboard 一致）
_EFF_LIMITS = {"COD": 100.0, "TN": 20.0, "AN": 15.0, "TP": 1.0}


@router.get("/system/status")
async def get_system_status():
    """系统当前态势快照。"""
    plants = []
    try:
        from shared.data.discover_plants import discover_plants
        for p in discover_plants():  # 返回 list[dict]
            plants.append({
                "plant_id": p.get("plant_id", ""),
                "latest_time": str(p.get("latest_time", ""))[:16].replace("T", " "),
                "status": "online",  # 能被发现=有数据
                "data_types": sorted(p.get("data_types", [])),
            })
    except Exception:
        pass  # InfluxDB 不可达时仍返回服务态势部分

    # 服务健康
    services = [{"name": "backend", "title": "后端 API", "status": "up"}]
    try:
        from backend.core.config import settings
        import httpx
        agent_ok = False
        try:
            async with httpx.AsyncClient(timeout=3) as hc:
                r = await hc.get(f"{settings.AGENT_SERVICE_URL}/health")
                agent_ok = r.status_code == 200
        except Exception:
            agent_ok = False
        services.insert(1, {"name": "agent", "title": "智能体服务",
                            "status": "up" if agent_ok else "down"})
    except Exception:
        pass
    try:
        from shared.data.influxdb_query import get_client_and_bucket
        get_client_and_bucket()[0].close()
        services.append({"name": "influxdb", "title": "时序数据库", "status": "up"})
    except Exception:
        services.append({"name": "influxdb", "title": "时序数据库", "status": "down"})

    # 累计处理量/异常量（prometheus 计数器快照，进程生命周期内累计）
    counters = {}
    try:
        from backend.metrics.definitions import (
            wastewater_data_processed_total,
            wastewater_anomaly_detected_total,
        )
        counters = {
            "data_processed_total": wastewater_data_processed_total._value.get(),
            "anomaly_detected_total": wastewater_anomaly_detected_total._value.get(),
        }
    except Exception:
        counters = {}

    return {"success": True, "data": {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "plants": plants,
        "services": services,
        "counters": counters,
    }}


@router.get("/system/history")
async def get_system_history(days: int = 30):
    """按天聚合的历史态势：每天监测点数、进/出水均值、超标次数。"""
    import pandas as pd
    from shared.data.influxdb_query import get_client_and_bucket

    client, bucket = get_client_and_bucket()
    try:
        q = (
            f'from(bucket: "{bucket}") |> range(start: 0) '
            f'|> filter(fn: (r) => r._measurement == "wastewater") '
            f'|> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")'
        )
        df = client.query_api().query_data_frame(q)
        if isinstance(df, list):
            df = pd.concat([d for d in df if not d.empty], ignore_index=True) if df else pd.DataFrame()
        if df is None or df.empty:
            return {"success": True, "data": []}

        df["_time"] = pd.to_datetime(df["_time"])
        df["day"] = df["_time"].dt.strftime("%Y-%m-%d")
        fields = [f for f in ("pH", "COD", "TN", "AN", "TP", "suspended_solids") if f in df.columns]

        rows = []
        for day, g in df.groupby("day"):
            row = {"day": day, "points": int(len(g)),
                   "influent_points": 0, "effluent_points": 0,
                   "exceed": 0, "metrics": {}}
            if "data_type" in g.columns:
                for side in ("influent", "effluent"):
                    sub = g[g["data_type"] == side]
                    row[f"{side}_points"] = int(len(sub))
                    if len(sub):
                        row["metrics"][side] = {
                            f: round(float(sub[f].dropna().mean()), 2)
                            for f in fields if sub[f].notna().any()
                        }
                eff = g[g["data_type"] == "effluent"]
                for f, lim in _EFF_LIMITS.items():
                    if f in eff.columns:
                        row["exceed"] += int((eff[f].dropna() > lim).sum())
            rows.append(row)

        rows.sort(key=lambda r: r["day"])
        if days and days > 0:
            rows = rows[-days:]
        return {"success": True, "data": rows}
    finally:
        client.close()
