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

from shared.knowledge_graph.graph_store import EDGE_TYPES, GraphStore  # noqa: E402

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
               "desc": "数据缺失率异常(>20%)/夜间缺失/设备离线/时段空白类逃避监测"
                       "（缺检测实现 TODO）",
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
               "note": "监测义务：自行监测/保存原始记录/保证监测设备正常运行"}},
    {"id": "regulation:water_law_s39", "label": "水污染防治法§39",
     "props": {"law": "中华人民共和国水污染防治法", "article": "第三十九条",
               "note": "禁止条款：禁止私设暗管/篡改伪造监测数据/不正常运行设施等逃避监管方式排放"}},
    {"id": "regulation:water_law_s83", "label": "水污染防治法§83",
     "props": {"law": "中华人民共和国水污染防治法", "article": "第八十三条",
               "note": "罚则：§83(三)逃避监管方式排放的行政处罚（10-100万）"}},
]

# operator → pattern (detects)；来源注释为证
# 审计 2026-09-09 修正：删 forgery_detector/isolation_forest→malicious_evasion
# 两条错边（造假四法检测在场数据统计异常、孤立森林是通用离群打分，
# 而恶意逃避是数据缺失型——方法与定义错位，见 violation_patterns.md §1.4）
_DETECTS: List[Tuple[str, str, str]] = [
    ("operator:specialized:constant_detector", "pattern:bottle_interference",
     "恒定检测 std/CV/唯一值三法（constant_detector.py）"),
    ("operator:specialized:change_point_detector", "pattern:dilution_discharge",
     "突变特征是插瓶(工艺规则2)与稀释(工艺规则3)的共有前提；稀释判定实际由 "
     "process_validator 规则3(多指标同步突降>50%+浓度低位)完成"),
    ("operator:specialized:smoothness_detector", "pattern:artificial_fitting",
     "平滑度检测（smoothness_detector.py:104）"),
]
# pattern → regulation (indicates)；法条号来自典型违规模式.md 各节"违规定性"
# 审计 2026-09-09 修正+裁决补全：篡改类（插瓶/人工拟合）锚 §39(禁止)+§83(罚则)
# ——§39 明文"禁止篡改、伪造监测数据"是行为定性条款，§83(三)是罚则；
# §23(监测义务)留给虚假申报类（虚假停产，源文 :93）；原错：篡改类只连 §23、
# 虚假停产错连 §83。暗管/稀释也补 §39（§39 明列"私设暗管"与逃避监管方式）。
_INDICATES: List[Tuple[str, str, str]] = [
    ("pattern:bottle_interference", "regulation:water_law_s39",
     "干扰采样=篡改伪造监测数据，§39 禁止条款（行为定性）"),
    ("pattern:bottle_interference", "regulation:water_law_s83",
     "插瓶属篡改伪造类，§83(三)是罚则锚点"),
    ("pattern:secret_pipe", "regulation:water_law_s39",
     "§39 明文禁止私设暗管（行为定性）"),
    ("pattern:secret_pipe", "regulation:water_law_s83", "私设暗管罚则（§二）"),
    ("pattern:dilution_discharge", "regulation:water_law_s39",
     "稀释属逃避监管方式排放，§39 禁止（§三）"),
    ("pattern:dilution_discharge", "regulation:water_law_s83", "清水稀释罚则（§三）"),
    ("pattern:artificial_fitting", "regulation:water_law_s39",
     "数据篡改，§39 禁止篡改伪造监测数据（§四）"),
    ("pattern:artificial_fitting", "regulation:water_law_s83",
     "篡改伪造监测数据，§83(三)罚则（源文 :74 引两条）"),
    ("pattern:false_shutdown", "regulation:water_law_s23",
     "虚假申报类违反监测义务，源文 :93 引第二十三条（原错连 §83）"),
    ("pattern:malicious_evasion", "regulation:water_law_s39",
     "恶意逃避属逃避监管方式，§39 禁止"),
    ("pattern:malicious_evasion", "regulation:water_law_s83", "恶意逃避监管罚则"),
]
# agent → operator (employs)；来源 run_anomaly_detection_simple.py imports
# (:25-27 五特征算子 import + :266-269 detectors 列表)
_EMPLOYS: List[Tuple[str, str, str]] = [
    ("agent:anomaly-detection", "operator:specialized:constant_detector",
     "平稳特征检测"),
    ("agent:anomaly-detection", "operator:specialized:change_point_detector",
     "突变特征检测"),
    ("agent:anomaly-detection", "operator:specialized:trend_detector",
     "趋势特征检测"),
    ("agent:anomaly-detection", "operator:specialized:periodicity_detector",
     "周期特征检测"),
    ("agent:anomaly-detection", "operator:specialized:high_freq_detector",
     "高频波动特征检测"),
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
               "skills": ["rule-reasoning-core", "graph-query"]}},
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
    ("service:agent_service", "service:frontend",
     "经 backend /api/query/stream 透传的逻辑数据流(非直连)"),
]
# 审计 2026-09-09 修正：删 rule-reasoning→sqlite_logs（零代码依据）；
# 删 disposition→sqlite_logs 的 writes（处置真实写的是会话目录结果文件
# sessions/<session>/——是中转不是库）。
# 2026-09-11 补真实边（子4 审查发现 sqlite_logs 零边孤岛）：backend 真实读写
# SQLite 日志库——conversation_service（对话历史）/event_service（事件+图谱写回
# 的入口侧）/logging 中间件（api_call_logs）都经 SessionLocal 连 ecological_logs.db
# （grep 证据：三文件 SessionLocal import + query.py 落库调用）。
_READS = [
    ("agent:multi-dimensional-data-perception", "service:influxdb",
     "get_data 取数"),
    ("service:backend", "service:sqlite_logs",
     "对话历史/事件/审计日志读写（conversation_service+event_service+logging 中间件）"),
]
_WRITES: List[Tuple[str, str, str]] = []
# event_service 的图谱写回发生在 backend 进程内，但图数据文件在 shared/data/
# （与日志库同库族）；图谱连通性由 hosts/reads 已覆盖，不单列 writes。

# ── 技能（skill）目录：主智能体 + 4 子智能体的真实技能（各 skills/ 目录） ──
SKILLS: List[Tuple[str, str, str]] = [
    # (skill 名, 归属 agent, 说明)
    ("orchestrator-core", "agent:master", "编排技能：停止铁律/task写法/结果整合"),
    ("action-command-core", "agent:master", "动作指令：分类器+检测短路"),
    ("plant-onboarding", "agent:master", "新厂接入向导"),
    ("regulation-lookup", "agent:master", "法规查询"),
    ("data-perception-core", "agent:multi-dimensional-data-perception", "取数主技能 get_data"),
    ("data-export", "agent:multi-dimensional-data-perception", "导出 CSV"),
    ("anomaly-detection-core", "agent:anomaly-detection", "检测主技能 5类特征+孤立森林"),
    ("rule-reasoning-core", "agent:rule-reasoning", "判定主技能 工艺规则+嫌疑矩阵"),
    ("graph-query", "agent:rule-reasoning", "查图谱:模式/案例/法条"),
    ("disposition-execution-core", "agent:disposition-execution", "处置主技能 工单+预警"),
    ("report-generator", "agent:disposition-execution", "日报/周报生成"),
]
# 主智能体运行时工具（tool_registration.py 精简后的 6 个 + MCP）
MASTER_TOOLS: List[Tuple[str, str]] = [
    ("call_subagent", "调用子智能体（核心编排工具）"),
    ("run_detector", "动作指令直调检测算子（不经 LLM）"),
    ("list_subagents", "列出可用子智能体"),
    ("create_session", "建会话目录（sessions/ 通信）"),
    ("read_result", "读子智能体结果（已废弃，防上下文撑爆）"),
    ("skill_view", "读技能 SKILL.md（hermes 原生，读编排技能用）"),
    ("skills_list", "列技能清单（hermes 原生）"),
]
# MCP 服务器（根 config.yaml mcp_servers 段，npx 启动）
MCPS: List[Tuple[str, str]] = [
    ("fetch", "网页抓取 @kazuph/mcp-fetch"),
    ("memory", "跨会话记忆 @modelcontextprotocol/server-memory"),
    ("filesystem", "文件系统（shared/knowledge 目录）"),
    ("influxdb", "InfluxDB 查询（community influxdb-mcp-server）"),
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
        # 市→厂区→厂 三级层级（category 复用：与算子库的分类同级语义）
        city_id = f"category:city:{city}"
        g.upsert_node(city_id, "category", city, {"parent": "厂区层级", "level": "市"})
        for district, plants in districts.items():
            if not isinstance(plants, list):
                continue
            district_id = f"category:district:{city}:{district}"
            g.upsert_node(district_id, "category", district,
                          {"parent": city, "level": "厂区"})
            g.upsert_edge(district_id, city_id, "belongs_to")
            for pid in plants:
                g.upsert_node(f"plant:{pid}", "plant", pid,
                              {"city": city, "district": district})
                g.upsert_edge(f"plant:{pid}", district_id, "belongs_to")
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
    # 数据库（三库一体的第三库）：时序监测数据库 → 指标归属
    # （InfluxDB monitoring-real bucket；指标是库里的 fields）
    g.upsert_node("library:database", "library", "时序监测数据库",
                  {"path": "shared/data", "engine": "InfluxDB 2.7",
                   "bucket": "monitoring-real", "measurement": "wastewater",
                   "desc": "三库一体之一——真实报表导入的时序监测数据"})
    for ind in indicators:
        g.upsert_node(f"indicator:{ind['field']}", "indicator",
                      ind["label"],
                      {"field": ind["field"], "unit": ind["unit"]})
        g.upsert_edge(f"indicator:{ind['field']}", "library:database", "belongs_to")
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
                           "note": op.get("note", ""),
                           "params": op.get("params", {}),
                           "data_type": op.get("data_type", []),
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
    # specialized 检测器的真实默认参数：从代码 __init__ 签名抽（inspect），
    # 点开节点即见"参数设定是多少"（用户需求），而非笼统描述
    spec_params: Dict[str, Dict] = {}
    try:
        import inspect
        import importlib
        import sys as _sys
        if str(_ROOT) not in _sys.path:
            _sys.path.insert(0, str(_ROOT))
        for key in name_map:
            try:
                mod = importlib.import_module(
                    f"shared.operators.specialized.{key}")
                cls = next((getattr(mod, c) for c in dir(mod)
                            if c[0].isupper() and inspect.isclass(getattr(mod, c))
                            and getattr(getattr(mod, c), "__module__", "").endswith(key)),
                           None)
                if cls:
                    sig = inspect.signature(cls.__init__)
                    spec_params[key] = {
                        p.name: (p.default if p.default is not inspect.Parameter.empty else "必填")
                        for p in sig.parameters.values() if p.name != "self"
                    }
            except Exception:
                pass
    except Exception as e:
        print(f"[seed] 提示: 专用检测器参数抽取失败({e})，仅导名称")
    for py in sorted(spec_dir.glob("*.py")):
        key = py.stem
        if key == "__init__":
            continue
        g.upsert_node(f"operator:specialized:{key}", "operator",
                      name_map.get(key, key),
                      {"category": "specialized", "desc": "专用违规模式检测器",
                       "params": spec_params.get(key, {})})
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

    # 知识库四库补全：工艺知识库 + 专家经验库（此前只有两库）
    g.upsert_node("category:process_knowledge", "category", "工艺知识库",
                  {"parent": "知识库", "path": "shared/knowledge/process_knowledge"})
    g.upsert_node("category:expert_experience", "category", "专家经验库",
                  {"parent": "知识库", "path": "shared/knowledge/expert_experience"})
    g.upsert_edge("category:process_knowledge", "library:knowledge", "belongs_to")
    g.upsert_edge("category:expert_experience", "library:knowledge", "belongs_to")
    # 工艺知识库实体：生化处理工艺（真实文档）
    g.upsert_node("knowledge_doc:bio_process", "knowledge_doc", "生化处理工艺",
                  {"file": "生化处理工艺.md",
                   "sections": ["工艺原理", "正常工况指标关系", "异常工况识别", "工艺异常模式"]})
    g.upsert_edge("knowledge_doc:bio_process", "category:process_knowledge", "belongs_to")
    # 专家经验库实体：典型违规模式 + 嫌疑规则 R001-R010（suspicion_rules.py 真实导出）
    g.upsert_node("knowledge_doc:typical_violations", "knowledge_doc", "典型违规模式",
                  {"file": "典型违规模式.md",
                   "sections": ["插瓶干扰", "暗管偷排", "清水稀释", "数据篡改", "虚假停产", "工况造假"]})
    g.upsert_edge("knowledge_doc:typical_violations", "category:expert_experience", "belongs_to")
    try:
        from shared.knowledge.expert_experience.suspicion_rules import RULES
        for r in RULES:
            g.upsert_node(f"expert_rule:{r.rule_id}", "knowledge_doc", f"{r.rule_id} {r.name}",
                          {"name": r.name, "desc": r.description,
                           "score": getattr(r, "suspicion_score", None)})
            g.upsert_edge(f"expert_rule:{r.rule_id}", "category:expert_experience", "belongs_to")
    except Exception as e:
        print(f"[seed] 警告: 嫌疑规则导入失败({e})，仅导典型违规模式文档")

    # 排放标准（GB 18918-2002 一级A标，排放标准.md 真实表格）：
    # 标准节点挂法规库，限值经 limits 边关联指标（超标判定基准）
    g.upsert_node("regulation:gb18918", "regulation", "GB 18918-2002 排放标准",
                  {"law": "城镇污水处理厂污染物排放标准", "grade": "一级A标",
                   "note": "基本控制项目最高允许排放浓度（日均值）"})
    g.upsert_edge("regulation:gb18918", "category:regulations", "belongs_to")
    limits_rows = [("pH", "6-9", ""), ("COD", "50 mg/L", ""),
                   ("TN", "15 mg/L", ""), ("AN", "5(8) mg/L",
                                           "括号内=水温≤12℃时限值"),
                   ("TP", "0.5 mg/L", ""), ("suspended_solids", "10 mg/L", "")]
    for field, limit, note in limits_rows:
        g.upsert_edge(f"indicator:{field}", "regulation:gb18918", "limits",
                      {"value": limit, **({"note": note} if note else {})})
    return 5  # 顶层骨架节点数（其余实体在幂等 upsert 里）


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
    # 服务簇↔智能体簇的桥：Agent 服务承载主智能体运行（无此边两簇不连通）
    g.upsert_edge("service:agent_service", "agent:master", "hosts",
                  {"note": "AIAgent 会话跑在 8642 服务进程内"})
    for src, dst, note in _CALLS:
        g.upsert_edge(src, dst, "calls", {"note": note})
    for src, dst, note in _READS:
        g.upsert_edge(src, dst, "reads", {"note": note})
    for src, dst, note in _WRITES:
        g.upsert_edge(src, dst, "writes", {"note": note})

    # ── 技能/工具/MCP：服务拓扑的丰满层 ──
    # 技能节点（各 agent 的 skills/ 目录实体）经 uses 边挂 agent
    for skill, owner, desc in SKILLS:
        g.upsert_node(f"skill:{skill}", "skill", skill, {"desc": desc})
        g.upsert_edge(owner, f"skill:{skill}", "uses")
    # 主智能体运行时工具（6 个精简编排工具）经 invokes 边挂主智能体
    for tool, desc in MASTER_TOOLS:
        g.upsert_node(f"tool:{tool}", "tool", tool, {"desc": desc})
        g.upsert_edge("agent:master", f"tool:{tool}", "invokes")
    # MCP 服务器（config.yaml mcp_servers，npx 子进程）挂 Agent 服务
    for name, desc in MCPS:
        g.upsert_node(f"mcp:{name}", "mcp", f"MCP {name}", {"desc": desc,
                                                             "runtime": "npx"})
        g.upsert_edge("service:agent_service", f"mcp:{name}", "mounts")
    # 库连接（复用 library 节点，领域/拓扑两 tab 的桥）：agents 经 reads/writes 摸三库
    for agent_id, lib_id, etype, note in [
        ("agent:anomaly-detection", "library:operators", "reads", "调 shared/operators 算子"),
        ("agent:rule-reasoning", "library:knowledge", "reads", "查知识四库"),
        ("agent:multi-dimensional-data-perception", "library:database", "reads", "InfluxDB 取数"),
        ("agent:disposition-execution", "library:knowledge", "reads",
         "工单法规引用为硬编码占位符（work_order_generator.py:111 '第XX条'），未实读知识库"),
    ]:
        _edge_if_ends_exist(g, agent_id, lib_id, etype, {"note": note})
    return len(AGENTS) + len(SERVICES) + len(SKILLS) + len(MASTER_TOOLS) + len(MCPS)


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
    # 种子自有边类型先清后写：映射表删了边，重灌必须同步从图里消失
    # （upsert 幂等只更新已存在的键，删掉的映射会留陈旧边——审计教训）。
    # 仅 cites（种子案例+研判沉淀共用）与 involves（研判写回）不清。
    g.delete_edges(sorted(EDGE_TYPES - {"cites", "involves"}))
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
