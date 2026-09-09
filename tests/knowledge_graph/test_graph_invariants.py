# tests/knowledge_graph/test_graph_invariants.py
"""图谱语义守卫：种子导入后自动校验关键不变量（审计 2026-09-09 发现 10 错边后立的规矩）。
每条断言对应一次真实审计错误——改映射表前先想清楚是否真的要改这里。"""
from pathlib import Path
import json

import pytest

from shared.knowledge_graph.graph_store import GraphStore
from shared.knowledge_graph import seed_importer

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def g(tmp_path_factory):
    db = tmp_path_factory.mktemp("inv") / "kg.db"
    seed_importer.run_seed(db_path=db)
    return GraphStore(db)


def _detects_targets(g, op_id):
    nb = g.neighbors(op_id, edge_types=["detects"], direction="out", depth=1)
    return {n["id"] for n in nb["nodes"]}


def test_detects_no_method_definition_mismatch(g):
    """造假检测(在场数据统计)不得连恶意逃避(数据缺失型)——方法与定义错位"""
    assert "pattern:malicious_evasion" not in _detects_targets(g, "operator:specialized:forgery_detector")
    assert "pattern:malicious_evasion" not in _detects_targets(g, "operator:machine_learning:isolation_forest")


def test_change_point_edge_note_is_honest(g):
    """突变→稀释的边注必须声明它是共有前提而非独立判定。
    注意断言用"共有前提"——旧夸大版"稀释排放的突变前提"也含"前提"二字，
    只查"前提"拦不住回退。"""
    row = g._conn.execute(
        "SELECT props_json FROM edges WHERE src=? AND dst=? AND type='detects'",
        ("operator:specialized:change_point_detector", "pattern:dilution_discharge")).fetchone()
    assert row is not None
    note = json.loads(row[0]).get("note", "")
    assert "共有前提" in note, f"边注未声明共有前提语义: {note}"
    assert "process_validator" in note, f"边注未指出真实判定方 process_validator: {note}"


def test_false_shutdown_indicates_s23(g):
    """虚假停产→§23（虚假申报类），不得回退到 §83——审计硬错防回归"""
    nb = g.neighbors("pattern:false_shutdown", edge_types=["indicates"], direction="out", depth=1)
    ids = {n["id"] for n in nb["nodes"]}
    assert "regulation:water_law_s23" in ids
    assert "regulation:water_law_s83" not in ids


def test_tampering_has_penalty_anchor(g):
    """篡改类(插瓶/人工拟合)必须双连禁止条款与罚则(§23/§39+§83)"""
    for pid in ("pattern:bottle_interference", "pattern:artificial_fitting"):
        nb = g.neighbors(pid, edge_types=["indicates"], direction="out", depth=1)
        ids = {n["id"] for n in nb["nodes"]}
        assert "regulation:water_law_s83" in ids, f"{pid} 缺罚则锚点 §83"
        assert "regulation:water_law_s23" in ids, f"{pid} 缺 §23 锚点"


def test_anomaly_agent_employs_all_five_feature_detectors(g):
    """②异常检测实际用 5 个特征算子，图上必须 5 条 employs（run_anomaly_detection_simple.py:25-27,266-269）"""
    nb = g.neighbors("agent:anomaly-detection", edge_types=["employs"], direction="out", depth=1)
    ops = {n["id"] for n in nb["nodes"]}
    expected = {"operator:specialized:constant_detector",
                "operator:specialized:change_point_detector",
                "operator:specialized:trend_detector",
                "operator:specialized:periodicity_detector",
                "operator:specialized:high_freq_detector"}
    assert expected <= ops, f"缺: {expected - ops}"
    # 孤立森林也真实在用（特征与打分两阶段），employs 保留但不得错连恶意逃避
    assert "operator:machine_learning:isolation_forest" in ops


def test_no_unevidenced_read_write_edges(g):
    """审计删掉的零依据读写边不得复活"""
    rows = g._conn.execute(
        "SELECT src, dst, type FROM edges WHERE type IN ('reads','writes')").fetchall()
    pairs = {(r["src"], r["dst"], r["type"]) for r in rows}
    assert ("agent:rule-reasoning", "service:sqlite_logs", "reads") not in pairs
    assert ("agent:disposition-execution", "service:sqlite_logs", "writes") not in pairs


def test_master_skills_include_installed(g):
    """主智能体技能含近期安装的 plant-onboarding/regulation-lookup（skills/ 目录实存）"""
    nb = g.neighbors("agent:master", edge_types=["uses"], direction="out", depth=1)
    skills = {n["id"] for n in nb["nodes"]}
    assert "skill:plant-onboarding" in skills and "skill:regulation-lookup" in skills


def test_malicious_evasion_desc_matches_source(g):
    """恶意逃避的 desc 必须是 §1.4 数据缺失型定义，不得回退到停产申报类（那是 false_shutdown 的特征）"""
    node = g.get_node("pattern:malicious_evasion")
    assert "数据缺失" in node["props"]["desc"]


def test_seed_reimport_purges_removed_edges(tmp_path):
    """重灌种子会清掉映射表删掉的边（审计时旧错边在真实库残留的根因）"""
    db = tmp_path / "kg.db"
    seed_importer.run_seed(db_path=db)
    conn = GraphStore(db)
    # 造一条映射表里已不存在的种子型边，重灌后必须消失
    conn.upsert_edge("agent:rule-reasoning", "service:sqlite_logs", "reads",
                     {"note": "人为塞回的审计错边"})
    seed_importer.run_seed(db_path=db)
    conn2 = GraphStore(db)
    rows = conn2._conn.execute(
        "SELECT 1 FROM edges WHERE src='agent:rule-reasoning' "
        "AND dst='service:sqlite_logs' AND type='reads'").fetchall()
    assert not rows, "重灌未清理已删除映射的陈旧边"
    # cites（研判沉淀共用）不在清理范围：手动写的 cites 边必须幸存
    conn2.upsert_edge("case:guard_probe", "pattern:dilution_discharge", "cites")
    seed_importer.run_seed(db_path=db)
    conn3 = GraphStore(db)
    survived = conn3._conn.execute(
        "SELECT 1 FROM edges WHERE src='case:guard_probe' "
        "AND dst='pattern:dilution_discharge' AND type='cites'").fetchall()
    assert survived, "重灌误删了研判沉淀的 cites 边"


def test_an_limit_note_clarifies_parenthesis(g):
    """AN 限值 5(8) 的括号含义必须写明（原边注让 8 像另一个限值）"""
    row = g._conn.execute(
        "SELECT props_json FROM edges WHERE src='indicator:AN' "
        "AND dst='regulation:gb18918' AND type='limits'").fetchone()
    assert row is not None
    props = json.loads(row[0])
    assert props.get("value") == "5(8) mg/L"
    assert "12" in props.get("note", "")
