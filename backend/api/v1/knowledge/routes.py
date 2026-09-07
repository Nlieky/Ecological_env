# backend/api/v1/knowledge/routes.py
"""知识图谱 API——只读 3 端点（/agents/knowledge 页面数据源）。

库不存在时返回空图 + seeded:false（前端显示引导卡片），不自动建库。
live=true 时把 /v1/system/status 的实时状态叠加到节点 props（查时合并，不落库）。
"""
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["知识图谱"])

# routes.py 在 backend/api/v1/knowledge/ 下，parents[4] 才是项目根
_DB_PATH = Path(__file__).resolve().parents[4] / "shared" / "data" / "knowledge_graph.db"
_store_cache: Optional[object] = None


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
    """查时合并：各厂数据新鲜度叠加到 plant 节点 props。失败不影响主图。

    get_system_status 返回 {"success", "data": {"plants": [
        {"plant_id", "latest_time", "status", "data_types"}, ...]}}；
    plant 节点 id 保留真实中文 plant_id（graph_store 约定，同 InfluxDB tag），
    故 id 去掉 "plant:" 前缀后直接与 plant_id 匹配。
    """
    try:
        from backend.api.v1.system.routes import get_system_status
        status = await get_system_status()
        plants = (status.get("data") or {}).get("plants", [])
        plant_fresh = {p.get("plant_id"): p for p in plants}
        for n in nodes:
            if n["type"] == "plant":
                info = plant_fresh.get(n["id"].split(":", 1)[1])
                if info:
                    n["props"]["last_data_ts"] = info.get("latest_time", "")
                    n["props"]["live_status"] = info.get("status", "")
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
