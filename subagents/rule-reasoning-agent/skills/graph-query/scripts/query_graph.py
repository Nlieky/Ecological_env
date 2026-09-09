#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""graph-query：规则推理子智能体的图谱查询技能（子项目3 阶段C）。

三种查询（互斥，必选其一）：
  --pattern <中文名>   模式详情：desc/status/laws(indicates)/detects(算子)/cases(cites 反向)
  --cases [--plant X]  全部案例（可按 involves 厂过滤，props.plant_id 兜底）
  --law <模式名>       模式关联法条（--pattern 的省 token 子集视图，不查 detects/cases）

输出：单行紧凑 JSON（<2000字符，LLM 上下文友好）。
图缺失/参数错 → {"error": "..."} + exit 0（绝不 exit 非 0——LLM 环境要稳）。
"""
import argparse
import json
import os
import sys
from pathlib import Path


def _project_root() -> Path:
    """标记法找项目根（含 shared/ + workspace/），位置无关——
    与 call_subagent.py 的 _project_root 同一约定，迁移/层级变化不会算错。"""
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "shared").is_dir() and (parent / "workspace").is_dir():
            return parent
    return p.parents[5]  # 兜底：scripts→graph-query→skills→agent→subagents→根


_PROJECT_ROOT = _project_root()
sys.path.insert(0, str(_PROJECT_ROOT))

from shared.knowledge_graph.graph_query import GraphKnowledgeSource  # noqa: E402
from shared.knowledge_graph.graph_store import GraphStore  # noqa: E402


def _compact(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _trunc(s, n: int = 80) -> str:
    s = str(s or "")
    return s if len(s) <= n else s[:n] + "…"


def _laws_view(laws) -> list:
    return [{"article": l.get("article", ""),
             "note": _trunc(l.get("note", ""), 60),
             "anchor": l.get("anchor", "")} for l in laws]


def main():
    # LLM 可能经 terminal 不带 -X utf8 调本脚本：强制 stdout UTF-8，
    # 否则中文经 cp936 管道回传会乱码
    try:
        if (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "") != "utf8":
            sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--pattern")
    p.add_argument("--cases", action="store_true")
    p.add_argument("--plant", default="")
    p.add_argument("--law")
    p.add_argument("--db", default="")
    # parse_known_args：LLM 多传/传错未知参数时按忽略处理（argparse 默认会 exit 2，
    # 违反"exit 0 永远"契约）
    a, _unknown = p.parse_known_args()

    modes = sum(bool(x) for x in (a.pattern, a.cases, a.law))
    if modes != 1:
        print(_compact({"error": "usage",
                        "hint": "--pattern X | --cases [--plant X] | --law X"}))
        return

    db_str = a.db or os.environ.get("KNOWLEDGE_GRAPH_DB", "")
    db = Path(db_str) if db_str else _PROJECT_ROOT / "shared" / "data" / "knowledge_graph.db"
    if not db.exists():
        print(_compact({"error": "graph_unavailable"}))
        return

    src = GraphKnowledgeSource(db_path=db)
    if not src.available:  # 库损坏等：GraphStore 构造失败同样优雅退出
        print(_compact({"error": "graph_unavailable"}))
        return

    if a.pattern or a.law:
        label = a.pattern or a.law
        node = next((x for x in src.get_patterns() if x["label"] == label), None)
        if node is None:
            print(_compact({"error": "pattern_not_found", "label": label}))
            return
        laws = _laws_view(src.get_pattern_laws(label))
        if a.law:  # 省 token 视图：只出法条，不查 detects/cases
            print(_compact({"label": label, "laws": laws}))
            return
        out = {"label": label, "desc": _trunc(node.get("desc")),
               "status": node.get("status", "")}
        g = GraphStore(db)
        try:
            # detects: operator→pattern，从模式看是入边
            det = g.neighbors(node["id"], edge_types=["detects"],
                              direction="in", depth=1)
            out["detects"] = [n["label"] for n in det["nodes"]]
            # cites: case→pattern，入边 = 引用该模式的历史/研判案例
            cs = g.neighbors(node["id"], edge_types=["cites"],
                             direction="in", depth=1)
            out["cases"] = [{"label": n["label"],
                             "severity": n["props"].get("severity", ""),
                             "timestamp": (str(n["props"].get("timestamp", "") or ""))[:10]}
                            for n in cs["nodes"]][:10]
        finally:
            g.close()
        out["laws"] = laws
        print(_compact(out))
        return

    if a.cases:
        cases = src.get_cases()
        if a.plant:
            g = GraphStore(db)
            try:
                # involves（case→plant）才是厂关联的正源；props.plant_id 是研判
                # 写回才带的冗余，种子案例两者皆无 → 过滤后 0 是正确行为
                sg = g.subgraph(node_types=["case", "plant"],
                                edge_types=["involves"])
                by_id = {n["id"]: n for n in sg["nodes"]}
                plants_by_case = {}
                for e in sg["edges"]:
                    s, d = by_id.get(e["src"]), by_id.get(e["dst"])
                    if (s and d and s["type"] == "case" and d["type"] == "plant"):
                        plants_by_case.setdefault(e["src"], []).append(d["label"])
            finally:
                g.close()

            def _hit(c):
                names = list(plants_by_case.get(c.get("id"), []))
                if c.get("plant_id"):
                    names.append(str(c["plant_id"]))
                return any(a.plant in n for n in names)

            cases = [c for c in cases if _hit(c)]
        out = [{"label": c["label"],
                "timestamp": (str(c.get("timestamp", "") or ""))[:10],
                "severity": c.get("severity", ""),
                "types": c.get("violation_types", []),
                "plant": c.get("plant_id", "")}
               for c in cases][:30]
        print(_compact({"cases": out}))


if __name__ == "__main__":
    main()
