# tests/knowledge_graph/test_graph_store.py
"""GraphStore 单测：建表、upsert 幂等、邻居、子图、路径、统计。"""
from pathlib import Path

import pytest

from shared.knowledge_graph.graph_store import GraphStore


def make_store(tmp_path: Path) -> GraphStore:
    return GraphStore(tmp_path / "kg.db")


def seed_small(g: GraphStore) -> None:
    """链 A->B->C->D + 旁支 E->C，类型各异。"""
    nodes = [
        ("agent:master", "agent", "主智能体", {}),
        ("operator:constant", "operator", "恒定检测", {}),
        ("pattern:bottle", "violation_pattern", "插瓶干扰", {}),
        ("regulation:law83", "regulation", "水污染防治法§83", {}),
        ("plant:jinqiao", "plant", "金桥一期", {}),
    ]
    for nid, ntype, label, props in nodes:
        g.upsert_node(nid, ntype, label, props)
    edges = [
        ("agent:master", "operator:constant", "employs"),
        ("operator:constant", "pattern:bottle", "detects"),
        ("pattern:bottle", "regulation:law83", "indicates"),
        ("plant:jinqiao", "pattern:bottle", "involves"),
    ]
    for src, dst, etype in edges:
        g.upsert_edge(src, dst, etype)


def test_upsert_node_idempotent(tmp_path):
    g = make_store(tmp_path)
    g.upsert_node("plant:x", "plant", "厂X", {"type": "市政"})
    g.upsert_node("plant:x", "plant", "厂X改", {"type": "洗舱"})  # 同 id 重写=更新
    node = g.get_node("plant:x")
    assert node["label"] == "厂X改"
    assert node["props"]["type"] == "洗舱"
    assert g.stats()["nodes"] == 1  # 不重复


def test_upsert_edge_idempotent(tmp_path):
    g = make_store(tmp_path)
    g.upsert_node("a", "plant", "A", {})
    g.upsert_node("b", "indicator", "B", {})
    g.upsert_edge("a", "b", "monitors")
    g.upsert_edge("a", "b", "monitors")  # UNIQUE(src,dst,type) 去重
    g.upsert_edge("a", "b", "monitors", {"w": 2})  # 带属性重写仍只 1 条
    assert g.stats()["edges"] == 1


def test_unknown_type_rejected(tmp_path):
    g = make_store(tmp_path)
    with pytest.raises(ValueError):
        g.upsert_node("x:y", "bad_type", "Y", {})
    g.upsert_node("a", "plant", "A", {})
    with pytest.raises(ValueError):
        g.upsert_edge("a", "x:y", "bad_edge")


def test_get_node_missing_returns_none(tmp_path):
    g = make_store(tmp_path)
    assert g.get_node("nope") is None


def test_neighbors_one_hop(tmp_path):
    g = make_store(tmp_path)
    seed_small(g)
    nb = g.neighbors("agent:master", depth=1)
    assert {n["id"] for n in nb["nodes"]} == {"operator:constant"}
    assert nb["depth"] == 1


def test_neighbors_multi_hop(tmp_path):
    g = make_store(tmp_path)
    seed_small(g)
    nb = g.neighbors("agent:master", depth=3)
    # 1跳 constant；2跳 bottle；3跳 law83/jinqiao
    assert {n["id"] for n in nb["nodes"]} == {
        "operator:constant", "pattern:bottle",
        "regulation:law83", "plant:jinqiao"}
    # 最小深度标注
    depths = {n["id"]: n["depth"] for n in nb["nodes"]}
    assert depths["operator:constant"] == 1
    assert depths["pattern:bottle"] == 2


def test_neighbors_edge_type_filter(tmp_path):
    g = make_store(tmp_path)
    seed_small(g)
    nb = g.neighbors("operator:constant", edge_types=["detects"], depth=4)
    assert {n["id"] for n in nb["nodes"]} == {"pattern:bottle"}


def test_neighbors_direction_in(tmp_path):
    g = make_store(tmp_path)
    seed_small(g)
    nb = g.neighbors("pattern:bottle", direction="in", depth=1)
    # 只有顺边指向 bottle 的：constant(detects)、jinqiao(involves)
    assert {n["id"] for n in nb["nodes"]} == {"operator:constant", "plant:jinqiao"}


def test_neighbors_depth_rejected_over_4(tmp_path):
    g = make_store(tmp_path)
    seed_small(g)
    with pytest.raises(ValueError):
        g.neighbors("agent:master", depth=5)
    with pytest.raises(ValueError):
        g.neighbors("agent:master", depth=99)
    assert g.neighbors("agent:master", depth=4)["depth"] == 4  # 上限内 OK


def test_neighbors_includes_connecting_edges(tmp_path):
    g = make_store(tmp_path)
    seed_small(g)
    nb = g.neighbors("agent:master", depth=2)
    etypes = {e["type"] for e in nb["edges"]}
    assert etypes == {"employs", "detects"}  # 起点到结果集内部的边


def test_subgraph_type_filter(tmp_path):
    g = make_store(tmp_path)
    seed_small(g)
    sg = g.subgraph(node_types=["plant", "violation_pattern"])
    assert {n["id"] for n in sg["nodes"]} == {"plant:jinqiao", "pattern:bottle"}
    # 边两端都在集合内才保留
    assert len(sg["edges"]) == 1
    assert sg["edges"][0]["type"] == "involves"


def test_shortest_path(tmp_path):
    g = make_store(tmp_path)
    seed_small(g)
    assert g.shortest_path("agent:master", "regulation:law83") == [
        "agent:master", "operator:constant", "pattern:bottle", "regulation:law83"]
    assert g.shortest_path("agent:master", "nope") is None
    assert g.shortest_path("agent:master", "agent:master") == ["agent:master"]


def test_stats_by_type(tmp_path):
    g = make_store(tmp_path)
    seed_small(g)
    st = g.stats()
    assert st["nodes"] == 5
    assert st["edges"] == 4
    assert st["node_types"]["plant"] == 1
    assert st["edge_types"]["detects"] == 1


def test_meta_roundtrip(tmp_path):
    g = make_store(tmp_path)
    g.set_meta("schema_version", "1")
    assert g.get_meta("schema_version") == "1"
    g.set_meta("schema_version", "2")  # 覆盖
    assert g.get_meta("schema_version") == "2"
    assert g.get_meta("nope") is None
