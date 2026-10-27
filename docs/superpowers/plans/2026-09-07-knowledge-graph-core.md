# 知识图谱核心（子项目 1/4）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建 SQLite 知识图谱库（shared/ 第四库）+ 种子导入 + 查询 API + `/agents/knowledge` 可视化页面，为后续推理底座/沉淀闭环/根因分析打地基。

**Architecture:** `shared/knowledge_graph/` 独立包（graph_store 存储层 + seed_importer 种子），backend 加一个只读路由文件挂 `/api/v1/knowledge`，前端加一个视图（Tab 切换领域知识/服务拓扑两个力导向子图）+ 一个 api module。图谱库对 backend 与子智能体（subprocess）都是可直连的共享资源。

**Tech Stack:** Python 3.12 + sqlite3（标准库，无新依赖）· FastAPI · Vue 3 + TypeScript + ECharts Graph（已在 `src/lib/echarts.ts` 注册，零构建改动）· pytest / Vitest

**Spec:** `docs/superpowers/specs/2026-09-07-knowledge-graph-core-design.md`

---

## 工程约定（执行前必读）

- **Python 一律用 venv 全路径**：`E:\project\Ecological_env\ecological_env\Scripts\python.exe`（下文以 `$PY` 代称；Git Bash 下为 `/e/project/Ecological_env/ecological_env/Scripts/python.exe`）。裸 `python` 是全局解释器，缺依赖。
- **pytest**：`$PY -m pytest tests/knowledge_graph/ -v`（pyproject 已配 testpaths=tests）。种子测试在本机 InfluxDB 运行时跑真实发现；不可达自动回退清单，不 skip。
- **前端测试/构建**：`cd frontend && npm test`（Vitest run）；页面人工验收在 http://localhost:5173/agents/knowledge。
- **提交**：每任务一提交，消息中文、`feat(graph)/test(graph)/docs` 前缀，结尾加 `Co-Authored-By: Claude <noreply@anthropic.com>`。
- **创建文件总览**：

```
shared/knowledge_graph/
├── __init__.py            # 导出 GraphStore
├── graph_store.py         # 存储+查询（nodes/edges/meta 3 表）
├── seed_importer.py       # 种子导入（可执行脚本）
backend/api/v1/knowledge/
├── __init__.py            # 空
└── routes.py              # 3 只读端点
frontend/src/api/modules/knowledge.ts       # API 封装
frontend/src/stores/knowledge.ts            # 图数据 store + ECharts 转换
frontend/src/views/KnowledgeGraphView.vue   # /agents/knowledge 页面
tests/knowledge_graph/
├── test_graph_store.py    # 存储层单测
├── test_seed_importer.py  # 种子集成测
└── test_api_routes.py     # 路由测试
frontend/src/stores/__tests__/knowledge.spec.ts
```

---

### Task 1: 图谱存储层 GraphStore

**Files:**
- Create: `shared/knowledge_graph/__init__.py`
- Create: `shared/knowledge_graph/graph_store.py`
- Test: `tests/knowledge_graph/test_graph_store.py`

- [ ] **Step 1: 写失败的单测**

```python
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `$PY -m pytest tests/knowledge_graph/test_graph_store.py -v`
Expected: FAIL —— `ModuleNotFoundError: No module named 'shared.knowledge_graph'`

- [ ] **Step 3: 实现完整的 graph_store.py**

实现要点（写代码时遵守）：
- 递归 CTE 里 **depth 用字面量内插**（`int(depth)` 校验后 f-string，无注入面），**edge_types 经 EDGE_TYPES 白名单校验后内插引号字面量**，**node_id 用命名参数 `:nid`**——把参数绑定从"数 `?` 个数"降为单参数，杜绝顺序错位 bug。
- `neighbors` 返回的 edges = 起点与结果集之间的全部边（`_edges_between`）。
- 同一节点多路径到达时 Python 侧取最小深度。

```python
# shared/knowledge_graph/__init__.py
from .graph_store import GraphStore

__all__ = ["GraphStore"]
```

```python
# shared/knowledge_graph/graph_store.py
"""知识图谱 SQLite 存储层（shared/ 第四库的存储+查询核心）。

设计要点：
- 3 张表 nodes/edges/meta；节点 id 形如 "type:slug"（英文 slug，中文进 label；
  例外：plant 节点 id 保留真实中文 plant_id，与 InfluxDB tag 一致，活图叠加直接匹配）
- 边 UNIQUE(src,dst,type) 幂等；写入只走 upsert
- 多跳邻居用递归 CTE（推理场景）；寻路用 Python BFS（根因场景）
- depth 硬上限 4（超限抛 ValueError，防递归 CTE 失控）
- WAL 模式；研判写回与种子重跑靠短事务 + UNIQUE 兜底
"""
from __future__ import annotations

import json
import sqlite3
from collections import deque
from pathlib import Path
from typing import Dict, List, Optional

MAX_DEPTH = 4

_SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes(
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    label TEXT NOT NULL,
    props_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS edges(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    src TEXT NOT NULL,
    dst TEXT NOT NULL,
    type TEXT NOT NULL,
    props_json TEXT NOT NULL DEFAULT '{}',
    UNIQUE(src, dst, type)
);
CREATE TABLE IF NOT EXISTS meta(
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src, type);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst, type);
CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);
"""

NODE_TYPES = {
    "plant", "indicator", "violation_pattern", "operator",
    "regulation", "case", "agent", "service",
}
EDGE_TYPES = {
    "monitors", "detects", "indicates", "cites", "employs",
    "calls", "orchestrates", "reads", "writes", "involves",
}


def _row_to_node(row: sqlite3.Row) -> Dict:
    return {"id": row["id"], "type": row["type"], "label": row["label"],
            "props": json.loads(row["props_json"] or "{}")}


def _row_to_edge(row: sqlite3.Row) -> Dict:
    return {"id": row["id"], "src": row["src"], "dst": row["dst"],
            "type": row["type"], "props": json.loads(row["props_json"] or "{}")}


class GraphStore:
    def __init__(self, db_path: Path | str):
        self.db_path = str(db_path)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ---------- 写入 ----------
    def upsert_node(self, node_id: str, ntype: str, label: str,
                    props: Optional[Dict] = None) -> None:
        if ntype not in NODE_TYPES:
            raise ValueError(f"未知节点类型: {ntype}")
        self._conn.execute(
            """INSERT INTO nodes(id, type, label, props_json) VALUES(?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 type=excluded.type, label=excluded.label,
                 props_json=excluded.props_json""",
            (node_id, ntype, label, json.dumps(props or {}, ensure_ascii=False)))
        self._conn.commit()

    def upsert_edge(self, src: str, dst: str, etype: str,
                    props: Optional[Dict] = None) -> None:
        if etype not in EDGE_TYPES:
            raise ValueError(f"未知边类型: {etype}")
        self._conn.execute(
            """INSERT INTO edges(src, dst, type, props_json) VALUES(?, ?, ?, ?)
               ON CONFLICT(src, dst, type) DO UPDATE SET
                 props_json=excluded.props_json""",
            (src, dst, etype, json.dumps(props or {}, ensure_ascii=False)))
        self._conn.commit()

    def set_meta(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
        self._conn.commit()

    def get_meta(self, key: str) -> Optional[str]:
        row = self._conn.execute(
            "SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None

    # ---------- 查询 ----------
    def get_node(self, node_id: str) -> Optional[Dict]:
        row = self._conn.execute(
            "SELECT * FROM nodes WHERE id=?", (node_id,)).fetchone()
        return _row_to_node(row) if row else None

    def seeded(self) -> bool:
        """是否跑过种子（meta 记录 last_seeded_at）。"""
        return self.get_meta("last_seeded_at") is not None

    def neighbors(self, node_id: str,
                  edge_types: Optional[List[str]] = None,
                  direction: str = "both",
                  depth: int = 1) -> Dict:
        """递归 CTE 多跳邻居（不含起点）。

        direction: out=只顺边 / in=只逆边 / both=双向（默认）。
        返回 {nodes: [{id,type,label,props,depth}], edges: [...], depth}；
        nodes 同点多路径取最小 depth；edges 为起点+结果集内部之间的边。
        """
        if not isinstance(depth, int) or depth < 1 or depth > MAX_DEPTH:
            raise ValueError(f"depth 必须在 1..{MAX_DEPTH}")
        if direction not in ("out", "in", "both"):
            raise ValueError("direction 必须是 out/in/both")
        ets = list(edge_types or [])
        for et in ets:
            if et not in EDGE_TYPES:
                raise ValueError(f"未知边类型: {et}")
        # edge_types 白名单校验后内插（注入安全）；depth 为校验过的 int 字面量
        et_sql = (f" AND e.type IN ({','.join(repr(e) for e in ets)})'"
                  .replace('"', "'")) if ets else ""
        et_sql = f" AND e.type IN ({','.join(chr(39)+e+chr(39) for e in ets)})" if ets else ""
        d_sql = str(depth)

        if direction == "out":
            base = (f"SELECT e.dst AS nxt, 1 AS d FROM edges e "
                    f"WHERE e.src = :nid{et_sql}")
            rec = (f"SELECT e.dst AS nxt, r.d + 1 AS d FROM edges e "
                   f"JOIN reach r ON e.src = r.nxt WHERE r.d < {d_sql}{et_sql}")
        elif direction == "in":
            base = (f"SELECT e.src AS nxt, 1 AS d FROM edges e "
                    f"WHERE e.dst = :nid{et_sql}")
            rec = (f"SELECT e.src AS nxt, r.d + 1 AS d FROM edges e "
                   f"JOIN reach r ON e.dst = r.nxt WHERE r.d < {d_sql}{et_sql}")
        else:  # both
            base = (f"SELECT e.dst AS nxt, 1 AS d FROM edges e "
                    f"WHERE e.src = :nid{et_sql} "
                    f"UNION SELECT e.src AS nxt, 1 AS d FROM edges e "
                    f"WHERE e.dst = :nid{et_sql}")
            rec = (f"SELECT nxt, d + 1 AS d FROM ("
                   f"SELECT e.dst AS nxt, r.d AS d FROM edges e "
                   f"JOIN reach r ON e.src = r.nxt WHERE r.d < {d_sql}{et_sql} "
                   f"UNION SELECT e.src AS nxt, r.d AS d FROM edges e "
                   f"JOIN reach r ON e.dst = r.nxt WHERE r.d < {d_sql}{et_sql})")
        sql = (f"WITH RECURSIVE reach(nxt, d) AS ({base} UNION {rec}) "
               f"SELECT n.id, n.type, n.label, n.props_json, reach.d AS d "
               f"FROM reach JOIN nodes n ON n.id = reach.nxt "
               f"WHERE n.id != :nid ORDER BY d, n.id")
        rows = self._conn.execute(sql, {"nid": node_id}).fetchall()

        best: Dict[str, Dict] = {}  # id -> 最小深度节点
        for r in rows:
            nid = r["id"]
            if nid not in best or r["d"] < best[nid]["depth"]:
                best[nid] = {"id": nid, "type": r["type"], "label": r["label"],
                             "props": json.loads(r["props_json"] or "{}"),
                             "depth": r["d"]}
        edges = self._edges_between({node_id, *best.keys()})
        return {"nodes": list(best.values()), "edges": edges, "depth": depth}

    def _edges_between(self, node_ids: set) -> List[Dict]:
        if not node_ids:
            return []
        ph = ",".join("?" * len(node_ids))
        rows = self._conn.execute(
            f"SELECT * FROM edges WHERE src IN ({ph}) AND dst IN ({ph})",
            list(node_ids) * 2).fetchall()
        return [_row_to_edge(r) for r in rows]

    def subgraph(self, node_types: Optional[List[str]] = None,
                 edge_types: Optional[List[str]] = None) -> Dict:
        """按类型过滤取子图；边仅当两端节点都在结果内才保留。"""
        nq, nparams = "SELECT * FROM nodes", []
        if node_types:
            nq += " WHERE type IN (%s)" % ",".join("?" * len(node_types))
            nparams += node_types
        nodes = [_row_to_node(r) for r in
                 self._conn.execute(nq, nparams).fetchall()]
        ids = {n["id"] for n in nodes}
        eq, eparams = "SELECT * FROM edges", []
        if edge_types:
            eq += " WHERE type IN (%s)" % ",".join("?" * len(edge_types))
            eparams += edge_types
        all_edges = [_row_to_edge(r) for r in
                     self._conn.execute(eq, eparams).fetchall()]
        edges = [e for e in all_edges if e["src"] in ids and e["dst"] in ids]
        return {"nodes": nodes, "edges": edges}

    def shortest_path(self, a: str, b: str,
                      max_hops: int = 6) -> Optional[List[str]]:
        """BFS 寻路（无向语义），返回节点 id 序列；不可达返回 None。"""
        if a == b:
            return [a]
        visited = {a}
        queue = deque([(a, [a])])
        while queue:
            cur, path = queue.popleft()
            if len(path) > max_hops:
                continue
            rows = self._conn.execute(
                "SELECT dst FROM edges WHERE src=? "
                "UNION SELECT src FROM edges WHERE dst=?",
                (cur, cur)).fetchall()
            for r in rows:
                nxt = r[0]
                if nxt in visited:
                    continue
                if nxt == b:
                    return path + [nxt]
                visited.add(nxt)
                queue.append((nxt, path + [nxt]))
        return None

    def stats(self) -> Dict:
        nodes_by_type = {r["type"]: r["c"] for r in self._conn.execute(
            "SELECT type, COUNT(*) AS c FROM nodes GROUP BY type").fetchall()}
        edges_by_type = {r["type"]: r["c"] for r in self._conn.execute(
            "SELECT type, COUNT(*) AS c FROM edges GROUP BY type").fetchall()}
        return {"nodes": sum(nodes_by_type.values()),
                "edges": sum(edges_by_type.values()),
                "node_types": nodes_by_type, "edge_types": edges_by_type}

    def close(self) -> None:
        self._conn.close()
```

**注意**：上面 `neighbors` 里 `et_sql` 的第一行赋值是无效残留（被第二行立即覆盖），写文件时**只保留第二行**：

```python
        et_sql = (f" AND e.type IN ({','.join(chr(39)+e+chr(39) for e in ets)})"
                  if ets else "")
```

（`chr(39)` 是单引号；ets 已过白名单校验，内插安全。）

- [ ] **Step 4: 跑测试确认全绿**

Run: `$PY -m pytest tests/knowledge_graph/test_graph_store.py -v`
Expected: 14 个测试全 PASS。若报 `Incorrect number of bindings`，检查 `et_sql` 是否只赋值了一次、`:nid` 命名参数是否传的 `{"nid": node_id}`。

- [ ] **Step 5: 提交**

```bash
git add shared/knowledge_graph/ tests/knowledge_graph/test_graph_store.py
git commit -m "feat(graph): GraphStore 存储层——3表schema+幂等upsert+递归CTE邻居+BFS寻路+子图统计

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: 种子导入器

**Files:**
- Create: `shared/knowledge_graph/seed_importer.py`
- Test: `tests/knowledge_graph/test_seed_importer.py`
- Modify: `.gitignore`（追加 knowledge_graph.db）

- [ ] **Step 1: 写失败的集成测试**

```python
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
    st = seeded_store.stats()
    assert st["nodes"] > 120, f"节点数不足: {st['nodes']}"
    expected_edges = {"monitors", "detects", "indicates", "cites", "employs",
                      "calls", "orchestrates", "reads", "writes", "involves"}
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
    """单源文件缺失：跳过该源其余继续，退出码 0。"""
    from shared.knowledge_graph import seed_importer
    monkeypatch.setattr(seed_importer, "_OPERATOR_CONFIG",
                        ROOT / "nonexistent" / "operator_config.json")
    db = tmp_path / "kg.db"
    assert seed_importer.run_seed(db_path=db) == 0
    g = GraphStore(db)
    st = g.stats()
    assert st["node_types"].get("operator", 0) == 0  # 算子源被跳过
    assert st["node_types"].get("plant", 0) >= 1     # 厂还在
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `$PY -m pytest tests/knowledge_graph/test_seed_importer.py -v`
Expected: FAIL —— `cannot import name 'seed_importer'`

- [ ] **Step 3: 实现 seed_importer.py（完整文件）**

```python
# shared/knowledge_graph/seed_importer.py
"""知识图谱种子导入：从项目真实文件灌出初始图。

数据源（全部只读）：
  1. plant-hierarchy.yaml     → plant 节点（id 保留中文 plant_id，同 InfluxDB tag）
  2. 指标发现（CANONICAL_FIELDS 契约 + InfluxDB 触达校验，不可达回退 7 指标清单）
  3. 违规模式静态目录（对齐 violation_patterns.md/典型违规模式.md）→ pattern 节点
  4. operator_config.json     → operator 节点
  5. 硬编码关系映射表（算子↔模式↔法条↔智能体，均对到真实文件）→ 各类边
  6. historical_cases.json    → case 节点 + cites 边
  7. 智能体/服务静态目录      → agent/service 节点 + orchestrates/calls/reads/writes

种子幂等：节点 upsert、边 UNIQUE 去重；研判沉淀的 case（id 不在种子里）不受影响。
运行：ecological_env\\Scripts\\python.exe shared\\knowledge_graph\\seed_importer.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))  # 允许 python path/to/seed_importer.py 直跑

from shared.knowledge_graph.graph_store import GraphStore  # noqa: E402

_HIERARCHY_FILE = _ROOT / "shared" / "data" / "plant-hierarchy.yaml"
_OPERATOR_CONFIG = _ROOT / "shared" / "operators" / "config" / "operator_config.json"
_CASES_FILE = (_ROOT / "shared" / "knowledge" / "violation_patterns"
               / "historical_cases.json")
_DEFAULT_DB = _ROOT / "shared" / "data" / "knowledge_graph.db"

_FALLBACK_INDICATORS: List[Dict] = [
    {"field": "pH", "label": "pH", "unit": ""},
    {"field": "COD", "label": "COD", "unit": "mg/L"},
    {"field": "TN", "label": "总氮", "unit": "mg/L"},
    {"field": "AN", "label": "氨氮", "unit": "mg/L"},
    {"field": "TP", "label": "总磷", "unit": "mg/L"},
    {"field": "suspended_solids", "label": "悬浮物", "unit": "mg/L"},
    {"field": "flow", "label": "流量", "unit": "m³/h"},
]

PATTERNS: List[Dict] = [
    {"id": "pattern:bottle_interference", "label": "插瓶干扰",
     "props": {"status": "implemented",
               "desc": "采样位置放预置达标水样，指标恒定缺乏自然波动",
               "source": "violation_patterns.md §1.1"}},
    {"id": "pattern:artificial_fitting", "label": "人工拟合",
     "props": {"status": "degraded",
               "desc": "曲线过于平滑(smoothness<0.3 且 R²>0.95)，缺工况数据增强",
               "source": "violation_patterns.md §1.2"}},
    {"id": "pattern:dilution_discharge", "label": "稀释排放",
     "props": {"status": "implemented",
               "desc": "多指标同步突降+流量增大，稀释比例不一致",
               "source": "violation_patterns.md §1.3"}},
    {"id": "pattern:malicious_evasion", "label": "恶意逃避",
     "props": {"status": "todo",
               "desc": "停产申报类逃避检测，缺停产申报数据（TODO）",
               "source": "violation_patterns.md §1.4"}},
    {"id": "pattern:secret_pipe", "label": "暗管偷排",
     "props": {"status": "knowledge_only",
               "desc": "私设暗管逃避监管，知识库有定义无专用算子",
               "source": "典型违规模式.md 二"}},
    {"id": "pattern:false_shutdown", "label": "虚假停产",
     "props": {"status": "knowledge_only",
               "desc": "谎报停产实际偷排，知识库有定义无专用算子",
               "source": "典型违规模式.md 五"}},
]

REGULATIONS: List[Dict] = [
    {"id": "regulation:water_law_s23", "label": "水污染防治法§23",
     "props": {"law": "中华人民共和国水污染防治法", "article": "第二十三条",
               "note": "监测设备安装/运行/联网要求"}},
    {"id": "regulation:water_law_s83", "label": "水污染防治法§83",
     "props": {"law": "中华人民共和国水污染防治法", "article": "第八十三条",
               "note": "私设暗管等逃避监管方式排放的法律责任"}},
]

# operator → pattern (detects)；来源注释为证
_DETECTS: List[Tuple[str, str, str]] = [
    ("operator:specialized:constant_detector", "pattern:bottle_interference",
     "恒定检测 std/CV/唯一值三法（constant_detector.py）"),
    ("operator:specialized:change_point_detector", "pattern:dilution_discharge",
     "稀释排放的突变前提（run_anomaly_detection_simple.py 特征算子）"),
    ("operator:specialized:smoothness_detector", "pattern:artificial_fitting",
     "平滑度检测（smoothness_detector.py:104）"),
    ("operator:specialized:forgery_detector", "pattern:malicious_evasion",
     "造假检测四法（forgery_detector.py）"),
    ("operator:machine_learning:isolation_forest", "pattern:malicious_evasion",
     "孤立森林异常打分 a≥0.5"),
]
# pattern → regulation (indicates)；法条号来自典型违规模式.md 各节"违规定性"
_INDICATES: List[Tuple[str, str, str]] = [
    ("pattern:bottle_interference", "regulation:water_law_s23",
     "干扰采样监测，违反监测设备运行要求（§一）"),
    ("pattern:secret_pipe", "regulation:water_law_s83", "私设暗管（§二）"),
    ("pattern:dilution_discharge", "regulation:water_law_s83", "清水稀释（§三）"),
    ("pattern:artificial_fitting", "regulation:water_law_s23", "数据篡改（§四）"),
    ("pattern:false_shutdown", "regulation:water_law_s83", "虚假停产（§五）"),
    ("pattern:malicious_evasion", "regulation:water_law_s83", "恶意逃避监管"),
]
# agent → operator (employs)；来源 run_anomaly_detection_simple.py imports
_EMPLOYS: List[Tuple[str, str, str]] = [
    ("agent:anomaly-detection", "operator:specialized:constant_detector",
     "平稳特征检测"),
    ("agent:anomaly-detection", "operator:specialized:change_point_detector",
     "突变特征检测"),
    ("agent:anomaly-detection", "operator:machine_learning:isolation_forest",
     "孤立森林异常打分"),
]

AGENTS: List[Dict] = [
    {"id": "agent:master", "label": "主智能体",
     "props": {"role": "编排", "identity_files": 7, "max_iterations": 15}},
    {"id": "agent:multi-dimensional-data-perception", "label": "①多维数据感知",
     "props": {"role": "取数", "skills": ["data-perception-core", "data-export"]}},
    {"id": "agent:anomaly-detection", "label": "②异常检测",
     "props": {"role": "检测", "skills": ["anomaly-detection-core"]}},
    {"id": "agent:rule-reasoning", "label": "③规则推理",
     "props": {"role": "判定",
               "skills": ["rule-reasoning-core", "knowledge-search"]}},
    {"id": "agent:disposition-execution", "label": "④研判处置",
     "props": {"role": "处置",
               "skills": ["disposition-execution-core", "report-generator"]}},
]
SERVICES: List[Dict] = [
    {"id": "service:frontend", "label": "前端 :5173", "props": {"port": 5173}},
    {"id": "service:backend", "label": "Backend :8000", "props": {"port": 8000}},
    {"id": "service:agent_service", "label": "Agent 服务 :8642",
     "props": {"port": 8642}},
    {"id": "service:influxdb", "label": "InfluxDB :8086", "props": {"port": 8086}},
    {"id": "service:sqlite_logs", "label": "SQLite 日志库",
     "props": {"db": "ecological_logs.db"}},
    {"id": "service:llm", "label": "LLM ctgu-vlm",
     "props": {"endpoint": "http://172.xx.xx.xx:30000/v1"}},
]
_ORCHESTRATES = [
    ("agent:master", "agent:multi-dimensional-data-perception"),
    ("agent:master", "agent:anomaly-detection"),
    ("agent:master", "agent:rule-reasoning"),
    ("agent:master", "agent:disposition-execution"),
]
_CALLS = [
    ("service:frontend", "service:backend", "HTTP /api/*"),
    ("service:backend", "service:agent_service", "HTTP /query(/stream) 转发"),
    ("service:agent_service", "service:llm", "OpenAI 兼容 API"),
]
_READS = [
    ("agent:multi-dimensional-data-perception", "service:influxdb",
     "get_data 取数"),
    ("agent:rule-reasoning", "service:sqlite_logs", "审计追溯"),
]
_WRITES = [
    ("agent:disposition-execution", "service:sqlite_logs", "处置结果归档"),
]


def _import_plants(g: GraphStore) -> List[str]:
    """读层级 yaml，返回 plant_id 列表。"""
    import yaml
    data = yaml.safe_load(_HIERARCHY_FILE.read_text(encoding="utf-8")) or {}
    plant_ids: List[str] = []
    for city, districts in data.items():
        if not isinstance(districts, dict):
            continue
        for district, plants in districts.items():
            if not isinstance(plants, list):
                continue
            for pid in plants:
                g.upsert_node(f"plant:{pid}", "plant", pid,
                              {"city": city, "district": district})
                plant_ids.append(pid)
    return plant_ids


def _discover_indicators() -> List[Dict]:
    """CANONICAL_FIELDS 契约字段为基集；触达 InfluxDB 校验（不可达回退清单）。"""
    try:
        from shared.data.influxdb_query import CANONICAL_FIELDS
        from shared.data.discover_plants import discover_plants
        plants = discover_plants()  # 触达 InfluxDB；失败抛异常→回退
        label_map = {i["field"]: i["label"] for i in _FALLBACK_INDICATORS}
        unit_map = {i["field"]: i["unit"] for i in _FALLBACK_INDICATORS}
        out = []
        for f in CANONICAL_FIELDS:
            if f == "discharge":
                continue  # 累积量字段，不作独立指标节点
            out.append({"field": f, "label": label_map.get(f, f),
                        "unit": unit_map.get(f, "")})
        return out
    except Exception as e:
        print(f"[seed] InfluxDB 不可达({e})，指标用回退清单")
        return _FALLBACK_INDICATORS


def _import_indicators(g: GraphStore, indicators: List[Dict],
                       plant_ids: List[str]) -> int:
    for ind in indicators:
        g.upsert_node(f"indicator:{ind['field']}", "indicator",
                      ind["label"],
                      {"field": ind["field"], "unit": ind["unit"]})
        for pid in plant_ids:
            g.upsert_edge(f"plant:{pid}", f"indicator:{ind['field']}", "monitors")
    return len(indicators)


def _import_operators(g: GraphStore) -> int:
    if not _OPERATOR_CONFIG.exists():
        print(f"[seed] 警告: {_OPERATOR_CONFIG} 不存在，跳过算子源")
        return 0
    cfg = json.loads(_OPERATOR_CONFIG.read_text(encoding="utf-8"))
    n = 0
    for cat, block in cfg.get("operators", {}).items():
        for op_key, op in (block.get("operators") or {}).items():
            g.upsert_node(f"operator:{cat}:{op_key}", "operator",
                          op.get("name", op_key),
                          {"category": cat,
                           "sub_category": op.get("sub_category", ""),
                           "formula": op.get("formula", ""),
                           "desc": op.get("description", ""),
                           "status": op.get("status", "available"),
                           "priority": op.get("priority", 3)})
            n += 1
    # specialized 目录不在 config json 里，按文件补（对违规模式的专用检测器）
    spec_dir = _ROOT / "shared" / "operators" / "specialized"
    name_map = {"constant_detector": "恒定检测", "change_point_detector": "突变检测",
                "smoothness_detector": "平滑度检测", "forgery_detector": "造假检测",
                "trend_detector": "趋势检测", "periodicity_detector": "周期检测",
                "high_freq_detector": "高频波动检测"}
    for py in sorted(spec_dir.glob("*.py")):
        key = py.stem
        if key == "__init__":
            continue
        g.upsert_node(f"operator:specialized:{key}", "operator",
                      name_map.get(key, key),
                      {"category": "specialized", "desc": "专用违规模式检测器"})
        n += 1
    return n


def _import_cases(g: GraphStore) -> int:
    if not _CASES_FILE.exists():
        print(f"[seed] 警告: {_CASES_FILE} 不存在，跳过案例源")
        return 0
    data = json.loads(_CASES_FILE.read_text(encoding="utf-8"))
    pattern_ids = {p["id"] for p in PATTERNS}
    n = 0
    for case in data.get("cases", []):
        cid = (case.get("case_id") or "").removeprefix("case_")
        if not cid:
            continue
        violations = case.get("violations", [])
        vtypes = [v.get("type", "") for v in violations if v.get("type")]
        g.upsert_node(f"case:{cid}", "case", f"案例 {cid}",
                      {"timestamp": case.get("timestamp", ""),
                       "confidence": case.get("confidence", ""),
                       "reasoning": case.get("reasoning", ""),
                       "violation_types": vtypes})
        for vt in vtypes:  # cites: case → pattern
            if f"pattern:{vt}" in pattern_ids:
                g.upsert_edge(f"case:{cid}", f"pattern:{vt}", "cites")
        # involves: 历史案例无厂字段，研判写回时补（子项目3）
        n += 1
    return n


def _import_static_topology(g: GraphStore) -> int:
    for a in AGENTS:
        g.upsert_node(a["id"], "agent", a["label"], a["props"])
    for s in SERVICES:
        g.upsert_node(s["id"], "service", s["label"], s["props"])
    for src, dst in _ORCHESTRATES:
        g.upsert_edge(src, dst, "orchestrates")
    for src, dst, note in _CALLS:
        g.upsert_edge(src, dst, "calls", {"note": note})
    for src, dst, note in _READS:
        g.upsert_edge(src, dst, "reads", {"note": note})
    for src, dst, note in _WRITES:
        g.upsert_edge(src, dst, "writes", {"note": note})
    return len(AGENTS) + len(SERVICES)


def _import_relation_edges(g: GraphStore) -> int:
    for src, dst, note in _DETECTS:
        g.upsert_edge(src, dst, "detects", {"note": note})
    for src, dst, note in _INDICATES:
        g.upsert_edge(src, dst, "indicates", {"note": note})
    for src, dst, note in _EMPLOYS:
        g.upsert_edge(src, dst, "employs", {"note": note})
    return len(_DETECTS) + len(_INDICATES) + len(_EMPLOYS)


def run_seed(db_path=None) -> int:
    """跑全量种子。返回退出码（0=成功，含单源跳过）。"""
    g = GraphStore(db_path or _DEFAULT_DB)
    report: Dict[str, int] = {}
    plant_ids = _import_plants(g)
    report["plants"] = len(plant_ids)
    report["indicators"] = _import_indicators(
        g, _discover_indicators(), plant_ids)
    for p in PATTERNS:
        g.upsert_node(p["id"], "violation_pattern", p["label"], p["props"])
    report["patterns"] = len(PATTERNS)
    for r in REGULATIONS:
        g.upsert_node(r["id"], "regulation", r["label"], r["props"])
    report["regulations"] = len(REGULATIONS)
    report["operators"] = _import_operators(g)
    report["cases"] = _import_cases(g)
    report["agents_services"] = _import_static_topology(g)
    report["relation_edges"] = _import_relation_edges(g)
    g.set_meta("last_seeded_at", datetime.now().isoformat(timespec="seconds"))
    g.set_meta("schema_version", "1")
    st = g.stats()
    print(f"[seed] 完成: {json.dumps(report, ensure_ascii=False)}")
    print(f"[seed] 图规模: {st['nodes']} 节点 / {st['edges']} 边")
    g.close()
    return 0


if __name__ == "__main__":
    sys.exit(run_seed())
```

- [ ] **Step 4: 跑测试确认通过**

Run: `$PY -m pytest tests/knowledge_graph/test_seed_importer.py -v`
Expected: 5 个 PASS。本机 InfluxDB 正在运行（真实发现路径也会过）；停掉 InfluxDB 时 `test_seed_influx_unreachable_fallback` 验证回退。

- [ ] **Step 5: 真实库跑一次种子 + gitignore**

Run: `$PY shared/knowledge_graph/seed_importer.py`
Expected: `[seed] 完成: {...}` + `图规模: ~145 节点 / ~270 边`（2厂×7指标=14 monitors + 17算子 + 7 specialized + 6 模式 + 2 法规 + 2 案例 + 11 agents/services + 指标节点等）

```bash
grep -q "knowledge_graph.db" .gitignore || echo "shared/data/knowledge_graph.db" >> .gitignore
```

- [ ] **Step 6: 提交**

```bash
git add shared/knowledge_graph/seed_importer.py tests/knowledge_graph/test_seed_importer.py .gitignore
git commit -m "feat(graph): 种子导入器——7源导入+硬编码关系映射(算子↔模式↔法条)+幂等+InfluxDB回退

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: 后端 API 路由

**Files:**
- Create: `backend/api/v1/knowledge/__init__.py`（空文件）
- Create: `backend/api/v1/knowledge/routes.py`
- Modify: `backend/main.py`（agents config 路由注册块之后追加，约 :147）
- Test: `tests/knowledge_graph/test_api_routes.py`

- [ ] **Step 1: 写失败的 API 测试**

```python
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
    # 不用 with：跳过 startup（不拉起 metrics/prometheus 子进程）
    return TestClient(app)


def test_graph_endpoint_returns_full(client):
    r = client.get("/api/v1/knowledge/graph", params={"live": "false"})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["seeded"] is True
    assert len(body["nodes"]) > 120
    assert len(body["edges"]) > 200


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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `$PY -m pytest tests/knowledge_graph/test_api_routes.py -v`
Expected: FAIL —— `ModuleNotFoundError: No module named 'backend.api.v1.knowledge'`

- [ ] **Step 3: 实现路由**

```python
# backend/api/v1/knowledge/routes.py
"""知识图谱 API——只读 3 端点（/agents/knowledge 页面数据源）。

库不存在时返回空图 + seeded:false（前端显示引导卡片），不自动建库。
live=true 时把 /v1/system/status 的实时状态叠加到节点 props（查时合并，不落库）。
"""
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["知识图谱"])

_DB_PATH = Path(__file__).resolve().parents[3] / "shared" / "data" / "knowledge_graph.db"
_store_cache: Optional[object] = None


def _get_store():
    global _store_cache
    if _store_cache is not None:
        return _store_cache
    if not _DB_PATH.exists():
        return None
    from shared.knowledge_graph import GraphStore
    _store_cache = GraphStore(_DB_PATH)
    return _store_cache


async def _overlay_live_status(nodes: list) -> None:
    """查时合并：各厂数据新鲜度叠加到 plant 节点 props。失败不影响主图。"""
    try:
        from backend.api.v1.system.routes import get_system_status
        status = await get_system_status()
        data = status.get("data", status)  # 兼容有无 envelope
        plant_fresh = {p.get("plant_id"): p for p in data.get("plants", [])}
        for n in nodes:
            if n["type"] == "plant":
                info = plant_fresh.get(n["id"].split(":", 1)[1])
                if info:
                    n["props"]["last_data_ts"] = info.get("latest_time", "")
    except Exception:
        pass


@router.get("/knowledge/graph")
async def get_graph(node_types: str = "", edge_types: str = "",
                    live: bool = True):
    store = _get_store()
    if store is None:
        return {"success": True, "seeded": False, "nodes": [],
                "edges": [], "stats": {}}
    nt = [t for t in node_types.split(",") if t]
    et = [t for t in edge_types.split(",") if t]
    sg = store.subgraph(node_types=nt or None, edge_types=et or None)
    if live:
        await _overlay_live_status(sg["nodes"])
    return {"success": True, "seeded": True, **sg, "stats": store.stats()}


@router.get("/knowledge/node/{node_id}")
async def get_node(node_id: str):
    store = _get_store()
    if store is None:
        raise HTTPException(404, "知识图谱未初始化")
    node = store.get_node(node_id)
    if node is None:
        raise HTTPException(404, f"节点不存在: {node_id}")
    nb = store.neighbors(node_id, depth=1)
    grouped: dict = {}
    for n in nb["nodes"]:
        grouped.setdefault(n["type"], []).append(n)
    return {"success": True, "node": node, "neighbors": grouped}


@router.get("/knowledge/stats")
async def get_stats():
    store = _get_store()
    if store is None:
        return {"success": True, "seeded": False, "nodes": 0, "edges": 0,
                "node_types": {}, "edge_types": {}, "case_count": 0}
    st = store.stats()
    st["case_count"] = st["node_types"].get("case", 0)
    st["seeded"] = True
    return {"success": True, **st}
```

**实现前先读** `backend/api/v1/system/routes.py` 的 `get_system_status` 返回形状（有无 `{"data": ...}` envelope、plants 数组字段名是否为 `plant_id`/`latest_time`），按真实字段名对齐 `_overlay_live_status`——上面代码按 `data.plants[].plant_id/latest_time` 写，若实际形状不同以实际为准调整取值路径。

- [ ] **Step 4: 注册路由**

`backend/main.py` 在 agents config 的 `include_router` 之后追加：

```python
# 知识图谱(shared/knowledge_graph 第四库只读端点)
from backend.api.v1.knowledge import routes as v1_knowledge_routes
app.include_router(v1_knowledge_routes.router, prefix="/api/v1")
```

- [ ] **Step 5: 跑测试确认通过**

Run: `$PY -m pytest tests/knowledge_graph/test_api_routes.py -v`
Expected: 5 个 PASS

- [ ] **Step 6: 真实服务验证（backend 以 --reload 跑着，保存即重载）**

Run: `curl -s "http://localhost:8000/api/v1/knowledge/stats"`
Expected: `{"success":true,"seeded":true,...,"case_count":2,...}`

Run: `curl -s "http://localhost:8000/api/v1/knowledge/graph?node_types=plant,violation_pattern&live=false"`
Expected: JSON 里 nodes 全是 plant/violation_pattern 类型

Run: `curl -s "http://localhost:8000/api/v1/knowledge/graph"`（默认 live=true）
Expected: plant 节点 props 里有 `last_data_ts` 字段（活图叠加生效）

- [ ] **Step 7: 提交**

```bash
git add backend/api/v1/knowledge/ backend/main.py tests/knowledge_graph/test_api_routes.py
git commit -m "feat(graph): /api/v1/knowledge 三只读端点——graph/node/stats+活图状态叠加+空库引导

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: 前端——API 封装与 store

**Files:**
- Create: `frontend/src/api/modules/knowledge.ts`
- Create: `frontend/src/stores/knowledge.ts`
- Test: `frontend/src/stores/__tests__/knowledge.spec.ts`

- [ ] **Step 1: 写失败的 store 测试**

```typescript
// frontend/src/stores/__tests__/knowledge.spec.ts
import { describe, it, expect } from 'vitest'
import { toEChartsSeries, NODE_META } from '@/stores/knowledge'

describe('toEChartsSeries', () => {
  const nodes = [
    { id: 'plant:jinqiao', type: 'plant', label: '金桥一期', props: {} },
    { id: 'indicator:COD', type: 'indicator', label: 'COD', props: {} },
    { id: 'pattern:bottle', type: 'violation_pattern', label: '插瓶干扰', props: {} },
    { id: 'agent:master', type: 'agent', label: '主智能体', props: {} },
  ]
  const edges = [
    { id: 1, src: 'plant:jinqiao', dst: 'indicator:COD', type: 'monitors', props: {} },
    { id: 2, src: 'indicator:COD', dst: 'pattern:bottle', type: 'monitors', props: {} },
    { id: 3, src: 'agent:master', dst: 'pattern:bottle', type: 'employs', props: {} },
  ]

  it('节点映射为 data，id/name/category 齐全', () => {
    const s = toEChartsSeries(nodes, edges, ['plant', 'indicator', 'violation_pattern'])
    expect(s.data).toHaveLength(3)
    expect(s.data[0]).toMatchObject({ id: 'plant:jinqiao', name: '金桥一期', category: 0 })
    expect(s.categories).toHaveLength(3)
  })

  it('边仅当两端类型都在可见集合内才保留', () => {
    const s = toEChartsSeries(nodes, edges, ['plant', 'indicator'])
    expect(s.links).toHaveLength(1) // 两条 monitors 端点都可见; employs 的 agent 不可见
    expect(s.links[0]).toMatchObject({ source: 'plant:jinqiao', target: 'indicator:COD' })
  })

  it('空图返回空数组', () => {
    const s = toEChartsSeries([], [], ['plant'])
    expect(s.data).toHaveLength(0)
    expect(s.links).toHaveLength(0)
  })
})

describe('NODE_META', () => {
  it('8 类节点齐备且 tab 归属二分', () => {
    const types = Object.keys(NODE_META)
    expect(types).toEqual(expect.arrayContaining([
      'plant', 'indicator', 'violation_pattern', 'operator',
      'regulation', 'case', 'agent', 'service',
    ]))
    for (const meta of Object.values(NODE_META)) {
      expect(['domain', 'topology']).toContain(meta.tab)
    }
  })
})
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd frontend && npm test -- src/stores/__tests__/knowledge.spec.ts`
Expected: FAIL —— 无法解析 `@/stores/knowledge`

- [ ] **Step 3: 实现 api module + store**

```typescript
// frontend/src/api/modules/knowledge.ts
import api from '../client'

export interface KGNode {
  id: string
  type: string
  label: string
  props: Record<string, unknown>
  depth?: number
}
export interface KGEdge {
  id: number
  src: string
  dst: string
  type: string
  props: Record<string, unknown>
}
export interface KGStats {
  nodes: number
  edges: number
  node_types: Record<string, number>
  edge_types: Record<string, number>
  case_count?: number
}
export interface GraphResp {
  success: boolean
  seeded: boolean
  nodes: KGNode[]
  edges: KGEdge[]
  stats: KGStats
}

export const knowledgeService = {
  graph: (nodeTypes?: string[], live = true) =>
    api.get<unknown, GraphResp>('/v1/knowledge/graph', {
      params: {
        ...(nodeTypes?.length ? { node_types: nodeTypes.join(',') } : {}),
        live,
      },
    }),
  node: (id: string) =>
    api.get<unknown, { success: boolean; node: KGNode; neighbors: Record<string, KGNode[]> }>(
      `/v1/knowledge/node/${encodeURIComponent(id)}`),
  stats: () => api.get<unknown, KGStats & { seeded: boolean }>('/v1/knowledge/stats'),
}
```

注：`src/api/client.ts` 拦截器统一解包 `response.data`，所以直接拿到 body 形状。

```typescript
// frontend/src/stores/knowledge.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { knowledgeService, type KGNode, type KGEdge, type KGStats } from '@/api/modules/knowledge'

// 节点类型元数据：中文标签/颜色/tab 归属（domain=领域知识 / topology=服务拓扑）
export const NODE_META: Record<string, { label: string; color: string; tab: 'domain' | 'topology' }> = {
  plant: { label: '厂区', color: '#22c55e', tab: 'domain' },
  indicator: { label: '指标', color: '#84cc16', tab: 'domain' },
  violation_pattern: { label: '违规模式', color: '#ef4444', tab: 'domain' },
  operator: { label: '算子', color: '#f59e0b', tab: 'domain' },
  regulation: { label: '法规', color: '#8b5cf6', tab: 'domain' },
  case: { label: '案例', color: '#ec4899', tab: 'domain' },
  agent: { label: '智能体', color: '#3b82f6', tab: 'topology' },
  service: { label: '服务', color: '#06b6d4', tab: 'topology' },
}

export const useKnowledgeStore = defineStore('knowledge', () => {
  const allNodes = ref<KGNode[]>([])
  const allEdges = ref<KGEdge[]>([])
  const stats = ref<KGStats | null>(null)
  const seeded = ref(false)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const activeTab = ref<'domain' | 'topology'>('domain')
  const enabledTypes = ref<string[]>([]) // 空=该 tab 全选

  async function loadGraph() {
    loading.value = true
    error.value = null
    try {
      const resp = await knowledgeService.graph()
      allNodes.value = resp.nodes
      allEdges.value = resp.edges
      stats.value = resp.stats
      seeded.value = resp.seeded
    } catch (e) {
      error.value = String(e)
    } finally {
      loading.value = false
    }
  }

  function toggleType(t: string) {
    enabledTypes.value = enabledTypes.value.includes(t)
      ? enabledTypes.value.filter(x => x !== t)
      : [...enabledTypes.value, t]
  }

  /** 当前可见类型 = tab 预设 ∩ 图例勾选（勾选为空=全选 tab 预设） */
  const visibleTypes = computed(() => {
    const tabTypes = Object.keys(NODE_META).filter(
      k => NODE_META[k].tab === activeTab.value)
    if (!enabledTypes.value.length) return tabTypes
    return tabTypes.filter(t => enabledTypes.value.includes(t))
  })

  /** 切 tab 时重置图例勾选 */
  function setTab(tab: 'domain' | 'topology') {
    activeTab.value = tab
    enabledTypes.value = []
  }

  const selectedNode = ref<KGNode | null>(null)
  const selectedNeighbors = ref<Record<string, KGNode[]>>({})
  async function selectNode(id: string) {
    try {
      const resp = await knowledgeService.node(id)
      selectedNode.value = resp.node
      selectedNeighbors.value = resp.neighbors
    } catch {
      selectedNode.value = null
    }
  }
  function clearSelection() {
    selectedNode.value = null
    selectedNeighbors.value = {}
  }

  return { allNodes, allEdges, stats, seeded, loading, error,
           activeTab, enabledTypes, visibleTypes, toggleType, setTab,
           selectedNode, selectedNeighbors, selectNode, clearSelection, loadGraph }
})

/** nodes/edges + 可见类型集合 → ECharts graph series（data/links/categories） */
export function toEChartsSeries(
  nodes: KGNode[], edges: KGEdge[], visibleTypes: string[],
): { data: unknown[]; links: unknown[]; categories: { name: string }[] } {
  const vis = visibleTypes.slice() // 保持顺序=categories 顺序
  const categories = vis.map(t => ({ name: NODE_META[t]?.label ?? t }))
  const catIdx = new Map(vis.map((t, i) => [t, i]))
  const data = nodes
    .filter(n => vis.includes(n.type))
    .map(n => ({
      id: n.id,
      name: n.label,
      category: catIdx.get(n.type) ?? 0,
      symbolSize: n.type === 'agent' || n.type === 'service' ? 40 : 28,
      itemStyle: { color: NODE_META[n.type]?.color },
    }))
  const nodeIds = new Set(data.map(d => (d as { id: string }).id))
  const links = edges
    .filter(e => nodeIds.has(e.src) && nodeIds.has(e.dst))
    .map(e => ({ source: e.src, target: e.dst, value: e.type }))
  return { data, links, categories }
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd frontend && npm test -- src/stores/__tests__/knowledge.spec.ts`
Expected: PASS（4 个测试）

- [ ] **Step 5: 提交**

```bash
git add frontend/src/api/modules/knowledge.ts frontend/src/stores/knowledge.ts frontend/src/stores/__tests__/knowledge.spec.ts
git commit -m "feat(graph): 前端 knowledge api+store——类型元数据/tab预设/图例过滤/ECharts series转换

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: 前端——知识图谱页面

**Files:**
- Create: `frontend/src/views/KnowledgeGraphView.vue`
- Modify: `frontend/src/router/index.ts`（agents/audit 路由后追加）
- Modify: `frontend/src/components/layout/AppSidebar.vue`（智能助手组追加项）

- [ ] **Step 1: 路由与侧栏注册**

`frontend/src/router/index.ts` —— `agents/audit` 行后追加：

```typescript
        { path: 'agents/knowledge', component: () => import('@/views/KnowledgeGraphView.vue'),
          meta: { title: '知识图谱', group: '智能助手' } },
```

`frontend/src/components/layout/AppSidebar.vue` —— 智能助手组 items 追加（`Connection` 图标已在 import 列表）：

```typescript
    { path: '/agents/knowledge', title: '知识图谱', icon: Connection },
```

- [ ] **Step 2: 页面组件**

```vue
<!-- frontend/src/views/KnowledgeGraphView.vue -->
<template>
  <div class="kg-page">
    <div class="kg-header">
      <div class="kg-title">
        <h2>知识图谱</h2>
        <span v-if="store.stats" class="kg-badges">
          <el-tag size="small">{{ store.stats.nodes }} 节点</el-tag>
          <el-tag size="small" type="warning">{{ store.stats.edges }} 关系</el-tag>
          <el-tag size="small" type="danger">{{ caseCount }} 案例</el-tag>
        </span>
      </div>
      <el-radio-group :model-value="store.activeTab" size="small" @update:model-value="store.setTab">
        <el-radio-button value="domain">领域知识</el-radio-button>
        <el-radio-button value="topology">服务拓扑</el-radio-button>
      </el-radio-group>
    </div>

    <el-empty v-if="!store.loading && !store.seeded" description="知识图谱未初始化">
      <template #image><el-icon :size="48"><Connection /></el-icon></template>
      <p class="kg-hint">运行初始化：ecological_env\Scripts\python.exe shared\knowledge_graph\seed_importer.py</p>
    </el-empty>

    <div v-else class="kg-body">
      <div class="kg-legend">
        <div class="label">图例 / 过滤</div>
        <el-checkbox-group v-model="store.enabledTypes">
          <el-checkbox v-for="(meta, t) in tabTypes" :key="t" :value="t">
            <span :style="{ color: meta.color }">●</span> {{ meta.label }}
            <span class="kg-count">{{ typeCount(String(t)) }}</span>
          </el-checkbox>
        </el-checkbox-group>
      </div>

      <div class="kg-chart-wrap">
        <el-alert v-if="renderError" type="warning" :closable="false"
                  title="图形渲染失败，已降级为列表视图" />
        <div v-show="!renderError" ref="chartEl" class="kg-chart" />
        <el-table v-if="renderError" :data="visibleNodes" size="small" height="100%">
          <el-table-column prop="id" label="ID" width="280" />
          <el-table-column prop="label" label="名称" />
          <el-table-column prop="type" label="类型" width="120" />
        </el-table>
      </div>

      <div v-if="store.selectedNode" class="kg-detail">
        <div class="kg-detail-head">
          <h3>{{ store.selectedNode.label }}</h3>
          <el-tag size="small">{{ typeLabel(store.selectedNode.type) }}</el-tag>
          <el-button text size="small" @click="store.clearSelection">关闭</el-button>
        </div>
        <el-descriptions :column="1" size="small" border>
          <el-descriptions-item v-for="(v, k) in store.selectedNode.props" :key="k"
                                :label="String(k)">{{ String(v) }}</el-descriptions-item>
        </el-descriptions>
        <div class="label kg-nb-title">关联（一跳）</div>
        <div v-for="(list, ntype) in store.selectedNeighbors" :key="ntype" class="kg-nb-group">
          <div class="label">{{ typeLabel(String(ntype)) }}（{{ list.length }}）</div>
          <el-tag v-for="n in list" :key="n.id" class="kg-nb-tag"
                  @click="store.selectNode(n.id)">{{ n.label }}</el-tag>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, nextTick, ref, watch } from 'vue'
import { Connection } from '@element-plus/icons-vue'
import echarts from '@/lib/echarts'
import { useKnowledgeStore, NODE_META, toEChartsSeries } from '@/stores/knowledge'

const store = useKnowledgeStore()
const chartEl = ref<HTMLDivElement>()
const renderError = ref(false)
let chart: echarts.ECharts | null = null

const caseCount = computed(() => store.stats?.node_types?.case ?? 0)
const tabTypes = computed(() =>
  Object.fromEntries(Object.entries(NODE_META)
    .filter(([, m]) => m.tab === store.activeTab)))
const visibleNodes = computed(() =>
  store.allNodes.filter(n => store.visibleTypes.includes(n.type)))

function typeLabel(t: string) { return NODE_META[t]?.label ?? t }
function typeCount(t: string) { return store.stats?.node_types?.[t] ?? 0 }

function renderChart() {
  if (!chartEl.value || !store.seeded) return
  try {
    if (!chart) chart = echarts.init(chartEl.value)
    const series = toEChartsSeries(store.allNodes, store.allEdges, store.visibleTypes)
    chart.setOption({
      tooltip: {
        formatter: (p: any) => p.dataType === 'node'
          ? `${p.name}（${typeLabel(store.allNodes.find(n => n.id === p.id)?.type ?? '')}）`
          : String(p.value ?? ''),
      },
      legend: { data: series.categories.map(c => c.name), bottom: 0 },
      series: [{
        type: 'graph',
        layout: 'force',
        force: { repulsion: 120, edgeLength: [40, 90], gravity: 0.08 },
        roam: true,
        draggable: true,
        label: { show: true, fontSize: 11 },
        emphasis: { focus: 'adjacency' },
        categories: series.categories,
        data: series.data,
        links: series.links,
      }],
    }, { notMerge: true })
    renderError.value = false
  } catch {
    renderError.value = true // 降级表格
  }
}

function onNodeClick(params: any) {
  if (params.dataType === 'node' && params.data?.id) store.selectNode(params.data.id)
}
function onResize() { chart?.resize() }

onMounted(async () => {
  await store.loadGraph()
  await nextTick()
  renderChart()
  chart?.on('click', onNodeClick)
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chart?.dispose()
  chart = null
})

// tab/图例/数据变化 → 重渲染（nextTick 兜底，吸取大屏 echarts.init 教训）
watch([() => store.visibleTypes, () => store.allNodes],
  () => nextTick(renderChart), { deep: true })
</script>

<style scoped>
.kg-page { padding: 16px; height: 100%; display: flex; flex-direction: column; }
.kg-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.kg-title { display: flex; align-items: center; gap: 12px; }
.kg-title h2 { margin: 0; font-size: 18px; }
.kg-badges { display: flex; gap: 6px; }
.kg-body { flex: 1; display: flex; gap: 12px; min-height: 0; }
.kg-legend { width: 180px; flex-shrink: 0; border: 1px solid var(--el-border-color-light); border-radius: 8px; padding: 12px; overflow-y: auto; }
.kg-legend .el-checkbox { display: flex; margin-right: 0; }
.kg-count { color: var(--el-text-color-secondary); font-size: 12px; margin-left: 4px; }
.kg-chart-wrap { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.kg-chart { flex: 1; min-height: 0; }
.kg-detail { width: 300px; flex-shrink: 0; border: 1px solid var(--el-border-color-light); border-radius: 8px; padding: 12px; overflow-y: auto; }
.kg-detail-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.kg-detail-head h3 { margin: 0; font-size: 15px; flex: 1; }
.kg-nb-title { margin-top: 12px; }
.kg-nb-group { margin-bottom: 8px; }
.kg-nb-tag { cursor: pointer; margin: 2px; }
.kg-hint { color: var(--el-text-color-secondary); font-size: 12px; }
</style>
```

- [ ] **Step 3: 手动验收（服务都在跑）**

1. 浏览器开 http://localhost:5173/agents/knowledge —— 默认领域知识 tab 显示力导向图
2. 切「服务拓扑」—— 图切换为 agent/service/operator 节点（employs/orchestrates/calls 边可见）
3. 图例取消「法规」—— 法规节点及其相连边消失
4. 点「插瓶干扰」—— 右侧详情：props（status/desc/source）+ 一跳邻居分组（operator 组有 constant_detector）
5. 详情点邻居 tag —— 跳到该节点详情
6. 点空白处不动；切 tab 后图例重置为全选（setTab 行为）

- [ ] **Step 4: 类型检查**

Run: `cd frontend && npx vue-tsc --noEmit 2>&1 | grep -i knowledge`
Expected: 无输出（knowledge 相关零类型错误；存量错误不在此范围）

- [ ] **Step 5: 提交**

```bash
git add frontend/src/views/KnowledgeGraphView.vue frontend/src/router/index.ts frontend/src/components/layout/AppSidebar.vue
git commit -m "feat(graph): /agents/knowledge 页面——双tab力导向图+图例过滤+详情侧栏+渲染降级

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 6: 收尾——全量回归 + 文档

- [ ] **Step 1: 全量 Python 测试**

Run: `$PY -m pytest tests/ -v`
Expected: knowledge_graph 三个文件全 PASS，无回归

- [ ] **Step 2: 前端全量测试**

Run: `cd frontend && npm test`
Expected: 全 PASS（存量 4 spec + 新增 knowledge spec）

- [ ] **Step 3: CLAUDE.md 补条目**（Key Files 区块末尾追加）

```markdown
### 知识图谱（2026-09-07 子项目 1/4）
- `shared/knowledge_graph/`：第四库（graph_store.py 存储+查询 / seed_importer.py 种子导入，幂等可重跑）
- `shared/data/knowledge_graph.db`：图数据文件（gitignore；不存在时 API 返回 seeded:false 引导）
- `backend/api/v1/knowledge/routes.py`：3 只读端点（graph/node/stats）+ 活图状态叠加（查时合并不落库）
- `frontend/src/views/KnowledgeGraphView.vue`：/agents/knowledge 双 tab（领域知识/服务拓扑）力导向图
- 后续子项目：2 事件中心真实化 → 3 智能体集成（图查询+研判写回）→ 4 根因分析
```

- [ ] **Step 4: 最终提交**

```bash
git add CLAUDE.md
git commit -m "docs: CLAUDE.md 补知识图谱核心条目

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Self-Review 记录

- **Spec 覆盖**：8 节点类型（Task 2 静态目录+导入函数）✓；10 边类型（Task 1 EDGE_TYPES + Task 2 全部产出：monitors/detects/indicates/cites/employs/calls/orchestrates/reads/writes/involves）✓；7 查询 API（Task 1：upsert×2/get_node/neighbors/subgraph/shortest_path/stats，impact 留子项目 4——spec 中 impact 属子项目 4 用途）✓；种子 7 源+硬编码映射+幂等+回退（Task 2）✓；3 端点+活图叠加+空库引导（Task 3）✓；双 tab+图例+详情+降级（Task 4/5）✓；错误处理（depth 上限抛错/单源跳过/不自动建库/try-catch 降级表格）✓；测试四层（pytest×3 + Vitest + 手动验收清单）✓
- **占位符扫描**：无 TBD/TODO 型占位；Task 1 有一处标注清楚的代码取舍说明（et_sql 只保留第二行赋值，第一行是写计划时的残留说明，非待办）
- **类型一致性**：`toEChartsSeries` 全计划统一；`GraphStore(db_path)` 构造一致；节点 id 前缀 `pattern:/operator:specialized:/plant:<中文 plant_id>`（中文例外已注明理由：与 InfluxDB tag/活图叠加对齐）；查询参数用全称 `violation_pattern`；`setTab/clearSelection/toggleType` 在 Task 4 定义、Task 5 使用，名称一致
- **已知偏差**：spec 说"节点 ID 用英文 slug"，plant 节点例外用中文 plant_id（避免造映射表、活图叠加直接匹配 InfluxDB tag）——已写进 graph_store.py 模块注释
```
