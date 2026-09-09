# tests/knowledge_graph/test_graph_query_tool.py
"""graph-query 技能脚本：三种查询模式+紧凑JSON输出+图缺失优雅退出。"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "subagents" / "rule-reasoning-agent" / "skills" / "graph-query" / "scripts" / "query_graph.py"


@pytest.fixture(scope="module")
def seeded_db(tmp_path_factory):
    from shared.knowledge_graph import seed_importer
    db = tmp_path_factory.mktemp("gqt") / "kg.db"
    seed_importer.run_seed(db_path=db)
    return db


def run(args, db):
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(SCRIPT)] + args,
        capture_output=True, text=True, timeout=60, cwd=str(ROOT),
        # 子进程 -X utf8 写 UTF-8；父进程默认 cp936 解码中文会乱码（对齐
        # test_baseline_compare.py 的做法，显式指定解码编码）
        encoding="utf-8", errors="replace",
        env={**os.environ, "KNOWLEDGE_GRAPH_DB": str(db)})


def last_json(stdout: str):
    return json.loads(stdout.strip().splitlines()[-1])


def test_pattern_query(seeded_db):
    r = run(["--pattern", "插瓶干扰"], seeded_db)
    assert r.returncode == 0, r.stderr[-300:]
    d = last_json(r.stdout)
    assert d["label"] == "插瓶干扰"
    articles = [str(l.get("article", "")) for l in d["laws"]]
    assert any("第三十九条" in a for a in articles), d  # 审计修正后 §39 锚
    assert any("第八十三条" in a for a in articles)
    assert "detects" in d and isinstance(d["detects"], list)
    assert "cases" in d and isinstance(d["cases"], list)


def test_cases_query(seeded_db):
    r = run(["--cases"], seeded_db)
    d = last_json(r.stdout)
    assert len(d["cases"]) >= 2  # 种子案例
    assert all("timestamp" in c for c in d["cases"])


def test_cases_plant_filter(seeded_db):
    # --plant 过滤 involves 的厂（种子案例无 involves → 过滤后 0）
    r = run(["--cases", "--plant", "当阳市金桥污水处理厂一期"], seeded_db)
    d = last_json(r.stdout)
    assert d["cases"] == []


def test_law_query(seeded_db):
    r = run(["--law", "人工拟合"], seeded_db)
    d = last_json(r.stdout)
    assert len(d["laws"]) >= 2  # §39+§83 双锚


def test_missing_db_exit_clean(tmp_path):
    r = run(["--pattern", "插瓶干扰"], tmp_path / "nope.db")
    assert r.returncode == 0  # 不崩
    assert last_json(r.stdout).get("error") == "graph_unavailable"


def test_unknown_pattern(seeded_db):
    r = run(["--pattern", "不存在的模式"], seeded_db)
    assert r.returncode == 0
    d = last_json(r.stdout)
    assert d.get("error") == "pattern_not_found" or d.get("label") is None


def test_output_compact(seeded_db):
    r = run(["--pattern", "插瓶干扰"], seeded_db)
    last_line = r.stdout.strip().splitlines()[-1]
    assert len(last_line) < 2000
    assert "\n" not in last_line.strip()


def test_no_args_usage_hint():
    r = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPT)],
                       capture_output=True, text=True, timeout=60,
                       encoding="utf-8", errors="replace",
                       env={**os.environ, "KNOWLEDGE_GRAPH_DB": "unused"})
    assert r.returncode == 0
    d = last_json(r.stdout)
    assert d.get("error") == "usage"
