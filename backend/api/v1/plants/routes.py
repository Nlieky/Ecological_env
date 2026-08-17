"""多厂区仪表盘 API——厂目录树 + 单厂看板数据（真实 InfluxDB 数据）。

与旧 mock 的 /api/realtime/plants 区分：这里是真实数据，按 plant_id tag 过滤。
"""
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["多厂区仪表盘"])


@router.get("/plants/tree")
async def get_plant_tree():
    """厂目录树：市→厂区→厂，从数据自动发现+配置分层。"""
    try:
        from shared.data.discover_plants import build_tree
        return {"success": True, "data": build_tree()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"构建厂目录树失败: {e}")


# 厂看板指标定义：(显示名, InfluxDB字段, 出水限值, 单位)
_DASH_INDICATORS = [
    ("pH", "pH", (6.0, 9.0), ""),
    ("COD", "COD", 100.0, "mg/L"),
    ("TN", "TN", 20.0, "mg/L"),
    ("氨氮", "AN", 15.0, "mg/L"),
    ("TP", "TP", 1.0, "mg/L"),
    ("SS", "suspended_solids", None, "mg/L"),
]


@router.get("/plants/{plant_id}/dashboard")
async def get_plant_dashboard(plant_id: str, hours: int = 24):
    """单厂看板数据包：各指标当前值+趋势+状态。hours 控制趋势窗口（默认24）。"""
    try:
        from datetime import datetime, timedelta
        import pandas as pd
        from shared.data.influxdb_query import get_client_and_bucket

        client, bucket = get_client_and_bucket()
        start = (datetime.utcnow() - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
        plant_id = plant_id.replace('"', '')  # 防 flux 注入：去掉引号

        def _flux(data_type: str) -> str:
            return (
                f'from(bucket: "{bucket}") '
                f'|> range(start: {start}) '
                f'|> filter(fn: (r) => r._measurement == "wastewater" '
                f'  and r.plant_id == "{plant_id}" '
                f'  and r.data_type == "{data_type}") '
                f'|> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")'
            )

        try:
            dfs = {}
            for side in ("influent", "effluent"):
                df = client.query_api().query_data_frame(_flux(side))
                if isinstance(df, list):
                    df = pd.concat([d for d in df if not d.empty], ignore_index=True) if df else pd.DataFrame()
                dfs[side] = df if df is not None and not df.empty else pd.DataFrame()
        finally:
            client.close()

        indicators = {}
        for label, field, limit, unit in _DASH_INDICATORS:
            item = {"label": label, "unit": unit,
                    "limit": limit, "influent": None, "effluent": None,
                    "status": "nodata", "series": {"influent": [], "effluent": []}}
            for side in ("influent", "effluent"):
                df = dfs.get(side, pd.DataFrame())
                if field in df.columns:
                    series = df[["_time", field]].dropna()
                    item["series"][side] = [
                        {"time": str(r["_time"])[:19].replace("T", " "),
                         "value": round(float(r[field]), 2)}
                        for _, r in series.iterrows()
                    ]
                    if not series.empty:
                        last = round(float(series.iloc[-1][field]), 2)
                        item[side] = last
            # 状态：有出水值→按限值判 normal/warning；无限值或无数据→normal/nodata
            eff = item["effluent"]
            if eff is not None and limit is not None:
                lo, hi = limit if isinstance(limit, tuple) else (None, limit)
                bad = (lo is not None and eff < lo) or (hi is not None and eff > hi)
                item["status"] = "warning" if bad else "normal"
            elif eff is not None:
                item["status"] = "normal"
            indicators[field] = item

        return {"success": True, "data": {
            "plant_id": plant_id,
            "window_hours": hours,
            "indicators": indicators,
            "influent_points": len(dfs.get("influent", pd.DataFrame())),
            "effluent_points": len(dfs.get("effluent", pd.DataFrame())),
        }}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"厂看板数据获取失败: {e}")
