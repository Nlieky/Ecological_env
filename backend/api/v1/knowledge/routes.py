# backend/api/v1/knowledge/routes.py
"""知识图谱 API——只读端点（/agents/knowledge 页面数据源）。

库不存在时返回空图 + seeded:false（前端显示引导卡片），不自动建库。
live=true 时叠加活状态到节点 props（查时合并，不落库）：plant 节点叠各厂
数据新鲜度、service 节点叠六服务健康（子项目4）——两路都取自
/v1/system/status 的 get_system_status（内部探测有 10s 缓存 + 网络 IO 在
线程池，不会拖慢本端点；图谱节点 id 后缀 ↔ status 数组 name 经 _SVC_MAP
映射，如 service:agent_service ↔ agent）。
/knowledge/impact/{node_id}（子项目4 根因分析）：GraphStore.impact 双向
故障影响面推演，downstream=该点挂了谁受影响 / upstream=可能是谁引起的。
"""
import asyncio
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["知识图谱"])

# routes.py 在 backend/api/v1/knowledge/ 下，parents[4] 才是项目根
_DB_PATH = Path(__file__).resolve().parents[4] / "shared" / "data" / "knowledge_graph.db"
_store_cache: Optional[object] = None

# 图谱 service 节点 id 后缀 ↔ /system/status services[].name（agent_service↔agent）
_SVC_MAP = {"agent_service": "agent", "backend": "backend",
            "influxdb": "influxdb", "frontend": "frontend",
            "llm": "llm", "sqlite_logs": "sqlite_logs"}


def _get_store():
    global _store_cache
    if _store_cache is not None:
        return _store_cache
    if not _DB_PATH.exists():
        return None
    from shared.knowledge_graph import GraphStore
    _store_cache = GraphStore(_DB_PATH)
    return _store_cache


async def _overlay_live_status(nodes: list) -> None:
    """查时合并：plant 新鲜度 + service 健康叠加到节点 props。失败不影响主图。

    数据源 get_system_status()（借道其 10s 探测缓存，plants/services 一次
    拿全）：plants 项含已格式化 latest_time 与 status="online"（能被发现即
    有数据）；services 项 {name, title, status}。plant 节点 id 保留真实中文
    plant_id（graph_store 约定，同 InfluxDB tag），去 "plant:" 前缀直接匹配。
    """
    try:
        from backend.api.v1.system.routes import get_system_status
        data = (await get_system_status()).get("data", {})
        services = data.get("services", [])
        generated_at = data.get("generated_at", "")
        plant_fresh = {p.get("plant_id"): p for p in data.get("plants", [])}
        for n in nodes:
            if n["type"] == "plant" and n["id"].startswith("plant:"):
                info = plant_fresh.get(n["id"].partition(":")[2])
                if info:
                    n["props"]["last_data_ts"] = (
                        str(info.get("latest_time", ""))[:16].replace("T", " "))
                    n["props"]["live_status"] = info.get("status", "online")
            elif n["type"] == "service" and ":" in n["id"]:
                # 六服务健康叠加（子项目4）
                key = _SVC_MAP.get(n["id"].split(":", 1)[1])
                svc = next((s for s in services if s.get("name") == key), None)
                if svc:
                    n["props"]["health"] = svc.get("status", "unknown")
                    n["props"]["health_checked_at"] = generated_at or ""
    except Exception:
        pass


@router.get("/knowledge/graph")
async def get_graph(node_types: str = "", edge_types: str = "",
                    live: bool = True):
    store = _get_store()
    if store is None:
        return {"success": True, "seeded": False, "nodes": [],
                "edges": [], "stats": {}}
    nt = [t for t in node_types.split(",") if t]
    et = [t for t in edge_types.split(",") if t]
    sg = store.subgraph(node_types=nt or None, edge_types=et or None)
    if live:
        await _overlay_live_status(sg["nodes"])
    return {"success": True, "seeded": True, **sg, "stats": store.stats()}


@router.get("/knowledge/node/{node_id}")
async def get_node(node_id: str):
    store = _get_store()
    if store is None:
        raise HTTPException(404, "知识图谱未初始化")
    node = store.get_node(node_id)
    if node is None:
        raise HTTPException(404, f"节点不存在: {node_id}")
    nb = store.neighbors(node_id, depth=1)
    grouped: dict = {}
    for n in nb["nodes"]:
        grouped.setdefault(n["type"], []).append(n)
    return {"success": True, "node": node, "neighbors": grouped}


@router.get("/knowledge/impact/{node_id}")
async def get_impact(node_id: str, direction: str = "both"):
    """故障影响面双向推演（子项目4 根因分析）。

    direction: downstream=该点挂了谁受影响 / upstream=可能是谁引起的 /
    both（默认）。节点不存在 404，direction 非法 400。
    """
    store = _get_store()
    if store is None:
        raise HTTPException(404, "知识图谱未初始化")
    try:
        r = store.impact(node_id, direction=direction)
    except KeyError:
        raise HTTPException(404, f"节点不存在: {node_id}")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"success": True, **r}


@router.get("/knowledge/stats")
async def get_stats():
    store = _get_store()
    if store is None:
        return {"success": True, "seeded": False, "nodes": 0, "edges": 0,
                "node_types": {}, "edge_types": {}, "case_count": 0}
    st = store.stats()
    st["case_count"] = st["node_types"].get("case", 0)
    st["seeded"] = True
    return {"success": True, **st}
