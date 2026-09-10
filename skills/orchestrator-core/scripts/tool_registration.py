#!/usr/bin/env python3
"""
工具注册模块 - 将orchestrator工具注册到AIAgent工具系统

这个模块负责将orchestrator-core的工具注册到AIAgent的工具列表中，
使主智能体能够通过LLM决策调用子智能体。
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any

# 添加项目路径——标记法找项目根(含 shared/ + workspace/)，位置无关，迁移后不会因目录深度算错
def _project_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "shared").is_dir() and (parent / "workspace").is_dir():
            return parent
    return p.parents[3]  # 兜底：标准深度


project_root = _project_root()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def _strategy(key, default):
    """DB 优先读策略(配置中心·策略tab)；backend 不可导入时走默认。"""
    try:
        from backend.services.agent_strategy import get_strategy
        return get_strategy(key, default)
    except Exception:
        return default


# 导入工具桥接——bridge 现与本文件同目录(scripts/)，按文件路径加载最稳
import importlib.util

_bridge_path = Path(__file__).resolve().parent / "orchestrator_core_bridge.py"
_spec = importlib.util.spec_from_file_location("orchestrator_core_bridge", _bridge_path)
bridge_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bridge_module)

call_subagent = bridge_module.call_subagent
list_subagents = bridge_module.list_subagents
create_session = bridge_module.create_session
read_result = bridge_module.read_result


# ── 流式进度通道 ──────────────────────────────────────────────
# /query/stream 端点跑 run_conversation 时，把当前请求的 queue.Queue 设到这里；
# _call_subagent_handler 被（ThreadPoolExecutor 线程）调用时读取它，push 进度事件。
# 靠 start_agent 的 _agent_lock 串行化保证：同一时刻只有一个 run_conversation 在跑，
# 故模块全局安全（contextvars 不会透传到 executor 线程，故用模块全局而非 contextvar）。
_current_progress_queue = None


def _emit_progress(subagent: str, stage: str, summary: str = None, skill_calls=None, evidence=None, chartData=None, action=None):
    """向当前请求的队列 push 进度事件（非流式时队列为 None，no-op）。

    evidence: 结构化证据（异常前几条/违规判定/预警级别），供审计证据链展示；
    chartData: 报告可视化数据（ECharts option 列表），供前端渲染曲线；
    action: 动作指令数据（actionData，如 run_detector 标注），供前端 Dispatcher 执行。
    """
    if _current_progress_queue is None:
        return
    evt = {"type": "progress", "subagent": subagent, "stage": stage}
    if summary:
        evt["summary"] = summary
    if skill_calls:
        evt["skill_calls"] = skill_calls
    if evidence:
        evt["evidence"] = evidence
    if chartData:
        evt["chartData"] = chartData
    if action:
        evt["action"] = action
    try:
        _current_progress_queue.put(evt)
    except Exception:
        pass


def _summarize_result(result) -> str:
    """从子智能体结果里抽一句摘要（异常数/违规判定/数据条数等），给进度事件用。"""
    try:
        r = result.get("result") if isinstance(result, dict) else None
        if isinstance(r, dict):
            if "anomalies" in r:
                return f"{len(r.get('anomalies') or [])} 个异常"
            if "has_violation" in r:
                return f"违规={r.get('has_violation')}, 嫌疑={r.get('suspicion_level')}"
            if "effluent" in r:
                return f"进出水各 {len(r.get('effluent') or [])} 条"
            if isinstance(r.get("alert"), dict):
                return f"预警={r['alert'].get('level_cn', r['alert'].get('level'))}"
    except Exception:
        pass
    return ""


def _extract_evidence(result) -> dict:
    """从子智能体结果提取【结构化证据】（供审计证据链展示，非主智能体）。

    与 _summarize_result（一句话摘要）不同，这里返回结构化 dict：
      异常检测 → {kind:anomaly, count, top:[{metric,time,type,value,score}...]}
      规则推理 → {kind:rule, has_violation, suspicion, types}
      处置执行 → {kind:disposition, level, disposition}
      数据感知 → {kind:data, rows_in, rows_out}
    """
    try:
        r = result.get("result") if isinstance(result, dict) else None
        if not isinstance(r, dict):
            return {}
        ev = {}
        anoms = r.get("anomalies")
        if isinstance(anoms, list):
            ev["kind"] = "anomaly"
            ev["count"] = len(anoms)
            ev["top"] = [{
                "metric": a.get("indicator") or a.get("metric"),
                "time": (a.get("timestamp") or "")[:16],
                "type": a.get("type"),
                "value": a.get("value"),
                "score": round(a.get("score"), 2) if isinstance(a.get("score"), (int, float)) else a.get("score"),
            } for a in anoms[:5]]
        elif "has_violation" in r:
            ev["kind"] = "rule"
            ev["has_violation"] = r.get("has_violation")
            ev["suspicion"] = r.get("suspicion_level")
            ev["types"] = r.get("violation_types") or r.get("patterns") or []
        elif isinstance(r.get("alert"), dict):
            ev["kind"] = "disposition"
            al = r["alert"]
            ev["level"] = al.get("level_cn") or al.get("level")
            ev["disposition"] = al.get("disposition") or al.get("suggestion") or al.get("action")
        elif isinstance(r.get("influent_count"), int) or isinstance(r.get("effluent_count"), int) or isinstance(r.get("effluent"), list):
            ev["kind"] = "data"
            ev["rows_in"] = r.get("influent_count", len(r.get("influent") or []))
            ev["rows_out"] = r.get("effluent_count", len(r.get("effluent") or []))
        return ev
    except Exception:
        return {}


def _compact_result_for_master(result):
    """精简子智能体结果——给主智能体编排决策够用的摘要，不返回原始数据。

    铁律：LLM（主智能体）绝不读原始数据。数据是算子之间通过 SESSION_DIR 文件传递的。
    但 LLM 需要足够的信息回答用户——否则它会调 read_result 去读完整文件（更糟）。
    所以返回 status + 摘要 + 关键数字。
    对数据感知结果，额外计算各指标的统计值（min/max/mean，Python 算不是 LLM 编），
    让主智能体能回答"pH是多少"这类数据查询。
    """
    if not isinstance(result, dict):
        return {"status": "failed", "summary": str(result)[:200]}

    status = result.get("status", "unknown")
    r = result.get("result", {}) if isinstance(result.get("result"), dict) else {}
    summary = _summarize_result(result) or "完成"

    compact = {
        "task_id": result.get("task_id", ""),
        "status": status,
        "summary": summary,
    }

    # 数据感知：计算各指标统计值（Python 算，不是 LLM 编），让主智能体能回答数据查询
    # ★ 多厂通用(2026-08-26)：进水为空(如洗舱站只有排放口)不再跳过整块——出水统计照给,
    #   否则无进水厂永远"没有 data_stats",主智能体会误判为"该厂无数据"。
    infl = r.get("influent")
    effl = r.get("effluent")
    if isinstance(infl, list) or isinstance(effl, list):
        infl = infl if isinstance(infl, list) else []
        effl = effl if isinstance(effl, list) else []
        if not infl and not effl:
            infl = None  # 双侧都空才走"无数据"路径
    if isinstance(infl, list) or isinstance(effl, list):
        n_in = len(infl)
        n_out = len(effl)
        compact["influent_count"] = n_in
        compact["effluent_count"] = n_out
        compact["chart_generated"] = "曲线已由数据感知自动生成（chartData），前端会自动渲染，你不需要自己画"
        stats = {}
        for ind in ("pH", "COD", "TN", "NH3-N", "TP", "SS"):
            infl_vals = [x.get(ind) for x in infl if x.get(ind) is not None]
            effl_vals = [x.get(ind) for x in effl if x.get(ind) is not None]
            if infl_vals or effl_vals:
                s = {}
                if infl_vals:
                    s["influent"] = {"min": round(min(infl_vals), 2), "max": round(max(infl_vals), 2),
                                     "mean": round(sum(infl_vals) / len(infl_vals), 2)}
                if effl_vals:
                    s["effluent"] = {"min": round(min(effl_vals), 2), "max": round(max(effl_vals), 2),
                                     "mean": round(sum(effl_vals) / len(effl_vals), 2)}
                stats[ind] = s
        if stats:
            compact["data_stats"] = stats
        md = r.get("metadata", {})
        if isinstance(md, dict):
            if md.get("time_range"):
                compact["time_range"] = md["time_range"]
            if md.get("plant"):
                compact["plant"] = md["plant"]  # 多厂:标明本结果是哪个厂
        # ★ summary 头条区分"有进水"和"仅出水"(无进水厂),主智能体不再误判"无数据"
        ind_list = ", ".join(stats.keys()) if stats else "各指标"
        if n_in > 0:
            side_txt = f"进出水 {n_in}/{n_out} 条"
        else:
            side_txt = f"出水 {n_out} 条（该监测点无进水监测,属正常）"
        compact["summary"] = (
            f"✅ 数据+曲线已就绪：{side_txt}"
            f"（{ind_list} 的 min/max/mean 见 data_stats）；"
            f"时序曲线 chartData 已生成，前端自动渲染。"
            f"用户要的'曲线/图'已包含——不要为画曲线再调本子智能体。"
        )
        # ★ 多厂归档透传(2026-08-27):子智能体一次调用可能跑了多个厂(data_result.json
        # 只留最后一个厂,主智能体会漏看其他厂)。data_result_plants.json 是逐厂累积统计,
        # 附进 compact.all_plants_stats——主智能体不用再调①就能拿到本会话全部厂的数字。
        try:
            import os as _os
            _sd = _os.environ.get("SESSION_DIR")
            if _sd:
                _pf = Path(_sd) / "data_result_plants.json"
                if _pf.exists():
                    _plants = json.loads(_pf.read_text(encoding="utf-8"))
                    if isinstance(_plants, dict) and len(_plants) > 1:
                        compact["all_plants_stats"] = _plants
                        compact["summary"] += (
                            f" 本次会话已查 {len(_plants)} 个厂,逐厂统计见 all_plants_stats"
                            f"(主文件 data_result 只是其中一厂)——回答多厂问题时逐厂引用它,不要重调①。")
        except Exception:
            pass

    # 异常检测：异常数
    anoms = r.get("anomalies")
    if isinstance(anoms, list):
        compact["anomaly_count"] = len(anoms)

    # 规则推理：嫌疑等级 + 违规类型
    if "suspicion_level" in r:
        compact["suspicion_level"] = r["suspicion_level"]
    if "violation_types" in r:
        vt = r["violation_types"]
        if isinstance(vt, list) and vt:
            compact["violation_types"] = vt

    # 处置执行：处置行动
    if "action" in r:
        compact["action"] = r["action"]

    return compact


def _remount_mcp_tools(agent):
    """把全局 registry 里已注册的 mcp_* 工具 schema 补挂进 agent.tools。

    可重入：registry 里没有(未装 MCP/discover 未跑)时 no-op；有则去重后 extend。
    解决 hermes agent_init 首次 query 重算 agent.tools 冲掉 MCP 的问题(见注册函数内注释)。
    """
    try:
        from tools.registry import registry as _reg
        mcp_names = {n for n in _reg.get_all_tool_names() if str(n).startswith("mcp_")}
        if not mcp_names:
            return
        existing = {t.get('function', {}).get('name') for t in agent.tools if isinstance(t, dict)}
        defs = _reg.get_definitions(mcp_names - existing)
        if defs:
            agent.tools.extend(defs)
    except Exception as e:
        print(f"MCP 工具补挂跳过: {e}")


def register_orchestrator_tools(agent):
    """将orchestrator工具注册到AIAgent实例（hermes-agent兼容版本）

    只有下面两层注册是真正生效的（2026-07-21 端到端验证）：
      1. 把 4 个 schema 灌进 agent.tools —— conversation_loop 只读 agent.tools
         喂给 LLM（completion(tools=agent.tools)）。不灌这里 LLM 看不到工具。
      2. 以 override=True 覆盖注册到 hermes 全局 tools.registry —— dispatch 走全局
         registry，用项目签名正确的 handler 取代 vendored 自带的损坏版
         tools/orchestrator_tool.py。

    历史上还有第三层 agent.tool_registry.register(ToolEntry(...))，但
    agent.tool_registry 在整个 framework 里没有任何读取方（grep 零命中），
    且 vendored ToolEntry 签名已变（要求 toolset/check_fn/requires_env/
    is_async/description/emoji），旧调用必然失败靠回退兜住——纯死代码，已删。

    Args:
        agent: AIAgent实例
    """
    # 确保agent有tools列表
    if not hasattr(agent, 'tools') or agent.tools is None:
        agent.tools = []

    # 第 1 层：把 4 个 orchestrator 工具 schema 灌进 agent.tools。
    _ORCH_SCHEMAS = [
        {"type": "function", "function": {
            "name": "call_subagent",
            "description": "调用指定的子智能体执行任务。可用子智能体：multi-dimensional-data-perception(数据感知)、anomaly-detection(异常检测)、rule-reasoning(规则推理)、disposition-execution(处置执行)",
            "parameters": {"type": "object", "properties": {
                "subagent_name": {"type": "string", "enum": ["multi-dimensional-data-perception", "anomaly-detection", "rule-reasoning", "disposition-execution"], "description": "子智能体名称"},
                "task": {"type": "string", "description": "具体任务描述"},
                "context": {"type": "string", "description": "前置结果（可选）"}
            }, "required": ["subagent_name", "task"]}
        }},
        {"type": "function", "function": {
            "name": "list_subagents", "description": "列出所有可用的子智能体及其功能",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }},
        {"type": "function", "function": {
            "name": "create_session", "description": "创建新的会话目录用于子智能体通信",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }},
        {"type": "function", "function": {
            "name": "read_result", "description": "读取子智能体的执行结果文件",
            "parameters": {"type": "object", "properties": {
                "result_file": {"type": "string", "description": "结果文件名"}
            }, "required": ["result_file"]}
        }},
        {"type": "function", "function": {
            "name": "run_detector",
            "description": "对监测数据跑异常检测算法并在大屏标注。当用户指令是检测类动作(如'检测pH平稳异常''检测COD突变''用孤立森林检测')时调用。纯问答(如'pH是多少')不要调。时间范围:用户消息带[大屏当前观看窗口]注记且未明确指定时间→必须用注记的段起/段止;否则用户说了日期用日期;都没提传 now(脚本自动取数据最新点24h)。",
            "parameters": {"type": "object", "properties": {
                "algorithm": {"type": "string", "enum": ["constant", "changepoint", "iforest"],
                              "description": "算法: constant=平稳/恒定检测, changepoint=突变检测, iforest=孤立森林离群检测"},
                "indicator": {"type": "string", "enum": ["pH", "COD", "TN", "NH3-N", "TP", "SS"],
                              "description": "监测指标"},
                "start": {"type": "string", "description": "开始时间 YYYY-MM-DD 或 'YYYY-MM-DD HH:MM' 或 'now'。用户消息带[大屏当前观看窗口]注记时=注记的段起"},
                "end": {"type": "string", "description": "结束时间,同 start 格式;注记时=注记的段止;无注记无日期传 now"}
            }, "required": ["algorithm", "indicator", "start", "end"]}
        }},
        {"type": "function", "function": {
            "name": "query_history",
            "description": "查询历史研判记录与违规案例（图谱案例库+事件表合并，秒回）。当用户问'XX厂历史上有没有违规''以前的案例''最近的研判结论是什么''上次判了什么'这类历史/案例/既往问题时必须先调本工具再回答——不要现场重跑研判管线、不要拿大屏当前窗口当研判历史。查完有结果直接引用作答；无结果如实说没有记录。普通数据查询/研判类问题（问某天数据如何）不调本工具。",
            "parameters": {"type": "object", "properties": {
                "plant": {"type": "string", "description": "厂名或别名（如'金桥'），空=全部厂"},
                "limit": {"type": "integer", "description": "最多返回条数，默认10"}
            }, "required": []}
        }},
    ]
    existing = {t.get('function', {}).get('name') for t in agent.tools if isinstance(t, dict)}
    for s in _ORCH_SCHEMAS:
        if s['function']['name'] not in existing:
            agent.tools.append(s)

    # 砍掉真·分心工具（terminal/browser/memory/execute_code/skill_manage 等），但
    # 【保留 skill_view + skills_list】——主智能体必须能用 skill_view 读自己的编排技能
    # orchestrator-core/SKILL.md（AGENTS.md 要求"先 skill_view('orchestrator-core')
    # 再 call_subagent"）。之前把 skill_view 一起砍了，导致主智能体根本读不到编排规则，
    # 只能瞎猜、时对时错（有时只调①、有时跑全链①②③④）。
    # 【保留 mcp_* 工具】——MCP 是配置中心装的外部能力(Filesystem 查知识库/Fetch 抓网页/
    # InfluxDB 即席查/Memory 记忆)。实测(2026-08-29): hermes agent_init 在首次 query 时会
    # 用内置工具表重算 agent.tools,把启动时挂载的 MCP 工具冲掉——所以这里精简后重新从
    # registry 拉 mcp 工具挂回来(可重入:无论工具表何时被重算,MCP 都会回来)。
    _KEEP_NAMES = {s['function']['name'] for s in _ORCH_SCHEMAS} | {"skill_view", "skills_list"}
    before_n = len(agent.tools)
    agent.tools = [t for t in agent.tools if isinstance(t, dict)
                   and (t.get('function', {}).get('name') in _KEEP_NAMES
                        or str(t.get('function', {}).get('name', '')).startswith('mcp_'))]
    # 精简后补挂 MCP 工具(从全局 registry 取,discover 阶段已注册进来;没配 MCP 时空列表 no-op)
    _remount_mcp_tools(agent)
    # ★ 同步刷新 valid_tool_names(2026-08-30 根因修复):conversation_loop 用这个集合做
    # 调用合法性闸门——初始化时算的旧集合(17 个,无 mcp_*)会让 LLM 的 mcp 工具调用
    # 全部被判 "Unknown tool" 回错误,模型试几次后就学会宣称"工具不存在"。
    # agent.tools 扩了集合必须跟着扩,否则工具表有 79 个但只有旧集合里的能调。
    try:
        if hasattr(agent, "valid_tool_names"):
            agent.valid_tool_names = {t.get('function', {}).get('name')
                                      for t in agent.tools if isinstance(t, dict)}
    except Exception as _e:
        print(f"valid_tool_names 刷新跳过: {_e}")
    print(f"主智能体工具精简：{before_n} → {len(agent.tools)}（保留编排工具 + skill_view/skills_list + MCP，移除 terminal/browser 等分心工具）")

    # 第 2 层：覆盖注册到 hermes 全局 registry。vendored hermes 自带的
    # tools/orchestrator_tool.py 是多处损坏的桥接（handler 签名错、schema 双层包裹
    # 致 LLM 400），这里用本项目签名正确、走 bridge、schema 正确的 handler 以
    # override=True 覆盖，让 dispatch 真正走通。
    try:
        from tools.registry import registry as _hg
        _OVR = [
            ("call_subagent", _call_subagent_handler, _ORCH_SCHEMAS[0]["function"]),
            ("list_subagents", _list_subagents_handler, _ORCH_SCHEMAS[1]["function"]),
            ("create_session", _create_session_handler, _ORCH_SCHEMAS[2]["function"]),
            ("read_result", _read_result_handler, _ORCH_SCHEMAS[3]["function"]),
            ("run_detector", _run_detector_handler, _ORCH_SCHEMAS[4]["function"]),
            ("query_history", _query_history_handler, _ORCH_SCHEMAS[5]["function"]),
        ]
        for _n, _h, _sch in _OVR:
            _hg.register(
                name=_n, toolset="orchestrator", schema=_sch, handler=_h,
                check_fn=lambda: True, requires_env=[], is_async=False, override=True,
            )
        print(f"已覆盖注册 {len(_OVR)} 个 orchestrator 工具到 hermes 全局 registry")
    except Exception as _e:
        print(f"⚠ orchestrator 全局 registry 覆盖失败: {_e}")


# Hermes-agent兼容的工具处理器（灵活签名以兼容多种调用方式）
def _query_history_handler(*args, **kwargs) -> str:
    """query_history 工具处理器：查历史研判/案例（图谱+事件表双源，秒回）。
    实现 query_history.py（2026-09-10 修复实测问题：历史类问题答非所问/漏写回案例）。
    目录名带连字符（orchestrator-core）不可 import——用 importlib 按文件路径加载。"""
    import importlib.util as _ilu
    _p = Path(__file__).resolve().parent / "query_history.py"
    _spec = _ilu.spec_from_file_location("_qhist", _p)
    _mod = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    return _mod._handler(*args, **kwargs)


def _guard_perception_result(result, task_text, session_dir):
    """感知①结果守卫(2026-08-27):LLM 构造 get_data 命令丢参(厂/时间)不稳定——
    校验产出,不符则用任务文本解析的参数确定性重跑脚本,覆盖错误结果。

    校验项:plant 为空(全库混合)、metadata.time_range 不含任务要求的日期。
    返回修正后的 result(或原 result)。"""
    try:
        if not isinstance(result, dict) or result.get("status") != "completed":
            return result
        r = result.get("result") or {}
        md = r.get("metadata") or {}
        plant = md.get("plant") or ""
        tr = str(md.get("time_range") or "")
        import re as _re
        # 任务要求的日期(显式 YYYY-MM-DD 或 YYYY年M月D日)
        m = _re.search(r'(20\d{2})[-年](\d{1,2})[-月](\d{1,2})', task_text or "")
        want_date = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else ""
        # 任务要求的厂
        want_plant = None
        for alias, pid in {"金桥": "当阳市金桥污水处理厂一期",
                           "洗舱站": "洗舱站污水排放口"}.items():
            if alias in (task_text or ""):
                want_plant = pid
                break
        bad_plant = (not plant) and bool(want_plant)          # 混库
        bad_date = bool(want_date) and want_date not in tr    # 时间窗回退
        # 指标校验:任务点名了指标(如"只要COD"),图的 series 却画了全指标 → 也重跑
        want_inds = []
        for cn, en in [("pH", "pH"), ("COD", "COD"), ("化学需氧量", "COD"), ("总氮", "TN"),
                       ("氨氮", "NH3-N"), ("总磷", "TP"), ("悬浮物", "SS")]:
            if cn in (task_text or "") and en not in want_inds:
                want_inds.append(en)
        got_series = []
        for c in (r.get("chartData") or []):
            got_series += [s.get("name") for s in (c.get("option") or {}).get("series") or []]
        # 图里的中文名→英文键粗映射,比对集合
        _cn2en = {"COD": "COD", "pH": "pH", "总氮": "TN", "氨氮": "NH3-N", "总磷": "TP", "悬浮物": "SS"}
        got_en = {_cn2en.get(n, n) for n in got_series}
        bad_inds = bool(want_inds) and bool(got_en) and not set(want_inds) >= got_en
        if not (bad_plant or bad_date or bad_inds):
            return result
        # 确定性重跑:从任务文本解析参数(entry 已有同款解析,这里内联精简版)
        import subprocess as _sp
        import sys as _sys
        # 项目根:tool_registration.py 在 skills/orchestrator-core/scripts/ 下,parents[2]=skills/,parents[3]=项目根
        script = Path(__file__).resolve().parents[3] / "subagents" / "multi-dimensional-data-perception-agent" / "skills" / "data-perception-core" / "scripts" / "get_data.py"
        if not script.exists():
            return result
        args = []
        m2 = _re.search(r'(20\d{2}-\d{2}-\d{2})\s*(?:00:00)?\s*(?:至|~|-|到)\s*(20\d{2}-\d{2}-\d{2})', task_text or "")
        if want_date:
            args += ["--start", want_date, "--end", want_date]
        elif m2:
            args += ["--start", m2.group(1), "--end", m2.group(2)]
        else:
            args += ["--hours", "24"]
        if want_plant:
            args += ["--plant", want_plant]
        inds = []
        for cn, en in [("pH", "pH"), ("COD", "COD"), ("化学需氧量", "COD"), ("总氮", "TN"),
                       ("氨氮", "NH3-N"), ("总磷", "TP"), ("悬浮物", "SS")]:
            if cn in (task_text or "") and en not in inds:
                inds.append(en)
        if inds:
            args += ["--chart-indicators", ",".join(inds)]
        env = dict(os.environ)
        if session_dir:
            env["SESSION_DIR"] = str(session_dir)
        rp = _sp.run([_sys.executable, str(script)] + args, capture_output=True,
                     text=True, encoding="utf-8", errors="replace", timeout=120, env=env)
        print(f"[感知守卫] 参数不符(plant='{plant}' tr='{tr[:20]}' want={want_plant or '-'}{want_date}) → 确定性重跑 rc={rp.returncode}")
        if rp.returncode == 0 and session_dir:
            p = Path(session_dir) / "data_result.json"
            if p.exists():
                fixed = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(fixed, dict) and fixed.get("status") == "completed":
                    return fixed
        return result
    except Exception as e:
        print(f"[感知守卫] 异常(返回原结果): {e}")
        return result


def _call_subagent_handler(*args, **kwargs) -> str:
    """call_subagent工具的hermes-agent兼容处理器

    支持多种调用方式：
    - handler(args_dict) - Hermes Agent传统方式
    - handler(function_name, function_args) - 新式方式
    - handler(function_name="xxx", function_args={...}) - 关键字方式

    Returns:
        str: JSON格式的结果字符串
    """
    try:
        # 解析参数：支持多种调用方式
        if args and isinstance(args[0], dict):
            # 传统方式：handler(args_dict)
            params = args[0]
        elif 'function_args' in kwargs:
            # 新式关键字方式：handler(function_name="xxx", function_args={...})
            params = kwargs['function_args']
        elif args and len(args) >= 2 and isinstance(args[1], dict):
            # 新式位置方式：handler(function_name, function_args)
            params = args[1]
        else:
            # 回退：使用kwargs作为参数
            params = kwargs

        # 调用原始函数（向流式队列吐进度）
        subagent_name = params.get('subagent_name') or params.get('name') or 'unknown'
        _emit_progress(subagent_name, 'start')
        result = call_subagent(**params)
        # 感知①结果守卫:LLM 丢参(混库/时间回退)→确定性重跑修正。
        # 策略开关(配置中心·策略tab):perception_guard_enabled=False 跳过守卫(每调用读,立即生效)
        if subagent_name == "multi-dimensional-data-perception" and _strategy("perception_guard_enabled", True):
            _task_txt = str(params.get('task') or '')
            _sd = os.environ.get("SESSION_DIR") or ""
            result = _guard_perception_result(result, _task_txt, _sd)
        _sc = result.get("skill_calls") if isinstance(result, dict) else None
        _ev = _extract_evidence(result)
        # None 保护:子智能体失败时 result 里键存在但值为 null(如 result:None),
        # .get("result",{}) 默认值不生效,.get("chartData") 直接崩——真实错误被吞
        _r = result.get("result") if isinstance(result, dict) else None
        _cd = _r.get("chartData") if isinstance(_r, dict) else None
        _emit_progress(subagent_name, 'done', _summarize_result(result), skill_calls=_sc, evidence=_ev, chartData=_cd)
        # 给主智能体回传精简版：去掉大数据数组（进/出水原始行），只留摘要+关键字段。
        # 完整结果已在 session 文件，下游子智能体从文件读；主智能体不该背原始数据
        # （一周 53K 会撑爆上下文/迭代预算）。需要细节时用 read_result 取。
        compact = _compact_result_for_master(result)
        if isinstance(compact, dict):
            return json.dumps(compact, ensure_ascii=False)
        return str(compact)
    except Exception as e:
        error_msg = f"子智能体调用失败: {str(e)}"
        return json.dumps({"success": False, "error": error_msg}, ensure_ascii=False)


def _list_subagents_handler(*args, **kwargs) -> str:
    """list_subagents工具的hermes-agent兼容处理器

    支持多种调用方式，参见 _call_subagent_handler

    Returns:
        str: JSON格式的结果字符串
    """
    try:
        result = list_subagents()
        if isinstance(result, dict):
            return json.dumps(result, ensure_ascii=False)
        return str(result)
    except Exception as e:
        error_msg = f"列出子智能体失败: {str(e)}"
        return json.dumps({"success": False, "error": error_msg}, ensure_ascii=False)


def _create_session_handler(*args, **kwargs) -> str:
    """create_session工具的hermes-agent兼容处理器

    支持多种调用方式，参见 _call_subagent_handler

    Returns:
        str: JSON格式的结果字符串
    """
    try:
        session_dir = create_session()
        return json.dumps({"session_dir": session_dir}, ensure_ascii=False)
    except Exception as e:
        error_msg = f"创建会话失败: {str(e)}"
        return json.dumps({"success": False, "error": error_msg}, ensure_ascii=False)


def _read_result_handler(*args, **kwargs) -> str:
    """read_result 已废弃——主智能体不应读结果文件。

    编排铁律：call_subagent 返回的摘要已足够编排决策。读完整结果文件会把原始数据
    灌进 LLM 上下文（撑爆 token + 浪费 turn）。如果需要细节，调对应子智能体。
    """
    return json.dumps({
        "success": False,
        "error": "read_result 已废弃。call_subagent 返回的摘要已足够编排决策。"
                 "原始数据由子智能体之间通过文件传递，主智能体不需要读。"
                 "编排铁律：数据感知→异常检测→规则推理→处置执行，4步完成，不读结果文件。"
    }, ensure_ascii=False)


def _run_detector_handler(*args, **kwargs) -> str:
    """run_detector 工具处理器：直接 subprocess 跑轻量算子脚本(1-3秒,不经LLM)。

    窗口兜底：LLM 没传有效 start/end 时，用 agent 服务注入的 _current_view_context
    （大屏观看窗口）——检测的永远是用户眼前正在看的时段,标注才能落在窗口内。
    """
    import subprocess
    if args and isinstance(args[0], dict):
        params = args[0]
    elif 'function_args' in kwargs:
        params = kwargs['function_args']
    elif args and len(args) >= 2 and isinstance(args[1], dict):
        params = args[1]
    else:
        params = kwargs

    start = str(params.get("start", "") or "")
    end = str(params.get("end", "") or "")
    vc = getattr(_run_detector_handler, "_view_context", None) or {}
    # start/end 是 now/空 且有观看窗口 → 用窗口段起止兜底
    if (not start or start == "now") and vc.get("segmentStart"):
        start = str(vc["segmentStart"])
    if (not end or end == "now") and vc.get("segmentEnd"):
        end = str(vc["segmentEnd"])

    script = Path(__file__).resolve().parents[2] / "action-command-core" / "scripts" / "run_detector.py"
    cmd = [sys.executable, str(script),
           "--algorithm", str(params.get("algorithm", "constant")),
           "--indicator", str(params.get("indicator", "pH")),
           "--start", start or "now",
           "--end", end or "now"]
    # 环境变量兜底:LLM 若用 terminal 直接跑脚本(绕过本 handler),脚本自己也认这组变量
    env = {**os.environ}
    if vc.get("segmentStart"): env["DETECTOR_START"] = str(vc["segmentStart"])
    if vc.get("segmentEnd"): env["DETECTOR_END"] = str(vc["segmentEnd"])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60, env=env)
        out_str = r.stdout.strip()
        # 透传 action 事件给前端（run_detector 的 actionData → 大屏标注）
        try:
            out = json.loads(out_str) if out_str else {}
            if isinstance(out, dict) and out.get("actionData"):
                _emit_progress("action-command", "done",
                               summary=f"检出 {len(out.get('anomalies') or [])} 个异常",
                               action=out["actionData"])
        except Exception:
            pass
        return out_str or json.dumps(
            {"status": "failed", "error": r.stderr[-300:]}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "failed", "error": f"run_detector 执行失败: {e}"},
                          ensure_ascii=False)


# 导出函数
__all__ = [
    "register_orchestrator_tools",
    "handle_orchestrator_tool_call"
]


def handle_orchestrator_tool_call(tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
    """处理orchestrator工具调用（由conversation_loop调用）

    Args:
        tool_name: 工具名称
        tool_args: 工具参数

    Returns:
        Dict[str, Any]: 工具执行结果
    """
    try:
        # 根据工具名称调用相应的处理器
        tool_handlers = {
            "call_subagent": _call_subagent_handler,
            "list_subagents": _list_subagents_handler,
            "create_session": _create_session_handler,
            "read_result": _read_result_handler,
            "run_detector": _run_detector_handler
        }

        if tool_name not in tool_handlers:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}"
            }

        # 调用处理器（传递正确的参数）
        handler = tool_handlers[tool_name]
        result_str = handler(
            function_name=tool_name,
            function_args=tool_args
        )

        # 解析JSON结果
        try:
            result = json.loads(result_str) if isinstance(result_str, str) else result_str
        except:
            result = {"result": result_str}

        return result

    except Exception as e:
        return {
            "success": False,
            "error": f"Tool call failed: {str(e)}"
        }
