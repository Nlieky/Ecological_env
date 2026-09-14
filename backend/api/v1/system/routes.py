"""系统态势 API——部署系统运维状态监控 + 态势历史。

参考 aiops.hgdz.cn 的「系统态势/态势历史」两个一级入口：
- /system/status  : 当前态势快照（各厂数据新鲜度、服务健康、累计处理量/告警量）
- /system/history : 按天聚合的历史态势（点数、进/出水均值、超标次数）

六服务健康探测（子项目4 根因分析）：backend/agent/influxdb/frontend/llm/
sqlite_logs——name 与图谱 service 节点 id 后缀对齐（service:llm ↔ llm），
/knowledge/graph 的 service 健康叠加直接消费本结果。各探测独立 try/except
隔离（单探失败只标 down 不拖垮其余），五项独立探测在 _probe_services 里
ThreadPoolExecutor 并行（单探超时 ≤3s → 冷启总耗时 ≈最慢一探，非串行和）。
结果模块级缓存 _STATUS_TTL=10s（图谱叠加与大屏轮询共用，防重复探测）；
探测体是同步网络 IO，统一收进 _build_status_data 由 asyncio.to_thread
执行，防 InfluxDB/LLM 慢时冻结事件循环（同 knowledge 路由 discover_plants
的处理方式）。
"""
import asyncio
import copy
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(tags=["系统态势"])

# 出水超标限值（与 plants dashboard 一致）
_EFF_LIMITS = {"COD": 100.0, "TN": 20.0, "AN": 15.0, "TP": 1.0}

# routes.py 在 backend/api/v1/system/ 下，parents[4] 才是项目根（同 knowledge 路由）
_LOGS_DB_PATH = (Path(__file__).resolve().parents[4]
                 / "shared" / "data" / "ecological_logs.db")

# 六服务探测缓存（模块级；命中直接 deepcopy 返回，过期重探）
_STATUS_CACHE: dict = {"ts": 0.0, "data": None}
_STATUS_TTL = 10.0


def _probe_agent() -> str:
    try:
        from backend.core.config import settings
        import httpx
        # connect=1s：localhost 双栈(::1+127.0.0.1)各一次尝试，服务挂了 ~2s 判 down
        r = httpx.get(f"{settings.AGENT_SERVICE_URL}/health",
                      timeout=httpx.Timeout(3.0, connect=1.0))
        return "up" if r.status_code == 200 else "down"
    except Exception:
        return "down"


def _probe_influxdb() -> str:
    """真连探测：GET /health 且 status=="pass" 才算 up。

    InfluxDBClient 构造是惰性的（无网络 IO）、close() 是空操作——只验 token
    存在不算探测（InfluxDB 挂了也会误报 up）。health() 对网络失败/非 pass
    都返回 status="fail" → down。默认 timeout 30_000ms 太长，调 health() 前
    收紧为 (connect=1s, read=3s)（rest 层毫秒单位，支持二元组）——connect
    按 socket.create_connection 逐地址生效：localhost 双栈(IPv6+IPv4)各 ≤1s
    → 挂掉时 down ≤2s；健康时读 /health 响应仍有 3s 余量。
    """
    try:
        from shared.data.influxdb_query import get_client_and_bucket
        client, _bucket = get_client_and_bucket()
        try:
            client.api_client.configuration.timeout = (1_000, 3_000)  # ms
            return "up" if client.health().status == "pass" else "down"
        finally:
            client.close()
    except Exception:
        return "down"


def _probe_frontend() -> str:
    try:
        from backend.core.config import settings
        import httpx
        # connect=1s 同 _probe_agent：挂了 ~2s 判 down（总预算 2s）
        r = httpx.head(settings.FRONTEND_URL,
                       timeout=httpx.Timeout(2.0, connect=1.0))
        # 有响应即服务在（dev server 200；<500 都算活，500+ 视为故障）
        return "up" if r.status_code < 500 else "down"
    except Exception:
        return "down"


def _probe_llm() -> str:
    try:
        from backend.core.config import settings  # noqa: F401 触发 load_dotenv
        from backend.services.agent_params import get_param
        import httpx
        # URL 解析与真实 LLM 流量同一条 get_param 链（start_agent.py 同款调用：
        # DB 优先→env→注册表默认；其上还有 llm_providers 供应商表覆盖层，探测不感知）
        base = str(get_param("llm_base_url") or "").rstrip("/")
        if not base:
            return "down"
        # 远端主机 connect 略宽（1.5s），读预算 3s
        r = httpx.get(f"{base}/models", timeout=httpx.Timeout(3.0, connect=1.5))
        return "up" if r.status_code < 500 else "down"
    except Exception:
        return "down"


def _probe_sqlite_logs() -> str:
    try:
        if not _LOGS_DB_PATH.exists():
            return "down"
        conn = sqlite3.connect(str(_LOGS_DB_PATH), timeout=1.0)
        try:
            conn.execute("PRAGMA quick_check(1)").fetchone()
            return "up"
        finally:
            conn.close()
    except Exception:
        return "down"


def _probe_services() -> list:
    """五项独立探测并行跑（backend 能响应本请求即 up，不用探）。

    各探单超时 ≤3s，ThreadPoolExecutor 并行使冷启总耗时 ≈最慢一探而非串行
    和（~3s 而非 ~9s）。探测函数按模块全局名取（tests monkeypatch 生效）。
    """
    probes = [
        ("agent", "智能体服务", _probe_agent),
        ("influxdb", "时序数据库", _probe_influxdb),
        ("frontend", "前端界面", _probe_frontend),
        ("llm", "LLM 服务", _probe_llm),
        ("sqlite_logs", "日志数据库", _probe_sqlite_logs),
    ]
    with ThreadPoolExecutor(max_workers=len(probes)) as ex:
        statuses = list(ex.map(lambda p: p[2](), probes))
    services = [{"name": "backend", "title": "后端 API", "status": "up"}]
    services.extend({"name": name, "title": title, "status": status}
                    for (name, title, _), status in zip(probes, statuses))
    return services


def _build_status_data() -> dict:
    """同步探测体（asyncio.to_thread 里跑，可放心阻塞）。"""
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

    # 服务健康（并行探测，见 _probe_services）
    services = _probe_services()

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


@router.get("/system/status")
async def get_system_status():
    """系统当前态势快照（六服务探测，10s 缓存）。"""
    now = time.time()
    if _STATUS_CACHE["data"] is not None and now - _STATUS_CACHE["ts"] < _STATUS_TTL:
        return copy.deepcopy(_STATUS_CACHE["data"])
    resp = await asyncio.to_thread(_build_status_data)
    _STATUS_CACHE["ts"] = time.time()
    _STATUS_CACHE["data"] = resp
    return copy.deepcopy(resp)


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
