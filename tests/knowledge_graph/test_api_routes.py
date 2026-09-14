# tests/knowledge_graph/test_api_routes.py
"""knowledge 路由测试：种子后全图、类型过滤、节点详情、404、stats、空库引导。"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def client(tmp_path):
    """临时种子库 + 覆盖模块级 db 路径，测完还原（防污染同进程后续测试）。"""
    db = tmp_path / "kg.test.db"
    from shared.knowledge_graph import seed_importer
    seed_importer.run_seed(db_path=db)

    import backend.api.v1.knowledge.routes as kr
    saved_path, saved_cache = kr._DB_PATH, kr._store_cache
    kr._DB_PATH = db          # 模块级 db 路径（测试专用临时库）
    kr._store_cache = None    # 清缓存
    try:
        from backend.main import app
        yield TestClient(app)
    finally:
        kr._DB_PATH, kr._store_cache = saved_path, saved_cache


def test_graph_endpoint_returns_full(client):
    r = client.get("/api/v1/knowledge/graph", params={"live": "false"})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["seeded"] is True
    assert len(body["nodes"]) >= 60
    assert len(body["edges"]) >= 35


def test_graph_type_filter(client):
    r = client.get("/api/v1/knowledge/graph",
                   params={"node_types": "plant,violation_pattern",
                           "live": "false"})
    assert r.status_code == 200
    types = {n["type"] for n in r.json()["nodes"]}
    assert types <= {"plant", "violation_pattern"}
    for e in r.json()["edges"]:
        assert e["src"].split(":")[0] in ("plant", "violation_pattern")
        assert e["dst"].split(":")[0] in ("plant", "violation_pattern")


def test_node_detail(client):
    r = client.get("/api/v1/knowledge/node/pattern:bottle_interference")
    assert r.status_code == 200
    body = r.json()
    assert body["node"]["label"] == "插瓶干扰"
    assert "violation_pattern" not in body["neighbors"]  # 分组里不含自己类型
    assert "operator" in body["neighbors"]               # detects 入边来源


def test_node_404(client):
    r = client.get("/api/v1/knowledge/node/nonexistent:id")
    assert r.status_code == 404


def test_stats_endpoint(client):
    r = client.get("/api/v1/knowledge/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["node_types"]["plant"] >= 1
    assert "case_count" in body


def test_impact_happy_path(client):
    r = client.get("/api/v1/knowledge/impact/service:influxdb",
                   params={"direction": "downstream"})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["node"]["id"] == "service:influxdb"
    assert body["downstream"]            # 感知→主智能体→…整条链都在
    assert body["upstream"] == []        # 单向模式另一侧为空
    assert all("depth" in n and "via" in n for n in body["downstream"])


def test_impact_unknown_node_404(client):
    r = client.get("/api/v1/knowledge/impact/nonexistent:node")
    assert r.status_code == 404


def test_impact_bad_direction_400(client):
    r = client.get("/api/v1/knowledge/impact/service:influxdb",
                   params={"direction": "sideways"})
    assert r.status_code == 400


def test_empty_db_guidance(tmp_path):
    """库不存在：三端点都走引导态（不建库、不 5xx）。"""
    import backend.api.v1.knowledge.routes as kr
    saved_path, saved_cache = kr._DB_PATH, kr._store_cache
    kr._DB_PATH = tmp_path / "nonexistent" / "kg.db"  # 不存在的路径
    kr._store_cache = None
    try:
        from fastapi.testclient import TestClient
        from backend.main import app
        c = TestClient(app)

        r = c.get("/api/v1/knowledge/graph")
        assert r.status_code == 200
        assert r.json() == {"success": True, "seeded": False,
                            "nodes": [], "edges": [], "stats": {}}

        r = c.get("/api/v1/knowledge/node/plant:any")
        assert r.status_code == 404

        r = c.get("/api/v1/knowledge/stats")
        assert r.status_code == 200
        body = r.json()
        assert body["seeded"] is False and body["nodes"] == 0
        assert body["node_types"] == {} and body["case_count"] == 0

        r = c.get("/api/v1/knowledge/impact/plant:any")
        assert r.status_code == 404  # 空库 impact 走 404 引导
    finally:
        kr._DB_PATH, kr._store_cache = saved_path, saved_cache
