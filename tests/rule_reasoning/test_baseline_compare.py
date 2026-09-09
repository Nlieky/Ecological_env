"""基线对比门：同输入下改造前后关键结论一致（子3阶段A验收门，用户红线）。

判定（spec）：suspicion_level / has_violation 一致率 100%；
violation_types 允许差异（知识源变化的目的）但打印供人审；
新行为：metadata.graph_usage 必须存在（回退观测）。

基线来源（快照固化于 tests/rule_reasoning/baselines/，git 入库）：
- 3 个历史 session 的真实产出（含 anomaly_result 输入的）；
- 4 个补生成：有 anomaly_result 无 rule 结果的 session，用改造前代码在临时目录跑出。

两种状态各验一遍（特殊警告#4）：
- 图在（KNOWLEDGE_GRAPH_DB=seed_importer 临时建库，确定性、不依赖
  gitignored 的开发库）：graph_usage.used_graph=True，知识=图谱+fallback 合并；
- KNOWLEDGE_GRAPH_DB 指向不存在路径（图挂）：全走 fallback 字典，
  关键结论也必须与基线一致（fallback 字典=原硬编码内容，一字不动）。
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from shared.knowledge_graph import seed_importer

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "subagents" / "rule-reasoning-agent" / "skills" / "rule-reasoning-core" / "scripts" / "run_rule_reasoning.py"
BASELINES = Path(__file__).parent / "baselines"

CASES = sorted([d for d in BASELINES.iterdir() if d.is_dir()]) if BASELINES.exists() else []


@pytest.fixture(scope="module")
def seeded_graph_db(tmp_path_factory):
    """确定性图谱库：seed_importer 临时建库（开发库同源），不依赖
    gitignored 的 shared/data/knowledge_graph.db——新 clone 也能跑图模式。"""
    db = tmp_path_factory.mktemp("kg") / "kg.db"
    seed_importer.run_seed(db_path=db)
    return db


def _run_reasoning(case_dir: Path, tmp_path: Path, extra_env: dict = None) -> Path:
    """在临时目录重放 case 输入并跑当前代码，返回工作目录。"""
    work = tmp_path / "s"
    work.mkdir()
    for f in ("anomaly_result.json", "data_result.json", "task.json"):
        src = case_dir / f
        if src.exists():
            shutil.copy2(src, work / f)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", **(extra_env or {})}
    r = subprocess.run(
        [sys.executable, str(SCRIPT),
         "--session-dir", str(work),
         "--anomaly-result", str(work / "anomaly_result.json")],
        capture_output=True, text=True, timeout=300, cwd=str(ROOT),
        env=env, encoding="utf-8", errors="replace")
    assert r.returncode == 0, f"stderr: {r.stderr[-800:]}"
    return work


def _compare_conclusions(case_dir: Path, new: dict, old: dict):
    """硬门：关键结论 100% 一致；软差异打印人审。"""
    assert new["result"]["suspicion_level"] == old["result"]["suspicion_level"], \
        f"suspicion 不一致: old={old['result']['suspicion_level']} new={new['result']['suspicion_level']}"
    assert new["result"]["has_violation"] == old["result"]["has_violation"], \
        f"has_violation 不一致: old={old['result']['has_violation']} new={new['result']['has_violation']}"
    # 软差异：打印人审（不 assert）
    if new["result"].get("violation_types") != old["result"].get("violation_types"):
        print(f"[人审] {case_dir.name} violation_types 差异: "
              f"old={old['result'].get('violation_types')} new={new['result'].get('violation_types')}")
    if new["result"].get("violation_type_names") != old["result"].get("violation_type_names"):
        print(f"[人审] {case_dir.name} violation_type_names 差异: "
              f"old={old['result'].get('violation_type_names')} new={new['result'].get('violation_type_names')}")
    if new["result"].get("conclusion") != old["result"].get("conclusion"):
        print(f"[人审] {case_dir.name} conclusion 差异: "
              f"old={old['result'].get('conclusion')} new={new['result'].get('conclusion')}")


def test_baselines_present():
    """哨兵：基线快照缺失时显式失败，而不是参数化静默跳过 0 个用例。"""
    assert len(CASES) >= 4, \
        f"基线快照不足: {len(CASES)} 个（期望>=4），目录 {BASELINES}"


@pytest.mark.parametrize("case_dir", CASES, ids=lambda d: d.name)
def test_conclusion_consistency_graph(case_dir, tmp_path, seeded_graph_db):
    """图在（seed 确定性库）：知识=图谱+fallback 合并，关键结论必须与基线一致。"""
    work = _run_reasoning(case_dir, tmp_path,
                          extra_env={"KNOWLEDGE_GRAPH_DB": str(seeded_graph_db)})
    new = json.loads((work / "rule_reasoning_result.json").read_text(encoding="utf-8"))
    old = json.loads((case_dir / "rule_reasoning_result.json").read_text(encoding="utf-8"))
    _compare_conclusions(case_dir, new, old)
    # 新行为：graph_usage 观测字段在且走的是图谱
    gu = (new.get("metadata") or {}).get("graph_usage")
    assert gu is not None and "used_graph" in gu, f"缺 graph_usage: {new.get('metadata')}"
    assert gu["used_graph"] is True, f"库存在时应走图谱: {gu}"


@pytest.mark.parametrize("case_dir", CASES, ids=lambda d: d.name)
def test_conclusion_consistency_fallback(case_dir, tmp_path):
    """图挂（KNOWLEDGE_GRAPH_DB 指向不存在路径）：全走 fallback 字典，
    关键结论同样必须与基线一致（fallback=原硬编码内容）。"""
    work = _run_reasoning(case_dir, tmp_path,
                          extra_env={"KNOWLEDGE_GRAPH_DB": str(tmp_path / "no_such.db")})
    new = json.loads((work / "rule_reasoning_result.json").read_text(encoding="utf-8"))
    old = json.loads((case_dir / "rule_reasoning_result.json").read_text(encoding="utf-8"))
    _compare_conclusions(case_dir, new, old)
    gu = (new.get("metadata") or {}).get("graph_usage")
    assert gu is not None and gu["used_graph"] is False, \
        f"库不存在时应回退并观测到: {gu}"
    assert gu["fallbacks"] > 0, f"回退必须被观测到: {gu}"
