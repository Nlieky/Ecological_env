# tests/knowledge_graph/test_seed_importer.py
"""种子导入集成测：真实文件跑通 + 幂等 + 核心关系边存在 + 单源缺失降级。"""
from pathlib import Path

import pytest

from shared.knowledge_graph.graph_store import GraphStore

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def seeded_store(tmp_path) -> GraphStore:
    from shared.knowledge_graph import seed_importer
    db = tmp_path / "kg.db"
    seed_importer.run_seed(db_path=db)
    return GraphStore(db)


def test_seed_produces_full_graph(seeded_store):
    # 真实数据全量 = 2厂+7指标+6模式+2法规+38算子(config31+specialized7)+2案例
    #              +11智能体/服务 = 68 节点。原计划写 >120 是期初错误估算
    # （spec 以为 operator_config 只有 17+ 个算子，实际 38），勿为凑数造假节点。
    st = seeded_store.stats()
    assert st["nodes"] >= 60, f"节点数不足: {st['nodes']}"
    # involves（案例→厂/指标）历史案例无厂字段，留给子项目3研判写回补；
    # writes 审计后无真实依据边（_WRITES 留空表保结构）。种子产出其余边型。
    expected_edges = {"monitors", "detects", "indicates", "cites", "employs",
                      "calls", "orchestrates", "reads", "uses"}
    missing = expected_edges - set(st["edge_types"].keys())
    assert not missing, f"缺边类型: {missing}"


def test_seed_core_relations(seeded_store):
    # 插瓶干扰有 detects 入边
    nb = seeded_store.neighbors("pattern:bottle_interference",
                                edge_types=["detects"], direction="in", depth=1)
    assert "operator:specialized:constant_detector" in {
        n["id"] for n in nb["nodes"]}
    # 稀释排放 → 水污染防治法§83
    nb2 = seeded_store.neighbors("pattern:dilution_discharge",
                                 edge_types=["indicates"], direction="out", depth=1)
    assert "regulation:water_law_s83" in {n["id"] for n in nb2["nodes"]}
    # 金桥厂 monitors 至少 5 个指标
    nb3 = seeded_store.neighbors("plant:当阳市金桥污水处理厂一期",
                                 edge_types=["monitors"], direction="out", depth=1)
    assert len(nb3["nodes"]) >= 5


def test_seed_idempotent(tmp_path):
    from shared.knowledge_graph import seed_importer
    db = tmp_path / "kg.db"
    seed_importer.run_seed(db_path=db)
    g1 = GraphStore(db); s1 = g1.stats(); g1.close()
    seed_importer.run_seed(db_path=db)  # 重跑
    g2 = GraphStore(db); s2 = g2.stats(); g2.close()
    assert s1 == s2, "重跑种子后图变化（幂等被破坏）"


def test_seed_missing_source_skips(tmp_path, monkeypatch):
    """单源文件缺失：跳过该源其余继续，退出码 0，且不产生悬挂边。"""
    from shared.knowledge_graph import seed_importer
    monkeypatch.setattr(seed_importer, "_OPERATOR_CONFIG",
                        ROOT / "nonexistent" / "operator_config.json")
    db = tmp_path / "kg.db"
    assert seed_importer.run_seed(db_path=db) == 0
    g = GraphStore(db)
    st = g.stats()
    assert st["node_types"].get("operator", 0) == 0  # 算子源被跳过
    assert st["node_types"].get("plant", 0) >= 1     # 厂还在
    # 算子端点的关系边一并丢弃（detects/employs 的端点全是 operator 节点）
    assert st["edge_types"].get("detects", 0) == 0
    assert st["edge_types"].get("employs", 0) == 0
    # 模式/法规源不受影响；篡改类双连后 6 模式 → 8 条 indicates（审计修正）
    assert st["edge_types"].get("indicates", 0) == 11  # 2026-09-09 裁决补全 §39 后 8→11
    # 数据完整性：任一边两端都必须是存在的节点（直查 sqlite，绕开
    # subgraph/neighbors 会静默丢悬挂边的 JOIN 过滤）
    import sqlite3
    conn = sqlite3.connect(db)
    dangling = conn.execute(
        "SELECT e.src, e.dst FROM edges e "
        "WHERE e.src NOT IN (SELECT id FROM nodes) "
        "   OR e.dst NOT IN (SELECT id FROM nodes)").fetchall()
    conn.close()
    assert not dangling, f"悬挂边: {dangling}"
    g.close()


def test_seed_yaml_missing_skips(tmp_path, monkeypatch):
    """层级 yaml 缺失：厂区源跳过（不抛 FileNotFoundError），其余源继续。"""
    from shared.knowledge_graph import seed_importer
    monkeypatch.setattr(seed_importer, "_HIERARCHY_FILE",
                        ROOT / "nonexistent" / "plant-hierarchy.yaml")
    db = tmp_path / "kg.db"
    assert seed_importer.run_seed(db_path=db) == 0
    g = GraphStore(db)
    st = g.stats()
    assert st["node_types"].get("plant", 0) == 0         # 厂区源被跳过
    assert st["node_types"].get("operator", 0) >= 30     # 算子源还在
    assert st["node_types"].get("violation_pattern", 0) == 6
    assert st["edge_types"].get("monitors", 0) == 0      # 无厂 → 无 monitors 边
    g.close()


def test_seed_influx_unreachable_fallback(tmp_path, monkeypatch):
    """InfluxDB 不可达：指标回退固定清单。"""
    from shared.knowledge_graph import seed_importer
    monkeypatch.setenv("INFLUXDB_URL", "http://127.0.0.1:1")
    db = tmp_path / "kg.db"
    seed_importer.run_seed(db_path=db)
    g = GraphStore(db)
    nb = g.neighbors("plant:当阳市金桥污水处理厂一期",
                     edge_types=["monitors"], direction="out", depth=1)
    assert len(nb["nodes"]) >= 5  # 回退清单 7 指标
    g.close()
