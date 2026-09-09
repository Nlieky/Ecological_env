# shared/knowledge_graph/graph_query.py
"""GraphKnowledgeSource——规则推理的知识源（子项目3 阶段A）。

优先图谱查询；DB 缺失/空图/异常时回退调用方提供的硬编码字典。
回退可观测：fallback_log 记录每次回退（时间/调用方/原因），
usage_report 汇总写进研判结果 metadata.graph_usage——
线上统计回退频率，几乎不触发则移除兜底（用户指示 2026-09-09）。
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from shared.knowledge_graph.graph_store import GraphStore

logger = logging.getLogger(__name__)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DB = _PROJECT_ROOT / "shared" / "data" / "knowledge_graph.db"


class GraphKnowledgeSource:
    """统一知识源：图谱优先、回退可观测。

    生命周期：一个研判流程一个实例（usage_report 随实例走，写进结果
    metadata.graph_usage 后即弃）。查询失败一次即熔断（available=False），
    后续全部走回退，不反复撞坏库。
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else _DEFAULT_DB
        self.fallback_log: list[dict] = []
        self._query_count = 0
        self._store: Optional[GraphStore] = None
        self._patterns_cache: Optional[list[dict]] = None  # pattern_id_by_label 复用
        self._broken_reason: Optional[str] = None  # 查询异常熔断时的原因
        self.available = False
        # 先检查存在再构造：GraphStore 构造即建库文件（executescript 建表），
        # 直接构造会把"图不存在"污染成"空图存在"
        if self.db_path.exists():
            try:
                self._store = GraphStore(self.db_path)
                self.available = True
            except Exception as e:
                logger.warning(f"[graph-query] GraphStore 初始化失败: {e}")

    # ---------- 内部 ----------
    def _fallback(self, caller: str, reason: str, data):
        self.fallback_log.append(
            {"time": datetime.now().isoformat(timespec="seconds"),
             "caller": caller, "reason": reason})
        return data

    def _unavailable_reason(self, default_reason: str) -> str:
        """图查询走不通时的归因：优先结构性原因，兜底调用方给的场景原因。

        pattern_not_found 这类"图正常但目标不在图里"的场景由 default_reason
        携带（图不可用会被前面两个分支截住，轮不到 default）。
        """
        if not self.db_path.exists():
            return "db_missing"
        if self._broken_reason:  # 曾查崩：归因到具体异常而非笼统不可用
            return self._broken_reason
        if not self.available:
            return "store_init_failed"
        return default_reason

    def _subgraph(self, node_types: list[str]):
        """查询子图；不可用/空/异常返回 None（调用方走回退）。异常后熔断 available。"""
        if not self.available:
            return None
        try:
            sg = self._store.subgraph(node_types=node_types)
            self._query_count += 1
            return sg if sg["nodes"] else None
        except Exception as e:
            logger.warning(f"[graph-query] 查询失败({node_types}): {e}")
            self._broken_reason = f"error:{type(e).__name__}"  # 熔断原因给回退归因
            self.available = False  # 熔断：后续查询直接回退，不反复撞
            return None

    # ---------- 查询 API（fallback 参数=调用方硬编码字典） ----------
    def get_patterns(self, fallback=None) -> list:
        """违规模式目录：[{id, label, desc, status}]。图成功路径有缓存。"""
        if (pats := self._patterns_cache) is not None:
            return pats
        sg = self._subgraph(["violation_pattern"])
        if sg is not None:
            out = [{"id": n["id"], "label": n["label"],
                    "desc": n["props"].get("desc", ""),
                    "status": n["props"].get("status", "")}
                   for n in sg["nodes"]]
            self._patterns_cache = out
            return out
        # 回退路径不缓存：available=False 时 _subgraph 直接 None，
        # 后续调用仍走这里，行为一致且 fallback_log 每次可观测
        return self._fallback("get_patterns",
                              self._unavailable_reason("empty_or_no_patterns"),
                              list(fallback or []))

    def get_cases(self, fallback=None) -> list:
        """历史案例：[{id, label, timestamp, confidence, reasoning, violation_types}]。"""
        sg = self._subgraph(["case"])
        if sg is not None:
            return [{"id": n["id"], "label": n["label"], **n["props"]}
                    for n in sg["nodes"]]
        return self._fallback("get_cases",
                              self._unavailable_reason("empty_or_no_cases"),
                              list(fallback or []))

    def get_indicator_limits(self, fallback=None) -> dict:
        """limits 边（indicator→GB18918）：{英文键: {value, standard}}。"""
        sg = self._subgraph(["indicator", "regulation"])
        if sg is not None:
            node_by_id = {n["id"]: n for n in sg["nodes"]}
            out = {}
            for e in sg["edges"]:
                if e["type"] != "limits":
                    continue
                ind, reg = node_by_id.get(e["src"]), node_by_id.get(e["dst"])
                if ind and reg and "gb18918" in reg["id"]:
                    key = ind["props"].get("field", ind["id"].split(":", 1)[1])
                    out[key] = {"value": e["props"].get("value", ""),
                                "standard": reg["label"]}
            if out:
                return out
            return self._fallback("get_indicator_limits", "no_limits_edges",
                                  dict(fallback or {}))
        return self._fallback("get_indicator_limits",
                              self._unavailable_reason("empty_or_no_indicators"),
                              dict(fallback or {}))

    def get_pattern_laws(self, pattern_label: str, fallback=None) -> list:
        """模式关联法条（indicates 边，篡改类双锚 §39+§83）：
        [{article, note, anchor}]。"""
        pid = self.pattern_id_by_label(pattern_label)
        # 审查 Important-1：熔断守卫——available=False 时不再撞库（此前绕过 _subgraph
        # 直调 neighbors，熔断后每次白撞一次；pid 可用但图已坏时归因走 _broken_reason）
        if pid is None or not self.available:
            return self._fallback("get_pattern_laws",
                                  self._unavailable_reason("pattern_not_found"),
                                  list(fallback or []))
        try:
            nb = self._store.neighbors(pid, edge_types=["indicates"],
                                       direction="out", depth=1)
            self._query_count += 1
        except Exception as e:
            logger.warning(f"[graph-query] 法条查询失败: {e}")
            self._broken_reason = f"error:{type(e).__name__}"
            self.available = False  # 与 _subgraph 熔断语义对齐
            return self._fallback("get_pattern_laws", f"error:{type(e).__name__}",
                                  list(fallback or []))
        return [{"article": n["props"].get("article", n["label"]),
                 "note": n["props"].get("note", ""),
                 "anchor": n["label"]} for n in nb["nodes"]]

    def pattern_id_by_label(self, label: str) -> Optional[str]:
        for p in self.get_patterns():  # 有缓存，二次调用不撞库
            if p["label"] == label:
                return p["id"]
        return None

    def usage_report(self) -> dict:
        """图谱使用情况汇总（写进研判结果 metadata.graph_usage）。"""
        return {"used_graph": self.available,
                "queries": self._query_count,
                "fallbacks": len(self.fallback_log),
                "fallback_detail": self.fallback_log}
