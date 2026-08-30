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


# 厂看板指标默认定义：(字段, 显示名, 出水限值, 单位)——**动态发现**的兜底顺序与默认限值。
# 多厂通用性:各厂指标集不同(洗舱站无SS、未来厂可能加石油类),看板按该厂实际
# 出现的字段渲染,这里只提供显示名/限值/单位映射 + 排序;未知字段也能显示(用字段名)。
_INDICATOR_META = {
    "pH": ("pH", (6.0, 9.0), ""),
    "COD": ("COD", 100.0, "mg/L"),
    "TN": ("总氮", 20.0, "mg/L"),
    "AN": ("氨氮", 15.0, "mg/L"),
    "TP": ("总磷", 1.0, "mg/L"),
    "suspended_solids": ("悬浮物", None, "mg/L"),
    "flow": ("流量", None, "m³/h"),
    "discharge": ("累计排放量", None, "m³"),
}
_INDICATOR_ORDER = ["pH", "COD", "TN", "AN", "TP", "suspended_solids", "flow", "discharge"]

# per-plant 覆盖(plant-hierarchy.yaml plant_configs.limits),未配置用上面的默认
_YAML_PATH = None


def _plant_overrides(plant_id: str) -> dict:
    """读 plant-hierarchy.yaml 的 plant_configs;失败返回空(全走默认)。"""
    global _YAML_PATH
    if _YAML_PATH is None:
        from pathlib import Path
        p = Path(__file__).resolve().parents[4] / "shared" / "data" / "plant-hierarchy.yaml"
        _YAML_PATH = p if p.exists() else False
    if not _YAML_PATH:
        return {}
    try:
        import yaml
        with open(_YAML_PATH, encoding="utf-8") as f:
            cfg = (yaml.safe_load(f) or {}).get("plant_configs", {})
        return cfg.get(plant_id) or {}
    except Exception:
        return {}


@router.get("/plants/{plant_id}/dashboard")
async def get_plant_dashboard(plant_id: str, hours: int = 24, anchor: str | None = None):
    """单厂看板数据包：各指标当前值+趋势+状态。

    hours 控制趋势窗口（默认24）。窗口锚定该厂**数据最新时间点**而非当前时刻——
    现有数据是历史批次（2026-01~07），锚 utcnow 会导致窗口内无数据、曲线全空。
    anchor: 任意开播日期(YYYY-MM-DD)。给了 anchor 就不做"最新点往前 N 小时",
    而是 [anchor 00:00 起 7 天] 的段数据(流式回放"任意时间点开播"用),不足7天给到数据末尾。
    """
    try:
        from datetime import datetime, timedelta, timezone
        import pandas as pd
        from shared.data.influxdb_query import get_client_and_bucket

        client, bucket = get_client_and_bucket()
        plant_id = plant_id.replace('"', '')  # 防 flux 注入：去掉引号

        # 1) 先查该厂最新数据时间，作为窗口终点（无数据则整包返回空）
        last_t: datetime | None = None
        for side in ("influent", "effluent"):
            q = (
                f'from(bucket: "{bucket}") '
                f'|> range(start: 0) '
                f'|> filter(fn: (r) => r._measurement == "wastewater" '
                f'  and r.plant_id == "{plant_id}" and r.data_type == "{side}") '
                f'|> group() |> last()'
            )
            df = client.query_api().query_data_frame(q)
            if isinstance(df, list):
                df = pd.concat([d for d in df if not d.empty], ignore_index=True) if df else pd.DataFrame()
            if df is not None and not df.empty and "_time" in df.columns:
                t = pd.to_datetime(df["_time"].iloc[0]).to_pydatetime()
                if last_t is None or t > last_t:
                    last_t = t

        if last_t is None:
            client.close()
            return {"success": True, "data": {
                "plant_id": plant_id, "window_hours": hours,
                "indicators": {f: {"label": l, "unit": u, "limit": lim, "influent": None,
                    "effluent": None, "status": "nodata",
                    "series": {"influent": [], "effluent": []}}
                    for l, f, lim, u in _DASH_INDICATORS},
                "influent_points": 0, "effluent_points": 0,
            }}

        # 2) 窗口:anchor 模式=[anchor 00:00 起7天];默认=最新点往前 hours 小时
        if anchor:
            a = datetime.strptime(anchor.replace('"', ''), "%Y-%m-%d").replace(tzinfo=timezone.utc)
            seg_start = a
            seg_end = a + timedelta(days=7)
            end_t = min(seg_end, last_t + timedelta(minutes=1))
            start = seg_start.strftime("%Y-%m-%dT%H:%M:%SZ")
            end = end_t.strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            start = (last_t - timedelta(hours=hours)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            end = (last_t + timedelta(minutes=1)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        def _flux(data_type: str) -> str:
            return (
                f'from(bucket: "{bucket}") '
                f'|> range(start: {start}, stop: {end}) '
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
        # ── 动态发现该厂实际有的指标字段(按默认顺序+未知字段追加;跳过 *_mass 排放量) ──
        overrides = _plant_overrides(plant_id)
        limits_cfg = overrides.get("limits") or {}
        fields: list[str] = []
        for side in ("influent", "effluent"):
            for c in dfs.get(side, pd.DataFrame()).columns:
                if c.startswith(("_", "table", "result", "data_type", "plant_id", "_measurement", "_start", "_stop")) or c.endswith("_mass"):
                    continue
                if c not in fields:
                    fields.append(c)
        ordered = [f for f in _INDICATOR_ORDER if f in fields] + [f for f in fields if f not in _INDICATOR_ORDER]
        # 无数据时仍返回默认指标集(前端显示"无数据"格而不是空白)
        if not ordered:
            ordered = _INDICATOR_ORDER[:6]

        for field in ordered:
            label, limit, unit = _INDICATOR_META.get(field, (field, None, ""))
            # per-plant 限值覆盖: {"COD": 60.0} 或 {"pH": [6,9]}
            if field in limits_cfg:
                limit = limits_cfg[field]
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
            "latest_time": last_t.strftime("%Y-%m-%d %H:%M"),
            "anchor": anchor or "",
            "segment_start": start[:16].replace("T", " "),
            "segment_end": end[:16].replace("T", " "),
            "indicators": indicators,
            "influent_points": len(dfs.get("influent", pd.DataFrame())),
            "effluent_points": len(dfs.get("effluent", pd.DataFrame())),
        }}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"厂看板数据获取失败: {e}")
