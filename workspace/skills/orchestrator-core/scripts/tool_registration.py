#!/usr/bin/env python3
"""
工具注册模块 - 将orchestrator工具注册到AIAgent工具系统

这个模块负责将orchestrator-core的工具注册到AIAgent的工具列表中，
使主智能体能够通过LLM决策调用子智能体。
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any

# 添加项目路径
project_root = Path(__file__).parents[4]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 导入工具桥接
try:
    from workspace.skills.orchestrator_core_bridge import (
        call_subagent,
        list_subagents,
        create_session,
        read_result
    )
except ImportError:
    # 如果直接导入失败，通过脚本导入
    import importlib.util
    bridge_path = project_root / "workspace" / "skills" / "orchestrator_core_bridge.py"
    spec = importlib.util.spec_from_file_location("orchestrator_core_bridge", bridge_path)
    bridge_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bridge_module)

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


def _emit_progress(subagent: str, stage: str, summary: str = None, skill_calls=None, evidence=None, chartData=None):
    """向当前请求的队列 push 进度事件（非流式时队列为 None，no-op）。

    evidence: 结构化证据（异常前几条/违规判定/预警级别），供审计证据链展示；
    chartData: 报告可视化数据（ECharts option 列表），供前端渲染曲线。
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
    infl = r.get("influent")
    effl = r.get("effluent")
    if isinstance(infl, list) and infl:
        n_in = len(infl)
        n_out = len(effl) if isinstance(effl, list) else 0
        compact["influent_count"] = n_in
        compact["effluent_count"] = n_out
        compact["chart_generated"] = "曲线已由数据感知自动生成（chartData），前端会自动渲染，你不需要自己画"
        stats = {}
        for ind in ("pH", "COD", "TN", "NH3-N", "TP", "SS"):
            infl_vals = [x.get(ind) for x in infl if x.get(ind) is not None]
            effl_vals = [x.get(ind) for x in (effl or []) if x.get(ind) is not None]
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
        if isinstance(md, dict) and md.get("time_range"):
            compact["time_range"] = md["time_range"]
        # ★ 把"数据+曲线已就绪"塞进 summary 头条——LLM 最先读 summary 字段。
        #   之前只把"曲线已生成"放在独立的 chart_generated 字段里，主智能体没读它，
        #   仍为"画曲线"重复调用①。现在让 summary 本身明确告知曲线已随数据返回，杜绝重调。
        ind_list = ", ".join(stats.keys()) if stats else "各指标"
        compact["summary"] = (
            f"✅ 数据+曲线已就绪：进出水各 {n_in}/{n_out} 条"
            f"（{ind_list} 的 min/max/mean 见 data_stats）；"
            f"时序曲线 chartData 已生成，前端自动渲染。"
            f"用户要的'曲线/图'已包含——不要为画曲线再调本子智能体。"
        )

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
    ]
    existing = {t.get('function', {}).get('name') for t in agent.tools if isinstance(t, dict)}
    for s in _ORCH_SCHEMAS:
        if s['function']['name'] not in existing:
            agent.tools.append(s)

    # 砍掉所有非编排工具：主智能体只保留这 4 个编排工具（call_subagent/list_subagents/
    # create_session/read_result），移除 skill_view/skill_manage/skills_list/memory/
    # browser_*/terminal/execute_code 等会让它跑偏去翻技能/记忆/跑终端的分心工具。
    # 主智能体职责是编排+综合，子智能体结果经 call_subagent 回传，不需要其它工具。
    _ORCH_NAMES = {s['function']['name'] for s in _ORCH_SCHEMAS}
    before_n = len(agent.tools)
    agent.tools = [t for t in agent.tools if isinstance(t, dict)
                   and t.get('function', {}).get('name') in _ORCH_NAMES]
    print(f"主智能体工具精简：{before_n} → {len(agent.tools)}（仅保留编排工具，移除分心工具）")

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
        _sc = result.get("skill_calls") if isinstance(result, dict) else None
        _ev = _extract_evidence(result)
        _cd = result.get("result", {}).get("chartData") if isinstance(result, dict) else None
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
            "read_result": _read_result_handler
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
