# tests/events/test_query_collect_gate.py
"""/api/query 采集门控单测：只有本轮真的调了处置子智能体才采集事件。

背景：start_agent 的 _fresh_session_dir 会把上一轮 disposition_result.json
续传进新 session 目录（追问轮不重跑处置但文件在）。若仅凭文件存在就采集，
同会话每追问一次都会插一条内容相同的重复事件——唯一索引只到 session_id
粒度，防不住跨目录。门控函数 _ran_disposition 由两处调用点共用：
非流式（agent 响应 trace.subagent_calls）/ 流式（progress done 收集的
subagent_executions），记录形如 {"subagent_name": "disposition-execution"}。
"""
from backend.api.routes.query import _ran_disposition


def test_none_and_empty():
    assert _ran_disposition(None) is False
    assert _ran_disposition([]) is False


def test_no_disposition_call():
    calls = [
        {"subagent_name": "multi-dimensional-data-perception", "status": "success"},
        {"subagent_name": "anomaly-detection", "status": "success"},
        {"subagent_name": "rule-reasoning", "status": "success"},
    ]
    assert _ran_disposition(calls) is False


def test_has_disposition_call():
    calls = [
        {"subagent_name": "multi-dimensional-data-perception"},
        {"subagent_name": "rule-reasoning"},
        {"subagent_name": "disposition-execution", "status": "success",
         "summary": "高风险，建议立即调查取证"},
    ]
    assert _ran_disposition(calls) is True


def test_name_key_variant():
    # 形状防御：真实 trace 用 subagent_name，但 name 键也认
    # （start_agent 解析 call_subagent 参数时对两个键都做兜底）
    assert _ran_disposition([{"name": "disposition-execution"}]) is True


def test_garbage_entries_do_not_crash():
    # 追问轮/短路轮的记录可能混入非 dict 项，不应炸也不应误判
    assert _ran_disposition([None, "disposition-execution", 42]) is False
    assert _ran_disposition([None, {"subagent_name": "disposition-execution"}]) is True
