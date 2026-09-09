# tests/knowledge_graph/test_graph_query.py
"""GraphKnowledgeSource：优先图谱、不可用回退、回退可观测。"""
import pytest

from shared.knowledge_graph.graph_query import GraphKnowledgeSource
from shared.knowledge_graph import seed_importer


@pytest.fixture(scope="module")
def seeded_db(tmp_path_factory):
    db = tmp_path_factory.mktemp("gq") / "kg.db"
    seed_importer.run_seed(db_path=db)
    return db


def test_patterns_from_graph(seeded_db):
    src = GraphKnowledgeSource(db_path=seeded_db)
    pats = src.get_patterns()
    assert src.available is True
    labels = {p["label"] for p in pats}
    assert {"插瓶干扰", "暗管偷排", "稀释排放", "人工拟合"} <= labels
    # 审计修正后的字段：恶意逃避 desc 是数据缺失型定义
    me = next(p for p in pats if p["label"] == "恶意逃避")
    assert "缺失" in me["desc"]


def test_cases_from_graph(seeded_db):
    src = GraphKnowledgeSource(db_path=seeded_db)
    cases = src.get_cases()
    assert len(cases) >= 2
    assert all("timestamp" in c and "violation_types" in c for c in cases)


def test_indicator_limits(seeded_db):
    src = GraphKnowledgeSource(db_path=seeded_db)
    lim = src.get_indicator_limits()
    assert lim.get("COD") and "50" in lim["COD"]["value"]
    assert lim.get("AN") and "5" in lim["AN"]["value"]


def test_pattern_laws_dual_anchor(seeded_db):
    src = GraphKnowledgeSource(db_path=seeded_db)
    laws = src.get_pattern_laws("插瓶干扰")
    articles = {l["article"] for l in laws}
    assert "第三十九条" in articles and "第八十三条" in articles


def test_pattern_id_by_label(seeded_db):
    src = GraphKnowledgeSource(db_path=seeded_db)
    assert src.pattern_id_by_label("暗管偷排") == "pattern:secret_pipe"
    assert src.pattern_id_by_label("不存在") is None


def test_db_missing_fallback_observed(tmp_path):
    src = GraphKnowledgeSource(db_path=tmp_path / "nope.db")
    assert src.available is False
    fallback_data = [{"label": "兜底模式"}]
    pats = src.get_patterns(fallback=fallback_data)
    assert pats == fallback_data
    assert len(src.fallback_log) == 1
    assert src.fallback_log[0]["reason"] == "db_missing"
    # 构造不得建出空库文件（"图不存在"语义不被污染）
    assert not (tmp_path / "nope.db").exists()


def test_empty_graph_fallback(tmp_path):
    db = tmp_path / "empty.db"
    from shared.knowledge_graph.graph_store import GraphStore
    g = GraphStore(db)  # 构造即建空库
    g.close()
    src = GraphKnowledgeSource(db_path=db)
    pats = src.get_patterns(fallback=[{"label": "兜底"}])
    assert pats == [{"label": "兜底"}]
    assert src.fallback_log[-1]["reason"] == "empty_or_no_patterns"


def test_query_exception_fallback(seeded_db, monkeypatch):
    src = GraphKnowledgeSource(db_path=seeded_db)
    def boom(node_types=None, edge_types=None):
        raise RuntimeError("boom")
    monkeypatch.setattr(src._store, "subgraph", boom)
    pats = src.get_patterns(fallback=[{"label": "兜底"}])
    assert pats == [{"label": "兜底"}]
    assert src.fallback_log[-1]["reason"].startswith("error")
    # 熔断：异常后 available=False，后续查询不再撞库
    assert src.available is False


def test_usage_report(seeded_db):
    src = GraphKnowledgeSource(db_path=seeded_db)
    src.get_patterns()
    src.get_cases()
    report = src.usage_report()
    assert report["used_graph"] is True
    assert report["queries"] >= 2
    assert report["fallbacks"] == 0


def test_pattern_laws_respects_circuit_break(seeded_db, monkeypatch):
    """审查 Important-1 防回归：熔断后 get_pattern_laws 不再撞 neighbors。"""
    src = GraphKnowledgeSource(db_path=seeded_db)
    pid = src.pattern_id_by_label("插瓶干扰")
    assert pid is not None  # 先成功（缓存 pid）
    calls = {"n": 0}
    real_neighbors = src._store.neighbors
    def counting(*a, **kw):
        calls["n"] += 1
        raise RuntimeError("boom")
    monkeypatch.setattr(src._store, "neighbors", counting)
    src.get_pattern_laws("插瓶干扰", fallback=[])   # 第一次撞上并熔断
    assert src.available is False
    src.get_pattern_laws("插瓶干扰", fallback=[])   # 第二次必须直接回退
    src.get_pattern_laws("插瓶干扰", fallback=[])
    assert calls["n"] == 1, "熔断后不应再调 neighbors"
