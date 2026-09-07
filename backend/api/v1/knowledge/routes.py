# backend/api/v1/knowledge/routes.py
"""知识图谱 API——只读 3 端点（/agents/knowledge 页面数据源）。

库不存在时返回空图 + seeded:false（前端显示引导卡片），不自动建库。
live=true 时把各厂数据新鲜度叠加到节点 props（查时合并，不落库）——直接经
asyncio.to_thread 调 discover_plants()（InfluxDB 网络 IO 挪出事件循环，防
InfluxDB 慢时全端点冻结；也不借道 /v1/system/status，免附 agent 服务探测）。
"""
import asyncio
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

    discover_plants() 返回 [{"plant_id", "data_types", "latest_time"(原始
    datetime 字符串), "point_count"}]，无 status 字段——能被发现即有数据，
    同 get_system_status 的映射记 online；时间同样截到分钟（[:16]）并把
    ISO 的 T 换成空格。plant 节点 id 保留真实中文 plant_id（graph_store
    约定，同 InfluxDB tag），去掉 "plant:" 前缀后直接与 plant_id 匹配。
    """
    try:
        from shared.data.discover_plants import discover_plants
        plants = await asyncio.to_thread(discover_plants)
        plant_fresh = {p.get("plant_id"): p for p in plants}
        for n in nodes:
            if n["type"] != "plant" or not n["id"].startswith("plant:"):
                continue  # startswith 守卫：畸形 id 跳过，不影响其余节点
            info = plant_fresh.get(n["id"].partition(":")[2])
            if info:
                n["props"]["last_data_ts"] = (
                    str(info.get("latest_time", ""))[:16].replace("T", " "))
                n["props"]["live_status"] = "online"
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
