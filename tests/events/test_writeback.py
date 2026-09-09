# tests/events/test_writeback.py
"""研判写回图谱：事件入库时同步写案例节点+involves/cites边；幂等；图缺失静默；防悬挂边。"""
import json

import pytest

from shared.knowledge_graph.graph_store import GraphStore
from shared.knowledge_graph import seed_importer


@pytest.fixture
def env(tmp_path, monkeypatch):
    """独立 events 库 + 独立种子图谱 + 伪造 medium session。"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import backend.database.base as base
    import backend.services.event_service as es
    engine = create_engine(f"sqlite:///{tmp_path}/ev.db", connect_args={"check_same_thread": False})
    base.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(es, "SessionLocal", sessionmaker(bind=engine))
    kg = tmp_path / "kg.db"
    seed_importer.run_seed(db_path=kg)
    svc = es.EventService(sessions_root=tmp_path)
    monkeypatch.setattr(es, "_graph_db_path", kg)
    sd = tmp_path / "session_wb1"
    sd.mkdir()
    (sd / "disposition_result.json").write_text(json.dumps({
        "task_id": "t1", "status": "completed",
        "result": {"suspicion_level": "medium", "suspicion_level_cn": "中风险",
                   "violation_types": ["暗管偷排"], "action": "现场核查",
                   "confidence": 0.9, "work_order": None, "report": None,
                   "evidence_points": []},
        "metadata": {"timestamp": "2026-09-09T10:00:00"}}, ensure_ascii=False), encoding="utf-8")
    (sd / "task.json").write_text(json.dumps(
        {"task": "查询当阳市金桥污水处理厂一期数据研判", "task_id": "t1"}, ensure_ascii=False), encoding="utf-8")
    yield svc, sd.name, kg
    engine.dispose()


def test_writeback_creates_case_node(env):
    svc, session_name, kg = env
    ev = svc.collect_from_session(session_name)
    assert ev is not None
    g = GraphStore(kg)
    node = g.get_node(f"case:{ev['id']}")
    assert node is not None
    assert node["props"]["plant_id"] == "当阳市金桥污水处理厂一期"
    assert node["props"]["severity"] == "medium"
    assert node["props"]["source_event"] == ev["id"]
    nb = g.neighbors(f"case:{ev['id']}", edge_types=["involves"], direction="out", depth=1)
    assert {n["id"] for n in nb["nodes"]} == {"plant:当阳市金桥污水处理厂一期"}
    nb2 = g.neighbors(f"case:{ev['id']}", edge_types=["cites"], direction="out", depth=1)
    assert "pattern:secret_pipe" in {n["id"] for n in nb2["nodes"]}
    g.close()


def test_writeback_idempotent(env):
    svc, session_name, kg = env
    svc.collect_from_session(session_name)
    assert svc.collect_from_session(session_name) is None  # 事件幂等
    g = GraphStore(kg)
    cases = g.subgraph(node_types=["case"])["nodes"]
    assert len(cases) == 3  # 种子2+写回1，无重复
    g.close()


def test_writeback_unknown_pattern_skips_cites(env):
    svc, sd, kg = env
    d = json.loads((svc.sessions_root / sd / "disposition_result.json").read_text(encoding="utf-8"))
    d["result"]["violation_types"] = ["不存在的类型"]
    (svc.sessions_root / sd / "disposition_result.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    ev = svc.collect_from_session(sd)
    g = GraphStore(kg)
    assert g.get_node(f"case:{ev['id']}") is not None  # 节点仍写
    nb = g.neighbors(f"case:{ev['id']}", edge_types=["cites"], direction="out", depth=1)
    assert nb["nodes"] == []  # 反查不到的边跳过
    g.close()


def test_writeback_unknown_plant_skips_involves(env):
    # 厂不在图（unknown）→ involves 边跳过防悬挂，节点仍写
    svc, sd, kg = env
    d = json.loads((svc.sessions_root / sd / "disposition_result.json").read_text(encoding="utf-8"))
    (svc.sessions_root / sd / "task.json").write_text(
        json.dumps({"task": "查询某未知厂数据", "task_id": "t1"}, ensure_ascii=False), encoding="utf-8")
    ev = svc.collect_from_session(sd)
    g = GraphStore(kg)
    assert g.get_node(f"case:{ev['id']}") is not None
    nb = g.neighbors(f"case:{ev['id']}", edge_types=["involves"], direction="out", depth=1)
    assert nb["nodes"] == []
    g.close()


def test_writeback_graph_missing_silent(tmp_path, monkeypatch):
    """图谱 DB 不存在 → 事件照常入库，写回静默跳过不抛。"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import backend.database.base as base
    import backend.services.event_service as es
    engine = create_engine(f"sqlite:///{tmp_path}/ev2.db", connect_args={"check_same_thread": False})
    base.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(es, "SessionLocal", sessionmaker(bind=engine))
    monkeypatch.setattr(es, "_graph_db_path", tmp_path / "nope.db")
    sd = tmp_path / "session_wb2"
    sd.mkdir()
    (sd / "disposition_result.json").write_text(json.dumps({
        "task_id": "t", "status": "completed",
        "result": {"suspicion_level": "high", "violation_types": ["插瓶干扰"],
                   "action": "立即调查取证", "confidence": 0.9,
                   "work_order": None, "report": None, "evidence_points": []},
        "metadata": {"timestamp": "2026-09-09T11:00:00"}}, ensure_ascii=False), encoding="utf-8")
    (sd / "task.json").write_text(json.dumps(
        {"task": "查询金桥数据", "task_id": "t"}, ensure_ascii=False), encoding="utf-8")
    svc = es.EventService(sessions_root=tmp_path)
    ev = svc.collect_from_session("session_wb2")  # 不抛
    assert ev is not None
    engine.dispose()


def test_writeback_corrupt_graph_silent(env, monkeypatch):
    """图文件损坏 → 写回静默（事件已入库不受影响）。"""
    import backend.services.event_service as es
    svc, sd, kg = env
    kg.write_text("not a database", encoding="utf-8")
    ev = svc.collect_from_session(sd)  # 不抛
    assert ev is not None
