# tests/knowledge_graph/test_api_routes.py
"""knowledge 路由测试：种子后全图、类型过滤、节点详情、404、stats。"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    db = tmp_path_factory.mktemp("kg") / "kg.test.db"
    from shared.knowledge_graph import seed_importer
    seed_importer.run_seed(db_path=db)

    import backend.api.v1.knowledge.routes as kr
    kr._DB_PATH = db          # 模块级 db 路径（测试专用临时库）
    kr._store_cache = None    # 清缓存

    from backend.main import app
    return TestClient(app)


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
