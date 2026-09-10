#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""query_history——主智能体的历史研判/案例查询工具（2026-09-10 修复实测问题①）。

用户问"这个厂历史上有没有违规""最近的研判结论是什么"时，主智能体直接调本工具
（秒回，不走研判管线）——数据源双查：
  1. 图谱 case 节点（shared/knowledge_graph.db，含研判写回的案例，子项目3阶段B）
  2. alert_events 表（事件库，子项目2）
按时间倒序合并去重（写回案例与事件同 source_event 只保留一条，优先事件行的完整字段）。

作为脚本可独立跑（python query_history.py --plant X --limit 5），
作为 handler 被 tool_registration.py 注册为 query_history 工具。
图/事件库任一不可用→静默用另一个，双不可用→空结果+说明（不抛——LLM 环境要稳）。
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _query_graph_cases(plant: str, limit: int) -> list:
    """图谱 case 节点（含研判写回）。图缺失/损坏返回 []。"""
    db = _PROJECT_ROOT / "shared" / "data" / "knowledge_graph.db"
    if not db.exists():
        return []
    try:
        conn = sqlite3.connect(str(db), timeout=5)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, label, props_json FROM nodes WHERE type='case' "
            "ORDER BY id DESC LIMIT ?", (limit * 3,)).fetchall()
        conn.close()
        out = []
        for r in rows:
            p = json.loads(r["props_json"] or "{}")
            if plant and plant not in (p.get("plant_id") or ""):
                continue
            out.append({
                "source": "graph_case",
                "time": (p.get("timestamp") or "")[:16],
                "plant": p.get("plant_id") or "",
                "violation_types": p.get("violation_types") or [],
                "severity": p.get("severity") or "",
                "action": p.get("action") or "",
                "confidence": p.get("confidence"),
                "source_event": p.get("source_event") or "",
            })
            if len(out) >= limit:
                break
        return out
    except Exception:
        return []


def _query_events(plant: str, limit: int) -> list:
    """alert_events 表。库缺失返回 []。"""
    db = _PROJECT_ROOT / "shared" / "data" / "ecological_logs.db"
    if not db.exists():
        return []
    try:
        conn = sqlite3.connect(str(db), timeout=5)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, timestamp, plant_id, violation_types, severity, action, "
            "confidence, status FROM alert_events "
            "ORDER BY timestamp DESC LIMIT ?", (limit * 3,)).fetchall()
        conn.close()
        out = []
        for r in rows:
            if plant and plant not in (r["plant_id"] or ""):
                continue
            vt = r["violation_types"]
            if isinstance(vt, str):
                try:
                    vt = json.loads(vt)
                except Exception:
                    vt = []
            out.append({
                "source": "event",
                "time": str(r["timestamp"] or "")[:16],
                "plant": r["plant_id"] or "",
                "violation_types": vt or [],
                "severity": (r["severity"] or ""),
                "action": r["action"] or "",
                "confidence": r["confidence"],
                "status": (r["status"] or ""),
                "event_id": r["id"],
            })
            if len(out) >= limit:
                break
        return out
    except Exception:
        return []


def query_history(plant: str = "", limit: int = 10) -> dict:
    """双源查询合并。返回 {total, cases:[...], note}——紧凑供 LLM 直接引用。"""
    limit = max(1, min(int(limit or 10), 50))
    events = _query_events(plant, limit)
    graph = _query_graph_cases(plant, limit)
    # 去重：图谱写回案例带 source_event，与事件表 event_id 相同 → 只留事件行（字段全）
    event_ids = {e.get("event_id") for e in events}
    merged = list(events) + [g for g in graph
                             if not g.get("source_event")
                             or g["source_event"] not in event_ids]
    merged.sort(key=lambda x: x.get("time") or "", reverse=True)
    cases = merged[:limit]
    note = ""
    if not cases:
        note = (f"未找到{'该厂' if plant else ''}历史研判/违规案例记录"
                f"（图谱 {len(graph)} 条、事件 {len(events)} 条源数据均无匹配）")
    return {"total": len(cases), "cases": cases, "note": note}


def _handler(*args, **kwargs) -> str:
    """tool_registration 注册用的 handler（灵活签名，与 _run_detector_handler 同模式）。"""
    if args and isinstance(args[0], dict):
        params = args[0]
    elif 'function_args' in kwargs:
        params = kwargs['function_args']
    elif args and len(args) >= 2 and isinstance(args[1], dict):
        params = args[1]
    else:
        params = kwargs
    try:
        result = query_history(
            plant=str(params.get("plant", "") or ""),
            limit=int(params.get("limit", 10) or 10))
    except Exception as e:
        result = {"total": 0, "cases": [], "note": f"查询失败: {e}"}
    return json.dumps(result, ensure_ascii=False)


if __name__ == "__main__":
    import io
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--plant", default="")
    ap.add_argument("--limit", type=int, default=10)
    a = ap.parse_args()
    print(json.dumps(query_history(a.plant, a.limit), ensure_ascii=False))
