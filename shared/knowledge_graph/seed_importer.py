# shared/knowledge_graph/seed_importer.py
"""知识图谱种子导入：从项目真实文件灌出初始图。

数据源（全部只读）：
  1. plant-hierarchy.yaml     → plant 节点（id 保留中文 plant_id，同 InfluxDB tag）
  2. 指标发现（CANONICAL_FIELDS 契约 + InfluxDB 触达校验，不可达回退 7 指标清单）
  3. 违规模式静态目录（对齐 violation_patterns.md/典型违规模式.md）→ pattern 节点
  4. operator_config.json     → operator 节点 + specialized 目录补齐
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
from typing import Dict, List, Optional, Tuple

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
     "props": {"endpoint": "http://172.16.12.41:30000/v1"}},
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


# yaml 顶层保留键（映射不是层级），与 discover_plants.build_tree 的 _RESERVED 一致
_RESERVED_KEYS = {"report_name_map", "plant_configs", "plant_aliases"}


def _import_plants(g: GraphStore) -> List[str]:
    """读层级 yaml，返回 plant_id 列表。缺失/损坏跳过（返回 []，不抛）。"""
    if not _HIERARCHY_FILE.exists():
        print(f"[seed] 警告: {_HIERARCHY_FILE} 不存在，跳过厂区源")
        return []
    import yaml
    try:
        data = yaml.safe_load(_HIERARCHY_FILE.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        print(f"[seed] 警告: 层级 yaml 解析失败({e})，跳过厂区源")
        return []
    plant_ids: List[str] = []
    for city, districts in data.items():
        if city in _RESERVED_KEYS or not isinstance(districts, dict):
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
    # 层级骨架：算子库 → 各分类（统计/机器学习/深度学习/专用）→ 具体算子（belongs_to）
    # 没有归属的算子就是孤点——库结构本身是图的一部分（用户语义：梯度检测属于
    # 统计学算子属于算子库；transformer 属于深度学习算子属于算子库）
    g.upsert_node("library:operators", "library", "算子库",
                  {"path": "shared/operators", "desc": "异常检测模型算子库（三库一体之一）"})
    cat_names = {"statistical": "统计类算子", "machine_learning": "机器学习类算子",
                 "deep_learning": "深度学习类算子", "specialized": "专用类算子"}
    cfg = json.loads(_OPERATOR_CONFIG.read_text(encoding="utf-8"))
    n = 0
    for cat, block in cfg.get("operators", {}).items():
        cat_id = f"category:{cat}"
        g.upsert_node(cat_id, "category", cat_names.get(cat, cat),
                      {"parent": "算子库",
                       "desc": block.get("description", ""),
                       "requires_training": bool(block.get("requires_training", False))})
        g.upsert_edge(cat_id, "library:operators", "belongs_to")
        for op_key, op in (block.get("operators") or {}).items():
            g.upsert_node(f"operator:{cat}:{op_key}", "operator",
                          op.get("name", op_key),
                          {"category": cat,
                           "sub_category": op.get("sub_category", ""),
                           "formula": op.get("formula", ""),
                           "desc": op.get("description", ""),
                           "status": op.get("status", "available"),
                           "priority": op.get("priority", 3)})
            g.upsert_edge(f"operator:{cat}:{op_key}", cat_id, "belongs_to")
            n += 1
    # specialized 目录不在 config json 里，按文件补（对违规模式的专用检测器）；
    # 分类节点也要在此建——json 循环只覆盖 json 里有的三类，specialized 的
    # category 节点漏建会让 belongs_to 边被悬挂守卫拦掉（算子重新变孤点）
    spec_cat_id = "category:specialized"
    g.upsert_node(spec_cat_id, "category", "专用类算子",
                  {"parent": "算子库", "desc": "针对违规模式的专用检测器（shared/operators/specialized）"})
    g.upsert_edge(spec_cat_id, "library:operators", "belongs_to")
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
        g.upsert_edge(f"operator:specialized:{key}", spec_cat_id, "belongs_to")
        n += 1
    return n


def _import_knowledge_tree(g: GraphStore) -> int:
    """知识库层级骨架：知识库 → 违规模式库/法规库 → 具体模式/法规。

    用户语义：人工拟合属于（知识库的）违规模式库、法规属于法规库——
    知识实体也要有归属，不只靠 detects/indicates 语义边连。
    """
    g.upsert_node("library:knowledge", "library", "知识库",
                  {"path": "shared/knowledge", "desc": "废水排放知识库（三库一体之一）"})
    g.upsert_node("category:violation_patterns", "category", "违规模式库",
                  {"parent": "知识库", "path": "shared/knowledge/violation_patterns"})
    g.upsert_node("category:regulations", "category", "法规库",
                  {"parent": "知识库", "path": "shared/knowledge/regulations"})
    g.upsert_edge("category:violation_patterns", "library:knowledge", "belongs_to")
    g.upsert_edge("category:regulations", "library:knowledge", "belongs_to")
    # 模式 → 违规模式库；法规 → 法规库
    for p in PATTERNS:
        g.upsert_edge(p["id"], "category:violation_patterns", "belongs_to")
    for r in REGULATIONS:
        g.upsert_edge(r["id"], "category:regulations", "belongs_to")
    return 5  # 库2 + 分类3（边在幂等 upsert 里）


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


def _edge_if_ends_exist(g: GraphStore, src: str, dst: str, etype: str,
                        props: Optional[Dict] = None) -> bool:
    """两端节点都存在才写边，防悬挂边（源被跳过时其关系边一并丢弃）。"""
    if g.get_node(src) is None or g.get_node(dst) is None:
        return False
    g.upsert_edge(src, dst, etype, props)
    return True


def _import_relation_edges(g: GraphStore) -> int:
    n = 0
    for src, dst, note in _DETECTS:
        n += _edge_if_ends_exist(g, src, dst, "detects", {"note": note})
    for src, dst, note in _INDICATES:
        n += _edge_if_ends_exist(g, src, dst, "indicates", {"note": note})
    for src, dst, note in _EMPLOYS:
        n += _edge_if_ends_exist(g, src, dst, "employs", {"note": note})
    return n


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
    report["knowledge_tree"] = _import_knowledge_tree(g)
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
