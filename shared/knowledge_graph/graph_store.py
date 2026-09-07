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
        et_sql = (f" AND e.type IN ({','.join(chr(39)+e+chr(39) for e in ets)})"
                  if ets else "")
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
            # SQLite 递归 CTE 限制：递归项只能引用 reach 一次且不能包在子查询里，
            # 故双向用 OR JOIN + CASE 取另一端（原计划的子查询双引用会报
            # "circular reference: reach"）
            rec = (f"SELECT CASE WHEN e.src = r.nxt THEN e.dst "
                   f"ELSE e.src END AS nxt, r.d + 1 AS d "
                   f"FROM reach r JOIN edges e "
                   f"ON e.src = r.nxt OR e.dst = r.nxt "
                   f"WHERE r.d < {d_sql}{et_sql}")
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
