# tests/knowledge_graph/test_impact.py
"""impact() 双向影响推演：按边类型分方向、排除领域边、depth 截断。"""
from pathlib import Path
import pytest
from shared.knowledge_graph.graph_store import GraphStore


@pytest.fixture
def topo(tmp_path):
    """混合边拓扑:
    agent_service --hosts--> master --orchestrates--> perception --reads--> influxdb
    backend --calls--> agent_service ; frontend --calls--> backend
    master --invokes--> call_subagent ; 领域边 plant--monitors-->COD
    """
    g = GraphStore(tmp_path / "kg.db")
    N = [
        ("service:frontend", "service"), ("service:backend", "service"),
        ("service:agent_service", "service"), ("service:influxdb", "service"),
        ("agent:master", "agent"),
        ("agent:multi-dimensional-data-perception", "agent"),
        ("tool:call_subagent", "tool"),
        ("plant:jinqiao", "plant"), ("indicator:COD", "indicator"),
    ]
    for nid, ntype in N:
        g.upsert_node(nid, ntype, nid.split(":")[1], {})
    E = [
        ("service:agent_service", "agent:master", "hosts"),
        ("agent:master", "agent:multi-dimensional-data-perception", "orchestrates"),
        ("agent:multi-dimensional-data-perception", "service:influxdb", "reads"),
        ("service:backend", "service:agent_service", "calls"),
        ("service:frontend", "service:backend", "calls"),
        ("agent:master", "tool:call_subagent", "invokes"),
        ("plant:jinqiao", "indicator:COD", "monitors"),
    ]
    for s, d, t in E:
        g.upsert_edge(s, d, t)
    return g


def test_impact_influxdb_downstream(topo):
    r = topo.impact("service:influxdb", direction="downstream")
    ids = {n["id"] for n in r["downstream"]}
    assert "agent:multi-dimensional-data-perception" in ids
    assert "agent:master" in ids
    assert "service:backend" in ids
    assert "service:frontend" in ids
    assert r["upstream"] == []


def test_impact_influxdb_upstream_empty(topo):
    r = topo.impact("service:influxdb", direction="upstream")
    assert r["upstream"] == [] and r["downstream"] == []


def test_impact_frontend_directions(topo):
    r = topo.impact("service:frontend", direction="downstream")
    assert r["downstream"] == []
    r2 = topo.impact("service:frontend", direction="upstream")
    up = {n["id"] for n in r2["upstream"]}
    assert "service:backend" in up and "service:agent_service" in up


def test_impact_agent_service_hosts(topo):
    r = topo.impact("service:agent_service", direction="downstream")
    ids = {n["id"] for n in r["downstream"]}
    assert "agent:master" in ids
    assert "service:frontend" in ids


def test_impact_excludes_domain_edges(topo):
    r = topo.impact("plant:jinqiao")
    assert r["downstream"] == [] and r["upstream"] == []


def test_impact_missing_node_raises(topo):
    with pytest.raises(KeyError):
        topo.impact("nope:xxx")


def test_impact_via_first_hop(topo):
    r = topo.impact("service:influxdb")
    perc = next(n for n in r["downstream"]
                if n["id"] == "agent:multi-dimensional-data-perception")
    assert perc.get("via") == "reads"


def test_impact_bad_direction_raises(topo):
    with pytest.raises(ValueError):
        topo.impact("service:influxdb", direction="sideways")


def test_impact_node_payload(topo):
    r = topo.impact("service:influxdb", direction="downstream")
    assert r["node"]["id"] == "service:influxdb"
    assert r["node"]["type"] == "service"
    for n in r["downstream"]:
        assert {"id", "type", "label", "depth", "via"} <= set(n)
        assert isinstance(n["depth"], int) and n["depth"] >= 1
